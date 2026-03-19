from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QFrame,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import save_config


class CheckEditDialog(QDialog):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.categories = []
        self.doctors = []
        self.current_user = {}
        self.pending_tasks = []
        self.record = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("病历检查记录")
        self.resize(1040, 840)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.task_combo = QComboBox()
        self.task_combo.addItem("不关联任务", None)
        self.task_combo.currentIndexChanged.connect(self._handle_task_changed)

        self.check_date = QDateEdit()
        self.check_date.setCalendarPopup(True)
        self.check_date.setDisplayFormat("yyyy-MM-dd")
        self.check_date.setDate(QDate.currentDate())

        self.record_no_input = QLineEdit()
        self.patient_name_input = QLineEdit()

        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self._handle_category_changed)

        self.doctor_combo = QComboBox()
        self.doctor_combo.addItem("请选择责任医师", None)

        self.template_combo = QComboBox()
        self.template_combo.addItem("请选择问题模板", "")
        self.template_combo.currentIndexChanged.connect(self._apply_selected_template)

        self.issue_found_input = QTextEdit()
        self.issue_found_input.setPlaceholderText("按自然书写方式输入发现的问题、证据和整改要求。")
        self.issue_found_input.setMinimumHeight(220)

        self.general_radio = QRadioButton("一般问题")
        self.serious_radio = QRadioButton("严重问题")
        self.general_radio.setChecked(True)
        severity_row = QHBoxLayout()
        severity_row.addWidget(self.general_radio)
        severity_row.addWidget(self.serious_radio)
        severity_row.addStretch()

        self.remarks_input = QTextEdit()
        self.remarks_input.setPlaceholderText("补充说明、交接信息或后续跟踪备注。")
        self.remarks_input.setMinimumHeight(150)

        for widget in (
            self.task_combo,
            self.check_date,
            self.category_combo,
            self.doctor_combo,
            self.template_combo,
        ):
            widget.setMinimumHeight(40)
            widget.setStyleSheet("font-size: 12pt; padding: 4px 8px;")

        for line_edit in (self.record_no_input, self.patient_name_input):
            line_edit.setMinimumHeight(40)
            line_edit.setStyleSheet("font-size: 12pt; padding: 6px 10px;")

        self.general_radio.setStyleSheet("font-size: 11pt;")
        self.serious_radio.setStyleSheet("font-size: 11pt;")
        self.issue_found_input.setStyleSheet("font-size: 12pt; padding: 8px 10px; line-height: 1.6;")
        self.remarks_input.setStyleSheet("font-size: 12pt; padding: 8px 10px; line-height: 1.6;")

        form.addRow("关联任务：", self.task_combo)
        form.addRow("检查日期：", self.check_date)
        form.addRow("病案号：", self.record_no_input)
        form.addRow("患者姓名：", self.patient_name_input)
        form.addRow("问题分类：", self.category_combo)
        form.addRow("责任医师：", self.doctor_combo)
        form.addRow("问题模板：", self.template_combo)
        form.addRow("发现问题：", self.issue_found_input)
        form.addRow("严重程度：", severity_row)
        form.addRow("备注：", self.remarks_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self._submit)
        self.close_button.setMinimumHeight(42)
        self.save_button.setMinimumHeight(42)
        self.close_button.setStyleSheet("font-size: 11pt; padding: 0 18px;")
        self.save_button.setStyleSheet("font-size: 11pt; font-weight: 600; padding: 0 18px;")
        button_row.addWidget(self.close_button)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

    def load_meta(self, categories, doctors, current_user, pending_tasks):
        self.categories = categories or []
        self.doctors = doctors or []
        self.current_user = current_user or {}
        self.pending_tasks = pending_tasks or []
        self._rebuild_category_options()
        self._rebuild_doctor_options()
        self._rebuild_task_options()

    def open_for_create(self):
        self.record = None
        self.setWindowTitle("新增病历检查")
        self._reset_form()
        return self.exec_()

    def open_for_edit(self, record):
        self.record = record
        self.setWindowTitle("编辑病历检查")
        self._reset_form()
        self._set_combo_by_data(self.task_combo, record.get("task_id"))
        self.check_date.setDate(self._to_qdate(record.get("check_date")))
        self.record_no_input.setText(record.get("record_no") or "")
        self.patient_name_input.setText(record.get("patient_name") or "")
        self._set_combo_by_data(self.category_combo, record.get("issue_category"))
        self._set_combo_by_data(self.doctor_combo, record.get("responsible_doctor_id"))
        self._refresh_template_options()
        self._set_combo_by_data(self.template_combo, record.get("issue_template") or "")
        self.issue_found_input.setPlainText(record.get("issue_found") or "")
        self.serious_radio.setChecked(record.get("severity") == "serious")
        self.general_radio.setChecked(record.get("severity") != "serious")
        self.remarks_input.setPlainText(record.get("remarks") or "")
        can_edit = self._can_edit_core_fields(record)
        self._set_core_fields_enabled(can_edit)
        self.save_button.setVisible(can_edit)
        return self.exec_()

    def _reset_form(self):
        self._set_combo_by_data(self.task_combo, None)
        self.check_date.setDate(QDate.currentDate())
        self.record_no_input.clear()
        self.patient_name_input.clear()
        if self.category_combo.count() > 0:
            self.category_combo.setCurrentIndex(0)
        self._set_combo_by_data(self.doctor_combo, None)
        self._refresh_template_options()
        self.issue_found_input.clear()
        self.general_radio.setChecked(True)
        self.remarks_input.clear()
        self._set_core_fields_enabled(True)
        self.save_button.setVisible(True)

    def _rebuild_task_options(self):
        current = self.task_combo.currentData()
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("不关联任务", None)
        for task in self.pending_tasks:
            self.task_combo.addItem(task.get("title") or f"任务 #{task.get('id')}", task.get("id"))
        self._set_combo_by_data(self.task_combo, current)
        self.task_combo.blockSignals(False)

    def _rebuild_category_options(self):
        current = self.category_combo.currentData()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        for category in self.categories:
            self.category_combo.addItem(category.get("label") or category.get("code") or "", category.get("code"))
        self._set_combo_by_data(self.category_combo, current or (self.categories[0].get("code") if self.categories else None))
        self.category_combo.blockSignals(False)
        self._refresh_template_options()

    def _rebuild_doctor_options(self):
        current = self.doctor_combo.currentData()
        self.doctor_combo.clear()
        self.doctor_combo.addItem("请选择责任医师", None)
        current_user_id = self.current_user.get("id")
        current_role = self.current_user.get("role")
        for doctor in self.doctors:
            if current_role == "doctor" and doctor.get("id") == current_user_id:
                continue
            self.doctor_combo.addItem(doctor.get("real_name") or doctor.get("username") or "", doctor.get("id"))
        self._set_combo_by_data(self.doctor_combo, current)

    def _refresh_template_options(self):
        current = self.template_combo.currentData()
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("请选择问题模板", "")
        category = self._selected_category()
        templates = category.get("templates") if category else []
        for template in templates:
            self.template_combo.addItem(template, template)
        self._set_combo_by_data(self.template_combo, current)
        self.template_combo.blockSignals(False)

    def _selected_category(self):
        code = self.category_combo.currentData()
        for category in self.categories:
            if category.get("code") == code:
                return category
        return None

    def _handle_category_changed(self):
        self._refresh_template_options()

    def _handle_task_changed(self):
        task_id = self.task_combo.currentData()
        if not task_id:
            return
        for task in self.pending_tasks:
            if task.get("id") == task_id and not self.doctor_combo.currentData():
                self._set_combo_by_data(self.doctor_combo, task.get("assigned_to"))
                return

    def _apply_selected_template(self):
        template = self.template_combo.currentData()
        if not template:
            return
        current_text = self.issue_found_input.toPlainText().strip()
        if not current_text or current_text == self.record_no_input.text().strip():
            self.issue_found_input.setPlainText(template)
            return
        if current_text in ("", template):
            self.issue_found_input.setPlainText(template)

    def _submit(self):
        payload = {
            "task_id": self.task_combo.currentData(),
            "check_date": self.check_date.date().toString("yyyy-MM-dd"),
            "record_no": self.record_no_input.text().strip(),
            "patient_name": self.patient_name_input.text().strip(),
            "responsible_doctor_id": self.doctor_combo.currentData(),
            "issue_category": self.category_combo.currentData() or "other",
            "issue_template": self.template_combo.currentData() or "",
            "issue_found": self.issue_found_input.toPlainText().strip(),
            "severity": "serious" if self.serious_radio.isChecked() else "general",
            "remarks": self.remarks_input.toPlainText().strip(),
        }
        if not payload["check_date"]:
            QMessageBox.warning(self, "提示", "请选择检查日期")
            return
        if not payload["responsible_doctor_id"]:
            QMessageBox.warning(self, "提示", "请选择责任医师")
            return
        if not payload["issue_found"]:
            QMessageBox.warning(self, "提示", "请填写发现问题")
            return
        try:
            if self.record:
                self.api.update_check(self.record["id"], payload)
            else:
                self.api.create_check(payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "保存病历检查失败")
            return
        self.app_context.refresh_overlay()
        self.accept()

    def _set_combo_by_data(self, combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _set_core_fields_enabled(self, enabled):
        widgets = [
            self.task_combo,
            self.check_date,
            self.record_no_input,
            self.patient_name_input,
            self.category_combo,
            self.doctor_combo,
            self.template_combo,
            self.issue_found_input,
            self.general_radio,
            self.serious_radio,
            self.remarks_input,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)

    def _can_edit_core_fields(self, record):
        user = self.current_user or {}
        return user.get("role") == "admin" or record.get("created_by") == user.get("id")

    def _to_qdate(self, text):
        parsed = QDate.fromString(text or "", "yyyy-MM-dd")
        return parsed if parsed.isValid() else QDate.currentDate()


class CheckWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.records = []
        self.stats = {"summary": {}, "category_stats": [], "doctor_stats": []}
        self.categories = []
        self.doctors = []
        self.current_user = {}
        self.pending_tasks = []
        self.pending_focus = {"task_id": None, "check_id": None}
        self.edit_dialog = CheckEditDialog(app_context, self)

        self.setWindowTitle("病历质控检查")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("check_window_width", 1320) or 1320), int(self.config.get("check_window_height", 780) or 780))
        x = self.config.get("check_window_x")
        y = self.config.get("check_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.summary_label = QLabel("病历检查加载中...")
        self.summary_label.setStyleSheet("font-size: 14pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        filters = QHBoxLayout()
        start_label = QLabel("开始")
        start_label.setStyleSheet("font-size: 11pt;")
        filters.addWidget(start_label)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setMinimumHeight(40)
        self.start_date.setStyleSheet("font-size: 11pt;")
        filters.addWidget(self.start_date)

        end_label = QLabel("结束")
        end_label.setStyleSheet("font-size: 11pt;")
        filters.addWidget(end_label)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setMinimumHeight(40)
        self.end_date.setStyleSheet("font-size: 11pt;")
        filters.addWidget(self.end_date)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部整改状态", "")
        self.status_filter.addItem("待整改", "pending")
        self.status_filter.addItem("已整改", "rectified")
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        self.status_filter.setMinimumHeight(40)
        self.status_filter.setStyleSheet("font-size: 11pt; padding: 4px 8px;")
        filters.addWidget(self.status_filter)

        self.category_filter = QComboBox()
        self.category_filter.addItem("全部问题分类", "")
        self.category_filter.currentIndexChanged.connect(self._apply_filters)
        self.category_filter.setMinimumHeight(40)
        self.category_filter.setStyleSheet("font-size: 11pt; padding: 4px 8px;")
        filters.addWidget(self.category_filter)

        self.doctor_filter = QComboBox()
        self.doctor_filter.addItem("全部责任医师", "")
        self.doctor_filter.currentIndexChanged.connect(self._apply_filters)
        self.doctor_filter.setMinimumHeight(40)
        self.doctor_filter.setStyleSheet("font-size: 11pt; padding: 4px 8px;")
        filters.addWidget(self.doctor_filter)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.refresh_content)
        query_button.setMinimumHeight(40)
        query_button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        filters.addWidget(query_button)

        create_button = QPushButton("新增检查")
        create_button.clicked.connect(self.create_record)
        create_button.setMinimumHeight(40)
        create_button.setStyleSheet("font-size: 11pt; font-weight: 600; padding: 0 16px;")
        filters.addWidget(create_button)

        filters.addStretch()
        layout.addLayout(filters)

        self.focus_label = QLabel("")
        self.focus_label.setStyleSheet("padding: 12px 14px; background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; border-radius: 8px; font-size: 11pt;")
        self.focus_label.setVisible(False)
        layout.addWidget(self.focus_label)

        stats_layout = QGridLayout()
        stats_layout.setHorizontalSpacing(12)
        stats_layout.setVerticalSpacing(12)
        self.total_card = self._create_stat_card("检查总数", "--")
        self.serious_card = self._create_stat_card("严重问题", "--")
        self.rectified_card = self._create_stat_card("已整改", "--")
        self.pending_card = self._create_stat_card("待整改", "--")
        stats_layout.addWidget(self.total_card, 0, 0)
        stats_layout.addWidget(self.serious_card, 0, 1)
        stats_layout.addWidget(self.rectified_card, 0, 2)
        stats_layout.addWidget(self.pending_card, 0, 3)
        layout.addLayout(stats_layout)

        summary_tables = QHBoxLayout()
        summary_tables.setSpacing(12)
        self.category_stats_table = self._create_summary_table(["分类", "总数", "严重", "已整改", "待整改"])
        self.doctor_stats_table = self._create_summary_table(["责任医师", "总数", "严重", "已整改", "待整改"])
        summary_tables.addWidget(self._wrap_summary_table("按问题分类统计", self.category_stats_table), 1)
        summary_tables.addWidget(self._wrap_summary_table("按责任医师统计", self.doctor_stats_table), 1)
        layout.addLayout(summary_tables)

        self.table = QTableWidget(0, 10, self)
        self.table.setStyleSheet("QTableWidget { font-size: 11pt; } QHeaderView::section { font-size: 11pt; padding: 8px; }")
        self.table.setHorizontalHeaderLabels(["检查日期", "病案号", "患者姓名", "问题分类", "责任医师", "严重程度", "整改状态", "整改日期", "发现问题", "检查人"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected_record())
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        self.open_button = QPushButton("打开选中记录")
        self.open_button.clicked.connect(self.open_selected_record)
        self.rectify_button = QPushButton("进入整改")
        self.rectify_button.clicked.connect(self.rectify_selected_record)
        self.detail_button = QPushButton("查看待办详情")
        self.detail_button.clicked.connect(self.open_selected_task_detail)
        self.delete_button = QPushButton("删除记录")
        self.delete_button.clicked.connect(self.delete_selected_record)
        button_row.addWidget(self.open_button)
        button_row.addWidget(self.rectify_button)
        button_row.addWidget(self.detail_button)
        button_row.addWidget(self.delete_button)
        for button in (self.open_button, self.rectify_button, self.detail_button, self.delete_button):
            button.setMinimumHeight(40)
            button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        button_row.addStretch()
        layout.addLayout(button_row)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["check_window_x"] = pos.x()
        self.config["check_window_y"] = pos.y()
        self.config["check_window_width"] = size.width()
        self.config["check_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def open_for_context(self, task=None, check_id=None):
        self.pending_focus = {
            "task_id": task.get("id") if task else None,
            "check_id": check_id,
        }
        self.show()
        self.raise_()
        self.activateWindow()
        self.refresh_content(silent=True)

    def refresh_content(self, silent=False):
        try:
            meta = self.api.get_checks_meta()
            self.categories = meta.get("categories") or []
            self.doctors = meta.get("doctors") or []
            self.current_user = meta.get("current_user") or {}
            self.pending_tasks = [
                task for task in self.api.list_tasks(type="check")
                if task.get("status") != "completed" and task.get("check_task_kind") != "rectification"
            ]
            self._rebuild_filter_options()
            self.records = self.api.list_checks(
                start=self.start_date.date().toString("yyyy-MM-dd"),
                end=self.end_date.date().toString("yyyy-MM-dd"),
            )
            self.stats = self.api.get_check_stats(
                start=self.start_date.date().toString("yyyy-MM-dd"),
                end=self.end_date.date().toString("yyyy-MM-dd"),
            )
            self.edit_dialog.load_meta(self.categories, self.doctors, self.current_user, self.pending_tasks)
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载病历检查失败"):
                self.refresh_content(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            self.summary_label.setText("病历检查加载失败")
            return

        self._apply_filters()
        self._populate_stats()
        self._focus_target()

    def _rebuild_filter_options(self):
        current_category = self.category_filter.currentData()
        current_doctor = self.doctor_filter.currentData()

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("全部问题分类", "")
        for category in self.categories:
            self.category_filter.addItem(category.get("label") or category.get("code") or "", category.get("code"))
        index = self.category_filter.findData(current_category)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

        self.doctor_filter.blockSignals(True)
        self.doctor_filter.clear()
        self.doctor_filter.addItem("全部责任医师", "")
        for doctor in self.doctors:
            self.doctor_filter.addItem(doctor.get("real_name") or doctor.get("username") or "", doctor.get("id"))
        index = self.doctor_filter.findData(current_doctor)
        self.doctor_filter.setCurrentIndex(index if index >= 0 else 0)
        self.doctor_filter.blockSignals(False)

    def _apply_filters(self):
        status_filter = self.status_filter.currentData()
        category_filter = self.category_filter.currentData()
        doctor_filter = self.doctor_filter.currentData()

        filtered = []
        for record in self.records:
            if status_filter == "pending" and record.get("is_rectified"):
                continue
            if status_filter == "rectified" and not record.get("is_rectified"):
                continue
            if category_filter and record.get("issue_category") != category_filter:
                continue
            if doctor_filter and record.get("responsible_doctor_id") != doctor_filter:
                continue
            filtered.append(record)

        self.summary_label.setText(f"病历检查共 {len(self.records)} 条，当前筛选结果 {len(filtered)} 条")
        self._populate_table(filtered)

    def _populate_stats(self):
        summary = self.stats.get("summary") or {}
        self.total_card.value_label.setText(str(summary.get("count", 0)))
        self.serious_card.value_label.setText(str(summary.get("serious", 0)))
        self.rectified_card.value_label.setText(str(summary.get("rectified", 0)))
        self.pending_card.value_label.setText(str(summary.get("pending", 0)))

        self._fill_summary_table(
            self.category_stats_table,
            self.stats.get("category_stats") or [],
            [
                lambda item: item.get("label") or "",
                lambda item: str(item.get("count", 0)),
                lambda item: str(item.get("serious", 0)),
                lambda item: str(item.get("rectified", 0)),
                lambda item: str(item.get("pending", 0)),
            ],
        )
        self._fill_summary_table(
            self.doctor_stats_table,
            self.stats.get("doctor_stats") or [],
            [
                lambda item: item.get("doctor_name") or "未指定",
                lambda item: str(item.get("count", 0)),
                lambda item: str(item.get("serious", 0)),
                lambda item: str(item.get("rectified", 0)),
                lambda item: str(item.get("pending", 0)),
            ],
        )

    def _populate_table(self, records):
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = [
                record.get("check_date") or "",
                record.get("record_no") or "",
                record.get("patient_name") or "",
                record.get("issue_category_label") or record.get("issue_category") or "",
                record.get("responsible_doctor_name") or "未指定",
                "严重" if record.get("severity") == "serious" else "一般",
                "已整改" if record.get("is_rectified") else "待整改",
                record.get("rectified_date") or "",
                record.get("issue_found") or "",
                record.get("creator_name") or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if column == 0:
                    item.setData(Qt.UserRole, record)
                self.table.setItem(row, column, item)

        if records:
            self.table.selectRow(0)

    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _create_stat_card(self, title, value):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11pt; color: #64748b; font-weight: 600;")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 20pt; color: #0f172a; font-weight: 700;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        frame.value_label = value_label
        return frame

    def _create_summary_table(self, headers):
        table = QTableWidget(0, len(headers), self)
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        return table

    def _wrap_summary_table(self, title, table):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12pt; font-weight: 700; color: #0f172a;")
        layout.addWidget(title_label)
        layout.addWidget(table)
        return frame

    def _fill_summary_table(self, table, rows, extractors):
        table.setRowCount(len(rows))
        for row_index, row_data in enumerate(rows):
            for column, extractor in enumerate(extractors):
                item = QTableWidgetItem(extractor(row_data))
                item.setTextAlignment(Qt.AlignCenter if column > 0 else (Qt.AlignLeft | Qt.AlignVCenter))
                table.setItem(row_index, column, item)

    def _focus_target(self):
        task_id = self.pending_focus.get("task_id")
        check_id = self.pending_focus.get("check_id")
        if not task_id and not check_id:
            self.focus_label.setVisible(False)
            return

        target_row = None
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            record = item.data(Qt.UserRole) or {}
            if check_id and record.get("id") == check_id:
                target_row = row
                break
            if task_id and (record.get("task_id") == task_id or record.get("rectification_task_id") == task_id):
                target_row = row
                break

        if target_row is not None:
            self.table.selectRow(target_row)
            self.table.scrollToItem(self.table.item(target_row, 0))
            self.focus_label.setText("已根据任务定位到关联病历检查记录。")
        else:
            self.focus_label.setText("未在当前筛选条件内找到关联病历检查记录，请调整日期范围后重试。")
        self.focus_label.setVisible(True)
        self.pending_focus = {"task_id": None, "check_id": None}

    def create_record(self):
        if self.edit_dialog.open_for_create() == QDialog.Accepted:
            self.refresh_content(silent=True)

    def open_selected_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条检查记录")
            return
        if self.edit_dialog.open_for_edit(record) == QDialog.Accepted:
            self.refresh_content(silent=True)

    def rectify_selected_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条检查记录")
            return
        if record.get("is_rectified"):
            QMessageBox.information(self, "提示", "该记录已整改")
            return
        if record.get("rectification_task_id"):
            task = {
                "id": record.get("rectification_task_id"),
                "type": "check",
                "title": f"病历问题整改 {record.get('record_no') or record.get('patient_name') or ''}",
                "check_task_kind": "rectification",
                "linked_check_id": record.get("id"),
            }
            self.app_context.show_rectification_window(task)
            return
        QMessageBox.information(self, "提示", "该记录暂未生成整改任务，请先补充责任医师并保存。")

    def open_selected_task_detail(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条检查记录")
            return
        task_id = record.get("rectification_task_id") or record.get("task_id")
        if not task_id:
            QMessageBox.information(self, "提示", "该记录未关联任务")
            return
        task = {
            "id": task_id,
            "type": "check",
            "title": f"病历检查任务 #{task_id}",
            "check_task_kind": "rectification" if record.get("rectification_task_id") == task_id else "scheduled",
            "linked_check_id": record.get("id"),
        }
        self.app_context.show_task_detail_window(task)

    def delete_selected_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条检查记录")
            return
        user = self.current_user or {}
        if user.get("role") != "admin" and record.get("created_by") != user.get("id"):
            QMessageBox.warning(self, "无权限", "只有管理员或创建人可以删除该记录")
            return
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确认删除检查记录“{record.get('record_no') or record.get('patient_name') or record.get('id')}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.delete_check(record["id"])
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "删除病历检查失败")
            return
        self.refresh_content(silent=True)

