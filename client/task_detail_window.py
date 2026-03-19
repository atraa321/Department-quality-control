from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
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


class TaskDetailWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.current_task = None
        self.current_check = None

        self.setWindowTitle("待办详情")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        width = int(self.config.get("task_detail_window_width", 780) or 780)
        height = int(self.config.get("task_detail_window_height", 560) or 560)
        self.resize(width, height)

        x = self.config.get("task_detail_window_x")
        y = self.config.get("task_detail_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.title_label = QLabel("请选择一条待办")
        self.title_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.title_label)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)

        self.type_label = QLabel("-")
        self.deadline_label = QLabel("-")
        self.status_label = QLabel("-")
        self.assignee_label = QLabel("-")
        self.record_no_label = QLabel("-")
        self.patient_name_label = QLabel("-")
        self.category_label = QLabel("-")
        self.doctor_label = QLabel("-")

        form_layout.addRow("任务类型：", self.type_label)
        form_layout.addRow("截止日期：", self.deadline_label)
        form_layout.addRow("任务状态：", self.status_label)
        form_layout.addRow("负责人：", self.assignee_label)
        form_layout.addRow("病案号：", self.record_no_label)
        form_layout.addRow("患者姓名：", self.patient_name_label)
        form_layout.addRow("问题分类：", self.category_label)
        form_layout.addRow("责任医师：", self.doctor_label)
        layout.addLayout(form_layout)

        layout.addWidget(QLabel("任务说明："))
        self.description_text = QTextEdit(self)
        self.description_text.setReadOnly(True)
        self.description_text.setMinimumHeight(90)
        layout.addWidget(self.description_text)

        layout.addWidget(QLabel("病历问题摘要："))
        self.check_summary_text = QTextEdit(self)
        self.check_summary_text.setReadOnly(True)
        layout.addWidget(self.check_summary_text)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.refresh_button = QPushButton("重新加载")
        self.refresh_button.clicked.connect(self.reload_current)
        button_layout.addWidget(self.refresh_button)
        self.rectify_button = QPushButton("快捷整改")
        self.rectify_button.clicked.connect(self.open_rectification)
        self.rectify_button.setVisible(False)
        button_layout.addWidget(self.rectify_button)
        self.open_button = QPushButton("打开对应页面")
        self.open_button.clicked.connect(self.open_target)
        button_layout.addWidget(self.open_button)
        layout.addLayout(button_layout)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["task_detail_window_x"] = pos.x()
        self.config["task_detail_window_y"] = pos.y()
        self.config["task_detail_window_width"] = size.width()
        self.config["task_detail_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def open_task(self, task):
        self.current_task = task
        self.show()
        self.raise_()
        self.activateWindow()
        self.load_task(task)

    def reload_current(self):
        if self.current_task:
            self.load_task(self.current_task)

    def open_target(self):
        if not self.current_task:
            QMessageBox.information(self, "提示", "当前没有可打开的任务")
            return
        self.app_context.open_task(self.current_task)

    def open_rectification(self):
        if not self.current_task or self.current_task.get("type") != "check":
            QMessageBox.information(self, "提示", "当前任务不支持快捷整改")
            return
        self.app_context.show_rectification_window(self.current_task)

    def load_task(self, task):
        self.current_task = task
        self.current_check = None
        self.title_label.setText(task.get("title") or "待办详情")
        self.type_label.setText(TYPE_LABELS.get(task.get("type"), task.get("type") or "-"))
        self.deadline_label.setText(task.get("deadline") or "-")
        self.status_label.setText("已逾期" if task.get("is_overdue") else "待处理")
        self.assignee_label.setText(task.get("assignee_name") or "当前用户")
        self.description_text.setPlainText(task.get("description") or "")
        self.rectify_button.setVisible(False)

        self._clear_check_fields()
        if task.get("type") != "check":
            self.check_summary_text.setPlainText("该任务没有关联病历整改信息。")
            return

        try:
            checks = self.api.list_checks(task_id=task.get("id"))
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载病历摘要失败"):
                self.load_task(task)
                return
            self.check_summary_text.setPlainText(f"加载病历摘要失败：{exc}")
            return

        if not checks:
            self.check_summary_text.setPlainText("未找到关联的病历问题记录。")
            return

        self.current_check = checks[0]
        self.record_no_label.setText(self.current_check.get("record_no") or "-")
        self.patient_name_label.setText(self.current_check.get("patient_name") or "-")
        self.category_label.setText(self.current_check.get("issue_category_label") or self.current_check.get("issue_category") or "-")
        self.doctor_label.setText(self.current_check.get("responsible_doctor_name") or "-")

        summary_lines = [
            f"整改状态：{'已整改' if self.current_check.get('is_rectified') else '待整改'}",
            f"预设问题：{self.current_check.get('issue_template') or '未选择'}",
            f"严重程度：{'严重问题' if self.current_check.get('severity') == 'serious' else '一般问题'}",
            f"发现问题：{self.current_check.get('issue_found') or '未填写'}",
            f"整改反馈：{self.current_check.get('rectification_feedback') or '未填写'}",
            f"备注：{self.current_check.get('remarks') or '无'}",
        ]
        self.check_summary_text.setPlainText("\n".join(summary_lines))
        self.rectify_button.setVisible(not self.current_check.get("is_rectified"))

    def _clear_check_fields(self):
        self.record_no_label.setText("-")
        self.patient_name_label.setText("-")
        self.category_label.setText("-")
        self.doctor_label.setText("-")

