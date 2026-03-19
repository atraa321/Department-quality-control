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


class RectificationWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.current_task = None
        self.current_check = None

        self.setWindowTitle("整改确认")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        width = int(self.config.get("rectification_window_width", 760) or 760)
        height = int(self.config.get("rectification_window_height", 540) or 540)
        self.resize(width, height)

        x = self.config.get("rectification_window_x")
        y = self.config.get("rectification_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.header_label = QLabel("请选择一条病历整改任务")
        self.header_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.header_label)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)

        self.record_no_label = QLabel("-")
        self.patient_name_label = QLabel("-")
        self.category_label = QLabel("-")
        self.doctor_label = QLabel("-")
        self.deadline_label = QLabel("-")
        self.status_label = QLabel("-")
        self.template_label = QLabel("-")
        self.severity_label = QLabel("-")
        self.issue_label = QLabel("-")
        self.issue_label.setWordWrap(True)
        self.issue_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        form_layout.addRow("病案号：", self.record_no_label)
        form_layout.addRow("患者姓名：", self.patient_name_label)
        form_layout.addRow("问题分类：", self.category_label)
        form_layout.addRow("责任医师：", self.doctor_label)
        form_layout.addRow("截止时间：", self.deadline_label)
        form_layout.addRow("当前状态：", self.status_label)
        form_layout.addRow("预设问题：", self.template_label)
        form_layout.addRow("严重程度：", self.severity_label)
        form_layout.addRow("发现问题：", self.issue_label)
        layout.addLayout(form_layout)

        self.feedback_input = QTextEdit(self)
        self.feedback_input.setPlaceholderText("填写整改说明，确认后该病历问题将标记为已整改")
        self.feedback_input.setMinimumHeight(140)
        layout.addWidget(QLabel("整改反馈："))
        layout.addWidget(self.feedback_input)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_button = QPushButton("重新加载")
        self.refresh_button.clicked.connect(self.reload_current)
        button_layout.addWidget(self.refresh_button)

        self.open_check_button = QPushButton("返回检查页")
        self.open_check_button.clicked.connect(self.open_check_page)
        button_layout.addWidget(self.open_check_button)

        self.open_browser_button = QPushButton("在浏览器中打开")
        self.open_browser_button.clicked.connect(self.open_in_browser)
        button_layout.addWidget(self.open_browser_button)

        self.submit_button = QPushButton("确认整改")
        self.submit_button.clicked.connect(self.submit_rectification)
        button_layout.addWidget(self.submit_button)
        layout.addLayout(button_layout)

        self._set_empty_state()

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["rectification_window_x"] = pos.x()
        self.config["rectification_window_y"] = pos.y()
        self.config["rectification_window_width"] = size.width()
        self.config["rectification_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def open_task(self, task):
        self.current_task = task
        self.show()
        self.raise_()
        self.activateWindow()
        self.load_task(task)

    def load_task(self, task):
        self.current_task = task
        self.current_check = None
        self.header_label.setText(task.get("title") or "整改确认")

        try:
            checks = self.api.list_checks(task_id=task.get("id"))
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载整改信息失败"):
                self.load_task(task)
                return
            self._set_empty_state("无法加载整改信息")
            return

        if not checks:
            self._set_empty_state("未找到关联的病历问题记录")
            return

        self.current_check = checks[0]
        self._fill_check(self.current_check)

    def reload_current(self):
        if self.current_task:
            self.load_task(self.current_task)

    def open_in_browser(self):
        if self.current_task:
            self.app_context.open_task(self.current_task)

    def open_check_page(self):
        if not self.current_task and not self.current_check:
            return
        self.app_context.show_check_window(
            task=self.current_task,
            check_id=self.current_check.get("id") if self.current_check else None,
        )

    def submit_rectification(self):
        if not self.current_check:
            QMessageBox.information(self, "提示", "当前没有可提交的整改记录")
            return

        try:
            updated = self.api.update_check(self.current_check["id"], {
                "rectification_feedback": self.feedback_input.toPlainText().strip(),
                "is_rectified": True,
            })
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "提交整改失败")
            return

        self.current_check = updated
        self._fill_check(updated)
        self.app_context.refresh_overlay()
        QMessageBox.information(self, "完成", "整改状态已更新，检查页、待办和详情窗口已同步刷新")

    def _fill_check(self, check):
        self.record_no_label.setText(check.get("record_no") or "-")
        self.patient_name_label.setText(check.get("patient_name") or "-")
        self.category_label.setText(check.get("issue_category_label") or check.get("issue_category") or "-")
        self.doctor_label.setText(check.get("responsible_doctor_name") or "-")
        self.deadline_label.setText(self.current_task.get("deadline") if self.current_task else "-")
        self.status_label.setText("已整改" if check.get("is_rectified") else "待整改")
        self.template_label.setText(check.get("issue_template") or "未选择")
        self.severity_label.setText("严重问题" if check.get("severity") == "serious" else "一般问题")
        self.issue_label.setText(check.get("issue_found") or "未填写")
        self.feedback_input.setPlainText(check.get("rectification_feedback") or "")

        can_submit = not check.get("is_rectified")
        self.feedback_input.setReadOnly(not can_submit)
        self.submit_button.setEnabled(can_submit)

    def _set_empty_state(self, message="请选择一条病历整改任务"):
        self.record_no_label.setText("-")
        self.patient_name_label.setText("-")
        self.category_label.setText("-")
        self.doctor_label.setText("-")
        self.deadline_label.setText("-")
        self.status_label.setText("-")
        self.template_label.setText("-")
        self.severity_label.setText("-")
        self.issue_label.setText(message)
        self.feedback_input.setPlainText("")
        self.feedback_input.setReadOnly(True)
        self.submit_button.setEnabled(False)

