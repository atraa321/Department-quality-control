from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


TYPE_LABELS = {
    "discussion": "病例讨论",
    "study": "业务学习",
    "check": "病历检查",
    "followup": "患者回访",
}


class TodoPanel(QWidget):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.tasks = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.summary_label = QLabel("待办加载中...")
        self.summary_label.setStyleSheet("font-size: 14pt; font-weight: 600;")
        header_layout.addWidget(self.summary_label)
        header_layout.addStretch()

        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型", "")
        self.type_filter.addItem("病例讨论", "discussion")
        self.type_filter.addItem("业务学习", "study")
        self.type_filter.addItem("病历检查", "check")
        self.type_filter.addItem("患者回访", "followup")
        self.type_filter.currentIndexChanged.connect(self._update_table)
        self.type_filter.setMinimumHeight(40)
        self.type_filter.setStyleSheet("font-size: 11pt; padding: 4px 8px;")
        header_layout.addWidget(self.type_filter)

        self.overdue_only = QCheckBox("仅看逾期")
        self.overdue_only.setStyleSheet("font-size: 11pt;")
        self.overdue_only.stateChanged.connect(self._update_table)
        header_layout.addWidget(self.overdue_only)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_tasks)
        self.refresh_button.setMinimumHeight(40)
        self.refresh_button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        header_layout.addWidget(self.refresh_button)

        self.open_button = QPushButton("打开选中任务")
        self.open_button.clicked.connect(self._open_selected_task)
        self.open_button.setMinimumHeight(40)
        self.open_button.setStyleSheet("font-size: 11pt; font-weight: 600; padding: 0 16px;")
        header_layout.addWidget(self.open_button)

        self.detail_button = QPushButton("查看详情")
        self.detail_button.clicked.connect(self._open_task_detail)
        self.detail_button.setMinimumHeight(40)
        self.detail_button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        header_layout.addWidget(self.detail_button)

        layout.addLayout(header_layout)

        self.table = QTableWidget(0, 5, self)
        self.table.setStyleSheet("QTableWidget { font-size: 11pt; } QHeaderView::section { font-size: 11pt; padding: 8px; }")
        self.table.setHorizontalHeaderLabels(["类型", "标题", "截止日期", "状态", "说明"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(lambda *_: self._open_selected_task())

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.tip_label = QLabel("双击任务可直接打开对应页面，病历检查任务会自动带上定位参数。")
        self.tip_label.setStyleSheet("font-size: 11pt; color: #666;")
        layout.addWidget(self.tip_label)

    def refresh_tasks(self, silent=False):
        try:
            self.tasks = self.api.get_pending_tasks()
            self._update_table()
            return True
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "刷新待办失败"):
                self.refresh_tasks(silent=silent)
                return True
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            self.summary_label.setText("待办加载失败")
            self.table.setRowCount(0)
            return False

    def _filtered_tasks(self):
        selected_type = self.type_filter.currentData()
        overdue_only = self.overdue_only.isChecked()
        result = []
        for task in self.tasks:
            if selected_type and task.get("type") != selected_type:
                continue
            if overdue_only and not task.get("is_overdue"):
                continue
            result.append(task)
        return result

    def _update_table(self):
        filtered_tasks = self._filtered_tasks()
        overdue_count = sum(1 for task in self.tasks if task.get("is_overdue"))
        self.summary_label.setText(f"当前待办 {len(self.tasks)} 项，逾期 {overdue_count} 项")

        self.table.setRowCount(len(filtered_tasks))
        for row_index, task in enumerate(filtered_tasks):
            self._set_cell(row_index, 0, TYPE_LABELS.get(task.get("type"), task.get("type") or "-"))
            self._set_cell(row_index, 1, task.get("title") or "")
            self._set_cell(row_index, 2, task.get("deadline") or "")
            self._set_cell(row_index, 3, "已逾期" if task.get("is_overdue") else "待处理")

            detail = task.get("description") or ""
            detail = detail.strip().replace("\n", "  ")
            if task.get("is_carryover"):
                detail = f"[结转] {detail}".strip()
            self._set_cell(row_index, 4, detail)

            self.table.item(row_index, 0).setData(Qt.UserRole, task)

        if filtered_tasks:
            self.table.selectRow(0)

    def _set_cell(self, row, column, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, column, item)

    def _selected_task(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _open_selected_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        if task.get("type") == "check" and task.get("check_task_kind") == "rectification":
            self.app_context.show_rectification_window(task)
            return
        self.app_context.open_task(task)

    def _open_task_detail(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        self.app_context.show_task_detail_window(task)

