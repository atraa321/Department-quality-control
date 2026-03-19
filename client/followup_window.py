from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import save_config


METHOD_LABELS = {
    "phone": "电话",
    "visit": "上门",
    "online": "线上",
}


ROLE_LABELS = {
    "doctor": "医师",
    "nurse": "护士",
}


class FollowupEditDialog(QDialog):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.current_patient = None
        self.current_record = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("回访登记")
        self.resize(620, 520)

        layout = QVBoxLayout(self)
        self.patient_summary_label = QLabel()
        self.patient_summary_label.setWordWrap(True)
        self.patient_summary_label.setStyleSheet("padding: 12px; background: #f8fafc; border: 1px solid #dbe3ee; border-radius: 8px;")
        layout.addWidget(self.patient_summary_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)

        self.followup_date_input = QDateEdit()
        self.followup_date_input.setCalendarPopup(True)
        self.followup_date_input.setDisplayFormat("yyyy-MM-dd")
        self.followup_date_input.setDate(QDate.currentDate())

        self.method_input = QComboBox()
        self.method_input.addItem("电话", "phone")
        self.method_input.addItem("上门", "visit")
        self.method_input.addItem("线上", "online")

        self.feedback_input = QTextEdit()
        self.feedback_input.setMinimumHeight(90)
        self.satisfaction_input = QSpinBox()
        self.satisfaction_input.setRange(1, 5)
        self.satisfaction_input.setValue(5)
        self.suggestions_input = QTextEdit()
        self.suggestions_input.setMinimumHeight(70)
        self.needs_attention_input = QCheckBox("需重点关注")

        form.addRow("回访日期：", self.followup_date_input)
        form.addRow("回访方式：", self.method_input)
        form.addRow("患者反馈：", self.feedback_input)
        form.addRow("满意度：", self.satisfaction_input)
        form.addRow("意见建议：", self.suggestions_input)
        form.addRow("", self.needs_attention_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("保存")
        save_button.clicked.connect(self._submit)
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

    def open_for_create(self, patient):
        self.current_patient = patient
        self.current_record = None
        self.setWindowTitle("登记回访")
        self.patient_summary_label.setText(self._format_patient_summary(patient))
        self.followup_date_input.setDate(QDate.currentDate())
        self.method_input.setCurrentIndex(0)
        self.feedback_input.clear()
        self.satisfaction_input.setValue(5)
        self.suggestions_input.clear()
        self.needs_attention_input.setChecked(False)
        return self.exec_()

    def open_for_edit(self, record):
        self.current_patient = None
        self.current_record = record
        self.setWindowTitle("编辑回访")
        self.patient_summary_label.setText(self._format_record_summary(record))
        parsed_date = QDate.fromString(record.get("followup_date") or "", "yyyy-MM-dd")
        self.followup_date_input.setDate(parsed_date if parsed_date.isValid() else QDate.currentDate())
        index = self.method_input.findData(record.get("followup_method") or "phone")
        self.method_input.setCurrentIndex(index if index >= 0 else 0)
        self.feedback_input.setPlainText(record.get("feedback") or "")
        self.satisfaction_input.setValue(int(record.get("satisfaction") or 5))
        self.suggestions_input.setPlainText(record.get("suggestions") or "")
        self.needs_attention_input.setChecked(bool(record.get("needs_attention")))
        return self.exec_()

    def _submit(self):
        payload = {
            "followup_date": self.followup_date_input.date().toString("yyyy-MM-dd"),
            "followup_method": self.method_input.currentData(),
            "feedback": self.feedback_input.toPlainText().strip(),
            "satisfaction": self.satisfaction_input.value(),
            "suggestions": self.suggestions_input.toPlainText().strip(),
            "needs_attention": self.needs_attention_input.isChecked(),
        }
        if not payload["followup_date"]:
            QMessageBox.warning(self, "提示", "请选择回访日期")
            return
        try:
            if self.current_record:
                self.api.update_followup(self.current_record["id"], payload)
            else:
                payload["patient_id"] = self.current_patient["id"]
                self.api.create_followup(payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "保存回访失败")
            return
        self.app_context.refresh_overlay()
        self.accept()

    def _format_patient_summary(self, patient):
        return (
            f"患者：{patient.get('patient_name') or '-'}\n"
            f"病案号：{patient.get('record_no') or '-'}\n"
            f"诊断：{patient.get('diagnosis') or '-'}\n"
            f"出院日期：{patient.get('discharge_date') or '-'}\n"
            f"主管医师：{patient.get('attending_doctor') or '-'}"
        )

    def _format_record_summary(self, record):
        return (
            f"患者：{record.get('patient_name') or '-'}\n"
            f"回访日期：{record.get('followup_date') or '-'}\n"
            f"回访方式：{METHOD_LABELS.get(record.get('followup_method'), record.get('followup_method') or '-')}\n"
            f"回访人：{record.get('followup_by_name') or '-'}"
        )


class FollowupWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.patients = []
        self.followups = []
        self.stats = []
        self.edit_dialog = FollowupEditDialog(app_context, self)

        self.setWindowTitle("出院患者回访")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("followup_window_width", 1240) or 1240), int(self.config.get("followup_window_height", 760) or 760))
        x = self.config.get("followup_window_x")
        y = self.config.get("followup_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.summary_label = QLabel("回访模块加载中...")
        self.summary_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        self.tabs = QTabWidget()
        self.todo_tab = self._build_todo_tab()
        self.records_tab = self._build_records_tab()
        self.stats_tab = self._build_stats_tab()
        self.tabs.addTab(self.todo_tab, "待回访患者")
        self.tabs.addTab(self.records_tab, "回访记录")
        self.tabs.addTab(self.stats_tab, "工作量统计")
        layout.addWidget(self.tabs)

    def _build_todo_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("出院开始"))
        self.patient_start_date = QDateEdit()
        self.patient_start_date.setCalendarPopup(True)
        self.patient_start_date.setDisplayFormat("yyyy-MM-dd")
        self.patient_start_date.setDate(QDate.currentDate().addMonths(-1))
        filters.addWidget(self.patient_start_date)

        filters.addWidget(QLabel("出院结束"))
        self.patient_end_date = QDateEdit()
        self.patient_end_date.setCalendarPopup(True)
        self.patient_end_date.setDisplayFormat("yyyy-MM-dd")
        self.patient_end_date.setDate(QDate.currentDate())
        filters.addWidget(self.patient_end_date)

        patient_query_button = QPushButton("查询患者")
        patient_query_button.clicked.connect(self.load_patients)
        filters.addWidget(patient_query_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.patient_table = QTableWidget(0, 8, self)
        self.patient_table.setHorizontalHeaderLabels(["患者", "病案号", "诊断", "出院日期", "主管医师", "医师回访", "护士回访", "操作"])
        self.patient_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patient_table.setSelectionMode(QTableWidget.SingleSelection)
        self.patient_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.patient_table.setAlternatingRowColors(True)
        self.patient_table.verticalHeader().setVisible(False)
        patient_header = self.patient_table.horizontalHeader()
        patient_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        patient_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        patient_header.setSectionResizeMode(2, QHeaderView.Stretch)
        patient_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        patient_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        patient_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        patient_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        patient_header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.patient_table.itemDoubleClicked.connect(lambda *_: self.create_followup())
        layout.addWidget(self.patient_table)

        button_row = QHBoxLayout()
        create_button = QPushButton("登记回访")
        create_button.clicked.connect(self.create_followup)
        button_row.addWidget(create_button)
        button_row.addStretch()
        layout.addLayout(button_row)
        return page

    def _build_records_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("回访开始"))
        self.record_start_date = QDateEdit()
        self.record_start_date.setCalendarPopup(True)
        self.record_start_date.setDisplayFormat("yyyy-MM-dd")
        self.record_start_date.setDate(QDate.currentDate().addMonths(-1))
        filters.addWidget(self.record_start_date)

        filters.addWidget(QLabel("回访结束"))
        self.record_end_date = QDateEdit()
        self.record_end_date.setCalendarPopup(True)
        self.record_end_date.setDisplayFormat("yyyy-MM-dd")
        self.record_end_date.setDate(QDate.currentDate())
        filters.addWidget(self.record_end_date)

        self.role_filter = QComboBox()
        self.role_filter.addItem("全部角色", "")
        self.role_filter.addItem("医师", "doctor")
        self.role_filter.addItem("护士", "nurse")
        filters.addWidget(self.role_filter)

        record_query_button = QPushButton("查询记录")
        record_query_button.clicked.connect(self.load_followups)
        filters.addWidget(record_query_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.followup_table = QTableWidget(0, 8, self)
        self.followup_table.setHorizontalHeaderLabels(["回访日期", "患者", "方式", "反馈", "满意度", "回访人", "角色", "需关注"])
        self.followup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.followup_table.setSelectionMode(QTableWidget.SingleSelection)
        self.followup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.followup_table.setAlternatingRowColors(True)
        self.followup_table.verticalHeader().setVisible(False)
        followup_header = self.followup_table.horizontalHeader()
        followup_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        followup_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        followup_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        followup_header.setSectionResizeMode(3, QHeaderView.Stretch)
        followup_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        followup_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        followup_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        followup_header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.followup_table.itemDoubleClicked.connect(lambda *_: self.edit_followup())
        layout.addWidget(self.followup_table)

        button_row = QHBoxLayout()
        edit_button = QPushButton("编辑记录")
        edit_button.clicked.connect(self.edit_followup)
        delete_button = QPushButton("删除记录")
        delete_button.clicked.connect(self.delete_followup)
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)
        button_row.addStretch()
        layout.addLayout(button_row)
        return page

    def _build_stats_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("开始"))
        self.stats_start_date = QDateEdit()
        self.stats_start_date.setCalendarPopup(True)
        self.stats_start_date.setDisplayFormat("yyyy-MM-dd")
        self.stats_start_date.setDate(QDate.currentDate().addMonths(-1))
        filters.addWidget(self.stats_start_date)

        filters.addWidget(QLabel("结束"))
        self.stats_end_date = QDateEdit()
        self.stats_end_date.setCalendarPopup(True)
        self.stats_end_date.setDisplayFormat("yyyy-MM-dd")
        self.stats_end_date.setDate(QDate.currentDate())
        filters.addWidget(self.stats_end_date)

        stats_query_button = QPushButton("统计")
        stats_query_button.clicked.connect(self.load_stats)
        filters.addWidget(stats_query_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.stats_table = QTableWidget(0, 4, self)
        self.stats_table.setHorizontalHeaderLabels(["姓名", "角色", "回访次数", "平均满意度"])
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stats_table.setSelectionMode(QTableWidget.SingleSelection)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.verticalHeader().setVisible(False)
        stats_header = self.stats_table.horizontalHeader()
        for column in range(4):
            stats_header.setSectionResizeMode(column, QHeaderView.Stretch)
        layout.addWidget(self.stats_table)
        return page

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["followup_window_x"] = pos.x()
        self.config["followup_window_y"] = pos.y()
        self.config["followup_window_width"] = size.width()
        self.config["followup_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_content(self, silent=False):
        self.load_patients(silent=True)
        self.load_followups(silent=True)
        self.load_stats(silent=True)
        user = self.config.get("user") or {}
        role_label = ROLE_LABELS.get(user.get("role"), user.get("role") or "用户")
        self.summary_label.setText(f"当前回访角色：{role_label} | 待回访患者 {len(self.patients)} 人 | 已加载回访记录 {len(self.followups)} 条")

    def open_for_task(self, task=None):
        self.show()
        self.raise_()
        self.activateWindow()
        self.tabs.setCurrentWidget(self.todo_tab)
        self.refresh_content(silent=True)

    def load_patients(self, silent=False):
        params = {
            "start": self.patient_start_date.date().toString("yyyy-MM-dd"),
            "end": self.patient_end_date.date().toString("yyyy-MM-dd"),
        }
        try:
            self.patients = self.api.list_patients(**params)
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载待回访患者失败"):
                self.load_patients(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            return
        self._populate_patient_table()

    def load_followups(self, silent=False):
        params = {
            "start": self.record_start_date.date().toString("yyyy-MM-dd"),
            "end": self.record_end_date.date().toString("yyyy-MM-dd"),
            "role": self.role_filter.currentData(),
        }
        try:
            self.followups = self.api.list_followups(**params)
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载回访记录失败"):
                self.load_followups(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            return
        self._populate_followup_table()

    def load_stats(self, silent=False):
        params = {
            "start": self.stats_start_date.date().toString("yyyy-MM-dd"),
            "end": self.stats_end_date.date().toString("yyyy-MM-dd"),
        }
        try:
            self.stats = self.api.get_followup_stats(**params)
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载工作量统计失败"):
                self.load_stats(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            return
        self._populate_stats_table()

    def create_followup(self):
        patient = self._selected_patient()
        if not patient:
            QMessageBox.information(self, "提示", "请先选择一位患者")
            return
        if self.edit_dialog.open_for_create(patient) == QDialog.Accepted:
            self.refresh_content(silent=True)
            self.tabs.setCurrentWidget(self.records_tab)

    def edit_followup(self):
        record = self._selected_followup()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条回访记录")
            return
        if self.edit_dialog.open_for_edit(record) == QDialog.Accepted:
            self.refresh_content(silent=True)

    def delete_followup(self):
        record = self._selected_followup()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条回访记录")
            return
        reply = QMessageBox.question(self, "确认删除", f"确认删除 {record.get('patient_name') or '该患者'} 的回访记录吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.delete_followup(record["id"])
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "删除回访记录失败")
            return
        self.refresh_content(silent=True)

    def _populate_patient_table(self):
        self.patient_table.setRowCount(len(self.patients))
        for row, patient in enumerate(self.patients):
            values = [
                patient.get("patient_name") or "",
                patient.get("record_no") or "",
                patient.get("diagnosis") or "",
                patient.get("discharge_date") or "",
                patient.get("attending_doctor") or "",
                "已回访" if patient.get("doctor_followup_done") else "未回访",
                "已回访" if patient.get("nurse_followup_done") else "未回访",
                "登记回访",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if column == 0:
                    item.setData(Qt.UserRole, patient)
                self.patient_table.setItem(row, column, item)
        if self.patients:
            self.patient_table.selectRow(0)

    def _populate_followup_table(self):
        self.followup_table.setRowCount(len(self.followups))
        for row, record in enumerate(self.followups):
            values = [
                record.get("followup_date") or "",
                record.get("patient_name") or "",
                METHOD_LABELS.get(record.get("followup_method"), record.get("followup_method") or ""),
                record.get("feedback") or "",
                str(record.get("satisfaction") or ""),
                record.get("followup_by_name") or "",
                ROLE_LABELS.get(record.get("followup_role"), record.get("followup_role") or ""),
                "是" if record.get("needs_attention") else "否",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if column == 0:
                    item.setData(Qt.UserRole, record)
                self.followup_table.setItem(row, column, item)
        if self.followups:
            self.followup_table.selectRow(0)

    def _populate_stats_table(self):
        self.stats_table.setRowCount(len(self.stats))
        for row, stat in enumerate(self.stats):
            values = [
                stat.get("real_name") or "",
                ROLE_LABELS.get(stat.get("role"), stat.get("role") or ""),
                str(stat.get("count") or 0),
                str(stat.get("avg_satisfaction") or 0),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.stats_table.setItem(row, column, item)

    def _selected_patient(self):
        row = self.patient_table.currentRow()
        if row < 0:
            return None
        item = self.patient_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _selected_followup(self):
        row = self.followup_table.currentRow()
        if row < 0:
            return None
        item = self.followup_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

