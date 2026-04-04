from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from async_worker import start_async_task


TYPE_LABELS = {
    "discussion": "病例讨论",
    "study": "业务学习",
    "check": "病历检查",
    "followup": "患者回访",
}
DEFAULT_TIP_TEXT = "双击任务可直接处理；病历整改任务会进入原生整改窗口，其余任务按当前原生化进度路由。"
LEGACY_TIP_TEXT = "当前服务端版本较旧，首页已自动降级为待办概览；已完成任务和待回访患者暂不统计。"


class DashboardPage(QWidget):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.tasks = []
        self._refresh_token = 0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(22)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(18)
        summary_grid.setVerticalSpacing(18)

        self.pending_card = self._create_card("当前待办", "--", "待完成任务")
        self.overdue_card = self._create_card("逾期任务", "--", "需优先处理")
        self.completed_card = self._create_card("已完成任务", "--", "来自任务中心")
        self.followup_card = self._create_card("待回访患者", "--", "按当前角色统计")

        summary_grid.addWidget(self.pending_card, 0, 0)
        summary_grid.addWidget(self.overdue_card, 0, 1)
        summary_grid.addWidget(self.completed_card, 1, 0)
        summary_grid.addWidget(self.followup_card, 1, 1)
        layout.addLayout(summary_grid)

        actions_frame = QFrame()
        actions_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 14px; }")
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(22, 22, 22, 22)
        actions_layout.setSpacing(16)

        actions_title = QLabel("快捷入口")
        actions_title.setStyleSheet("font-size: 16pt; font-weight: 700; color: #0f172a;")
        actions_layout.addWidget(actions_title)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        todo_button = QPushButton("打开我的待办")
        todo_button.clicked.connect(self.app_context.show_todo_window)
        todo_button.setMinimumHeight(40)
        todo_button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        button_row.addWidget(todo_button)

        detail_button = QPushButton("查看任务详情")
        detail_button.clicked.connect(self._open_selected_detail)
        detail_button.setMinimumHeight(40)
        detail_button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        button_row.addWidget(detail_button)

        handle_button = QPushButton("处理选中任务")
        handle_button.clicked.connect(self._open_selected_task)
        handle_button.setMinimumHeight(40)
        handle_button.setStyleSheet("font-size: 11pt; font-weight: 600; padding: 0 16px;")
        button_row.addWidget(handle_button)

        fallback_button = QPushButton("浏览器备用入口")
        fallback_button.clicked.connect(lambda: self.app_context.open_browser("/dashboard"))
        fallback_button.setMinimumHeight(40)
        fallback_button.setStyleSheet("font-size: 11pt; padding: 0 16px;")
        button_row.addWidget(fallback_button)

        button_row.addStretch()
        actions_layout.addLayout(button_row)

        self.summary_label = QLabel("最近任务：加载中...")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 13pt; color: #334155; line-height: 1.8;")
        actions_layout.addWidget(self.summary_label)

        self.task_table = QTableWidget(0, 4, self)
        self.task_table.setStyleSheet("QTableWidget { font-size: 11pt; } QHeaderView::section { font-size: 11pt; padding: 8px; }")
        self.task_table.setHorizontalHeaderLabels(["类型", "标题", "截止日期", "状态"])
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SingleSelection)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setMinimumHeight(200)  # 至少保证显示4条左右的任务以及表头
        self.task_table.itemDoubleClicked.connect(lambda *_: self._open_selected_task())

        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        actions_layout.addWidget(self.task_table)

        self.tip_label = QLabel(DEFAULT_TIP_TEXT)
        self.tip_label.setStyleSheet("font-size: 11pt; color: #64748b;")
        actions_layout.addWidget(self.tip_label)

        layout.addWidget(actions_frame, 1)

    def refresh_content(self, silent=False):
        self._refresh_token += 1
        token = self._refresh_token
        self.summary_label.setText("最近任务：加载中...")

        def load():
            return self.api.get_dashboard_summary()

        def on_success(payload):
            if token != self._refresh_token:
                return
            pending_tasks = payload.get("pending_tasks") or []
            stats = payload.get("stats") or {}
            self.tip_label.setText(LEGACY_TIP_TEXT if payload.get("legacy_fallback") else DEFAULT_TIP_TEXT)
            self.tasks = pending_tasks[:8]

            self.pending_card.value_label.setText(str(stats.get("pending_tasks", 0)))
            self.overdue_card.value_label.setText(str(stats.get("overdue_tasks", 0)))
            self.completed_card.value_label.setText(str(stats.get("completed_tasks", 0)))
            self.followup_card.value_label.setText(str(stats.get("pending_followups", 0)))
            self.summary_label.setText(self._format_summary(pending_tasks, stats.get("overdue_tasks", 0)))
            self._populate_table()

        def on_error(exc):
            if token != self._refresh_token:
                return
            if self.app_context.handle_api_error(exc, self, "刷新 Dashboard 失败"):
                self.refresh_content(silent=silent)
                return
            self.tasks = []
            self._reset_cards()
            self.summary_label.setText("最近任务：无法获取服务器数据。")
            self.tip_label.setText(DEFAULT_TIP_TEXT)
            self.task_table.setRowCount(0)
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))

        start_async_task(self, load, on_success, on_error)
        return True

    def _populate_table(self):
        self.task_table.setRowCount(len(self.tasks))
        for row_index, task in enumerate(self.tasks):
            self._set_cell(row_index, 0, TYPE_LABELS.get(task.get("type"), task.get("type") or "-"), task)
            self._set_cell(row_index, 1, task.get("title") or "")
            self._set_cell(row_index, 2, task.get("deadline") or "")
            self._set_cell(row_index, 3, "已逾期" if task.get("is_overdue") else "待处理")

        if self.tasks:
            self.task_table.selectRow(0)

    def _set_cell(self, row, column, text, task=None):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if task is not None:
            item.setData(Qt.UserRole, task)
        self.task_table.setItem(row, column, item)

    def _selected_task(self):
        row = self.task_table.currentRow()
        if row < 0:
            return None
        item = self.task_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _open_selected_task(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        self.app_context.open_task(task)

    def _open_selected_detail(self):
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "提示", "请先选择一条任务")
            return
        self.app_context.show_task_detail_window(task)

    def _format_summary(self, tasks, overdue_count):
        if not tasks:
            return "最近任务：当前暂无待办。"
        return f"最近任务：共 {len(tasks)} 项，逾期 {overdue_count} 项，显示最早截止的 8 条。"

    def _reset_cards(self):
        for card in (self.pending_card, self.overdue_card, self.completed_card, self.followup_card):
            card.value_label.setText("--")

    def _create_card(self, title, value, subtitle):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 14px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12pt; color: #64748b; font-weight: 600;")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 22pt; color: #0f172a; font-weight: 700;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 11pt; color: #94a3b8;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)

        frame.value_label = value_label
        frame.subtitle_label = subtitle_label
        return frame
