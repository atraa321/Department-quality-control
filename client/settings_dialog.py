from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QCheckBox, QMessageBox, QFileDialog,
    QComboBox,
    QFormLayout, QWidget, QFrame
)
from PyQt5.QtCore import Qt
import os


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("客户端设置")
        self.setFixedSize(720, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #f5f8fb;
            }
            QFrame#settingsCard {
                background: #ffffff;
                border: 1px solid #d9e4ee;
                border-radius: 14px;
            }
            QLabel {
                color: #243447;
                font-size: 11pt;
            }
            QLineEdit, QSpinBox, QComboBox {
                min-height: 36px;
                padding: 4px 10px;
                border: 1px solid #cfdbe6;
                border-radius: 8px;
                background: #ffffff;
                font-size: 11pt;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #2f7db2;
            }
            QPushButton {
                min-height: 36px;
                padding: 0 16px;
                border-radius: 8px;
                font-size: 11pt;
            }
            QCheckBox {
                font-size: 11pt;
                color: #243447;
                spacing: 8px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        card = QFrame(self)
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(16)

        title_label = QLabel("客户端设置")
        title_label.setStyleSheet("font-size: 15pt; font-weight: 700; color: #172534;")
        card_layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(14)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.server_input = QLineEdit(self.config.get("server_url", "http://localhost:5000"))
        self.server_input.setPlaceholderText("例如：http://127.0.0.1:5000")
        form.addRow("服务器地址：", self.server_input)

        browser_layout = QHBoxLayout()
        browser_layout.setSpacing(10)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        self.browser_input = QLineEdit(self.config.get("browser_path", ""))
        self.browser_input.setPlaceholderText("可选，Win7 推荐指定统一浏览器")
        self.browser_input.setFixedHeight(38)
        browser_layout.addWidget(self.browser_input)
        browse_btn = QPushButton("选择")
        browse_btn.setFixedWidth(92)
        browse_btn.setFixedHeight(38)
        browse_btn.clicked.connect(self.pick_browser)
        browser_layout.addWidget(browse_btn)
        browser_widget = QWidget(self)
        browser_widget.setLayout(browser_layout)
        browser_widget.setFixedHeight(38)
        form.addRow("固定浏览器路径：", browser_widget)

        self.compatibility_mode_input = QComboBox()
        self.compatibility_mode_input.setFixedHeight(38)
        self.compatibility_mode_input.addItem("自动识别（Win7 自动启用兼容优化）", "auto")
        self.compatibility_mode_input.addItem("标准模式", "standard")
        self.compatibility_mode_input.addItem("Win7 兼容模式", "win7")
        current_mode = str(self.config.get("compatibility_mode", "auto") or "auto").strip().lower()
        mode_index = self.compatibility_mode_input.findData(current_mode)
        self.compatibility_mode_input.setCurrentIndex(mode_index if mode_index >= 0 else 0)
        form.addRow("运行兼容档位：", self.compatibility_mode_input)

        self.refresh_input = QSpinBox()
        self.refresh_input.setRange(1, 60)
        self.refresh_input.setValue(int(self.config.get("overlay_refresh_minutes", 5) or 5))
        form.addRow("刷新间隔（分钟）：", self.refresh_input)

        self.max_items_input = QSpinBox()
        self.max_items_input.setRange(3, 20)
        self.max_items_input.setValue(int(self.config.get("overlay_max_items", 8) or 8))
        form.addRow("悬浮窗显示任务条数：", self.max_items_input)

        card_layout.addLayout(form)

        options_layout = QVBoxLayout()
        options_layout.setSpacing(12)

        self.summary_checkbox = QCheckBox("显示按业务类型汇总")
        self.summary_checkbox.setChecked(bool(self.config.get("overlay_show_summary", True)))
        options_layout.addWidget(self.summary_checkbox)

        self.topmost_checkbox = QCheckBox("透明提醒窗始终置顶")
        self.topmost_checkbox.setChecked(bool(self.config.get("overlay_always_on_top", True)))
        options_layout.addWidget(self.topmost_checkbox)
        card_layout.addLayout(options_layout)

        card_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            "QPushButton { background: #1976d2; color: white; border: none; }"
            "QPushButton:hover { background: #1565c0; }"
        )
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        card_layout.addLayout(btn_layout)

        layout.addWidget(card)

    def pick_browser(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择浏览器程序", self.browser_input.text().strip() or "", "程序 (*.exe);;所有文件 (*)")
        if path:
            self.browser_input.setText(path)

    def save_settings(self):
        server = self.server_input.text().strip()
        browser_path = self.browser_input.text().strip()
        if not server:
            QMessageBox.warning(self, "提示", "服务器地址不能为空")
            return
        if browser_path and not os.path.exists(browser_path):
            QMessageBox.warning(self, "提示", "固定浏览器路径不存在")
            return

        self.config["server_url"] = server
        self.config["browser_path"] = browser_path
        self.config["compatibility_mode"] = self.compatibility_mode_input.currentData()
        self.config["overlay_always_on_top"] = self.topmost_checkbox.isChecked()
        self.config["overlay_refresh_minutes"] = self.refresh_input.value()
        self.config["overlay_max_items"] = self.max_items_input.value()
        self.config["overlay_show_summary"] = self.summary_checkbox.isChecked()
        self.accept()
