from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import save_config


TYPE_LABELS = {
    "discussion": "病例讨论",
    "study": "业务学习",
    "check": "病历检查",
    "followup": "患者回访",
}


STATUS_LABELS = {
    "pending": "待完成",
    "in_progress": "进行中",
    "completed": "已完成",
    "overdue": "已过期",
}


class TaskEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.users = []
        self.task = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("任务分配")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)

        self.type_combo = QComboBox()
        for code, label in TYPE_LABELS.items():
            self.type_combo.addItem(label, code)
        self.type_combo.currentIndexChanged.connect(self._update_hint)

        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(90)

        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem("请选择负责人", None)

        self.deadline_input = QDateEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDisplayFormat("yyyy-MM-dd")
        self.deadline_input.setDate(QDate.currentDate())

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 9999)
        self.quantity_input.setValue(1)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setDate(QDate.currentDate())

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setDate(QDate.currentDate())

        self.quantity_label = QLabel("任务数量：")
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #64748b;")

        self.form.addRow("任务类型：", self.type_combo)
        self.form.addRow("任务说明：", self.description_input)
        self.form.addRow("负责人：", self.assignee_combo)
        self.form.addRow("截止日期：", self.deadline_input)
        self.form.addRow(self.quantity_label, self.quantity_input)
        self.form.addRow("开始日期：", self.start_date_input)
        self.form.addRow("结束日期：", self.end_date_input)
        self.form.addRow("规则说明：", self.hint_label)
        layout.addLayout(self.form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)
        self._update_hint()

    def load_users(self, users):
        self.users = users or []
        current = self.assignee_combo.currentData()
        self.assignee_combo.clear()
        self.assignee_combo.addItem("请选择负责人", None)
        for user in self.users:
            self.assignee_combo.addItem(user.get("real_name") or user.get("username") or "", user.get("id"))
        self._set_combo_data(self.assignee_combo, current)

    def open_for_create(self):
        self.task = None
        self.setWindowTitle("批量分配任务")
        self._set_mode(is_edit=False)
        self.type_combo.setCurrentIndex(0)
        self.description_input.clear()
        self._set_combo_data(self.assignee_combo, None)
        self.quantity_input.setValue(1)
        self.start_date_input.setDate(QDate.currentDate())
        self.end_date_input.setDate(QDate.currentDate())
        self.deadline_input.setDate(QDate.currentDate())
        return self.exec_()

    def open_for_edit(self, task):
        self.task = task
        self.setWindowTitle("编辑任务")
        self._set_mode(is_edit=True)
        self._set_combo_data(self.type_combo, task.get("type"))
        self.description_input.setPlainText(task.get("description") or "")
        self._set_combo_data(self.assignee_combo, task.get("assigned_to"))
        self.deadline_input.setDate(self._to_qdate(task.get("deadline")))
        return self.exec_()

    def get_payload(self):
        if self.task:
            return {
                "type": self.type_combo.currentData(),
                "description": self.description_input.toPlainText().strip(),
                "assigned_to": self.assignee_combo.currentData(),
                "deadline": self.deadline_input.date().toString("yyyy-MM-dd"),
            }
        return {
            "type": self.type_combo.currentData(),
            "description": self.description_input.toPlainText().strip(),
            "assigned_to": self.assignee_combo.currentData(),
            "quantity": self.quantity_input.value(),
            "start_date": self.start_date_input.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date_input.date().toString("yyyy-MM-dd"),
        }

    def _set_mode(self, is_edit):
        self.deadline_input.setVisible(is_edit)
        self.form.labelForField(self.deadline_input).setVisible(is_edit)

        self.quantity_input.setVisible(not is_edit)
        self.form.labelForField(self.quantity_input).setVisible(not is_edit)
        self.start_date_input.setVisible(not is_edit)
        self.form.labelForField(self.start_date_input).setVisible(not is_edit)
        self.end_date_input.setVisible(not is_edit)
        self.form.labelForField(self.end_date_input).setVisible(not is_edit)
        self.hint_label.setVisible(not is_edit)
        self.form.labelForField(self.hint_label).setVisible(not is_edit)
        self.type_combo.setEnabled(not is_edit)

    def _update_hint(self):
        task_type = self.type_combo.currentData()
        if task_type == "followup":
            self.quantity_label.setText("病例总数：")
            self.hint_label.setText("患者回访按周拆分任务，并将病例总数平均分配到各周。")
        elif task_type == "check":
            self.quantity_label.setText("病例数：")
            self.hint_label.setText("病历检查按周拆分任务，并自动结转上期未完成检查任务。")
        else:
            self.quantity_label.setText("任务数量：")
            self.hint_label.setText("系统会按时间范围均分任务数量，并自动生成截止日期。")

    def _set_combo_data(self, combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _to_qdate(self, text):
        parsed = QDate.fromString(text or "", "yyyy-MM-dd")
        return parsed if parsed.isValid() else QDate.currentDate()


class TaskManageWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.tasks = []
        self.users = []
        self.edit_dialog = TaskEditDialog(self)

        self.setWindowTitle("任务分配管理")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("task_manage_window_width", 1260) or 1260), int(self.config.get("task_manage_window_height", 760) or 760))
        x = self.config.get("task_manage_window_x")
        y = self.config.get("task_manage_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.summary_label = QLabel("任务分配加载中...")
        self.summary_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        filters = QHBoxLayout()
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型", "")
        for code, label in TYPE_LABELS.items():
            self.type_filter.addItem(label, code)
        filters.addWidget(self.type_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", "")
        for code, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, code)
        filters.addWidget(self.status_filter)

        self.assignee_filter = QComboBox()
        self.assignee_filter.addItem("全部负责人", None)
        filters.addWidget(self.assignee_filter)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.refresh_content)
        filters.addWidget(query_button)

        self.batch_delete_button = QPushButton("批量删除")
        self.batch_delete_button.clicked.connect(self.batch_delete_tasks)
        filters.addWidget(self.batch_delete_button)

        create_button = QPushButton("批量分配任务")
        create_button.clicked.connect(self.create_task)
        filters.addWidget(create_button)
        filters.addStretch()
        layout.addLayout(filters)

        self.table = QTableWidget(0, 8, self)
        self.table.setHorizontalHeaderLabels(["选择", "任务", "类型", "负责人", "来源", "截止日期", "说明", "状态"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(lambda *_: self.edit_selected_task())
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        edit_button = QPushButton("编辑任务")
        edit_button.clicked.connect(self.edit_selected_task)
        delete_button = QPushButton("删除任务")
        delete_button.clicked.connect(self.delete_selected_task)
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)
        button_row.addStretch()
        layout.addLayout(button_row)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["task_manage_window_x"] = pos.x()
        self.config["task_manage_window_y"] = pos.y()
        self.config["task_manage_window_width"] = size.width()
        self.config["task_manage_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_content(self, silent=False):
        user = self.config.get("user") or {}
        if user.get("role") != "admin":
            QMessageBox.warning(self, "无权限", "只有管理员可以使用任务分配页面")
            self.close()
            return

        try:
            self.users = [item for item in self.api.list_users() if item.get("is_active")]
            self._rebuild_user_filters()
            self.tasks = self.api.list_tasks(
                type=self.type_filter.currentData(),
                status=self.status_filter.currentData(),
                assigned_to=self.assignee_filter.currentData(),
            )
            self.edit_dialog.load_users(self.users)
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载任务分配失败"):
                self.refresh_content(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            self.summary_label.setText("任务分配加载失败")
            return

        self.summary_label.setText(f"当前共 {len(self.tasks)} 个任务")
        self._populate_table()

    def _rebuild_user_filters(self):
        current = self.assignee_filter.currentData()
        self.assignee_filter.blockSignals(True)
        self.assignee_filter.clear()
        self.assignee_filter.addItem("全部负责人", None)
        for user in self.users:
            self.assignee_filter.addItem(user.get("real_name") or user.get("username") or "", user.get("id"))
        index = self.assignee_filter.findData(current)
        self.assignee_filter.setCurrentIndex(index if index >= 0 else 0)
        self.assignee_filter.blockSignals(False)

    def _populate_table(self):
        self.table.setRowCount(len(self.tasks))
        for row, task in enumerate(self.tasks):
            selected_item = QTableWidgetItem()
            selected_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            selected_item.setCheckState(Qt.Unchecked)
            selected_item.setData(Qt.UserRole, task)
            self.table.setItem(row, 0, selected_item)
            self.table.setItem(row, 1, QTableWidgetItem(task.get("title") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(TYPE_LABELS.get(task.get("type"), task.get("type") or "")))
            self.table.setItem(row, 3, QTableWidgetItem(task.get("assignee_name") or ""))
            self.table.setItem(row, 4, QTableWidgetItem("结转任务" if task.get("is_carryover") else "本期生成"))
            self.table.setItem(row, 5, QTableWidgetItem(task.get("deadline") or ""))
            self.table.setItem(row, 6, QTableWidgetItem(task.get("description") or ""))
            self.table.setItem(row, 7, QTableWidgetItem(STATUS_LABELS.get(task.get("status"), task.get("status") or "")))
        if self.tasks:
            self.table.selectRow(0)

    def _selected_task(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _selected_task_ids(self):
        ids = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                task = item.data(Qt.UserRole) or {}
                if task.get("id"):
                    ids.append(task["id"])
        if ids:
            return ids
        task = self._selected_task()
        return [task["id"]] if task and task.get("id") else []

    def create_task(self):
        if self.edit_dialog.open_for_create() != QDialog.Accepted:
            return
        payload = self.edit_dialog.get_payload()
        if not payload.get("assigned_to") or not payload.get("start_date") or not payload.get("end_date"):
            QMessageBox.warning(self, "提示", "请填写完整信息")
            return
        try:
            self.api.create_task(payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "创建任务失败")
            return
        self.refresh_content(silent=True)

    def edit_selected_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        if self.edit_dialog.open_for_edit(task) != QDialog.Accepted:
            return
        payload = self.edit_dialog.get_payload()
        if not payload.get("assigned_to") or not payload.get("deadline"):
            QMessageBox.warning(self, "提示", "请填写完整信息")
            return
        try:
            self.api.update_task(task["id"], payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "更新任务失败")
            return
        self.refresh_content(silent=True)

    def delete_selected_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        reply = QMessageBox.question(self, "确认删除", f"确认删除任务“{task.get('title') or task.get('id')}”吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.delete_task(task["id"])
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "删除任务失败")
            return
        self.refresh_content(silent=True)

    def batch_delete_tasks(self):
        ids = self._selected_task_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择任务")
            return
        reply = QMessageBox.question(self, "批量删除", f"确认删除选中的 {len(ids)} 个任务吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.batch_delete_tasks(ids)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "批量删除任务失败")
            return
        self.refresh_content(silent=True)

