from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class LoginDialog(QDialog):
    def __init__(self, api_client, config, parent=None):
        super().__init__(parent)
        self.api = api_client
        self.config = config
        self.user_data = None
        self.login_btn = None
        self.cancel_btn = None
        self.setWindowTitle("科室质控平台 - 登录")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui()
        self._lock_dialog_size()

    def _init_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #edf6ff,
                    stop: 0.52 #f7fbff,
                    stop: 1 #f4efe5
                );
            }
            QFrame#loginCard {
                background: rgba(255, 255, 255, 0.96);
                border: 1px solid rgba(129, 166, 201, 0.35);
                border-radius: 20px;
            }
            QLabel#brandBadge {
                color: #ffffff;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1b6ca8,
                    stop: 1 #49a078
                );
                border-radius: 28px;
                font-size: 18pt;
                font-weight: 700;
            }
            QLabel#titleLabel {
                color: #1f2a37;
                font-size: 22pt;
                font-weight: 700;
            }
            QLabel#subtitleLabel {
                color: #5f6f81;
                font-size: 12pt;
                line-height: 1.4;
            }
            QLabel#fieldLabel {
                color: #304256;
                font-size: 13pt;
                font-weight: 600;
                margin-bottom: 4px;
            }
            QLabel#hintLabel {
                color: #6f7f91;
                font-size: 12pt;
                background: #f2f7fb;
                border-radius: 12px;
                padding: 12px 14px;
            }
            QLineEdit {
                min-height: 28px;
                padding: 11px 14px;
                border: 1px solid #d7e2ec;
                border-radius: 12px;
                background: #fdfefe;
                color: #1f2a37;
                selection-background-color: #1b6ca8;
                font-size: 13pt;
            }
            QLineEdit:focus {
                border: 1px solid #2f7db2;
                background: #ffffff;
            }
            QLineEdit:hover {
                border: 1px solid #bfd3e3;
            }
            QPushButton {
                min-height: 24px;
                padding: 11px 18px;
                border-radius: 12px;
                font-size: 12pt;
                font-weight: 600;
            }
            QPushButton#loginButton {
                color: #ffffff;
                border: none;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1b6ca8,
                    stop: 1 #2d8d7f
                );
            }
            QPushButton#loginButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #165c90,
                    stop: 1 #25776b
                );
            }
            QPushButton#loginButton:disabled {
                background: #b7cad9;
                color: #eff4f8;
            }
            QPushButton#cancelButton {
                color: #35506a;
                border: 1px solid #d8e3ec;
                background: #ffffff;
            }
            QPushButton#cancelButton:hover {
                border: 1px solid #bfd0de;
                background: #f8fbfd;
            }
            """
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(24, 22, 24, 22)

        card = QFrame(self)
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        brand_badge = QLabel("QC", self)
        brand_badge.setObjectName("brandBadge")
        brand_badge.setAlignment(Qt.AlignCenter)
        brand_badge.setFixedSize(56, 56)
        header_layout.addWidget(brand_badge)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)

        title_label = QLabel("客户端登录")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("连接科室质控平台服务，进入桌面提醒与任务联动。")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setWordWrap(True)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout, 1)
        card_layout.addLayout(header_layout)

        hint_label = QLabel(
            "建议填写统一部署的服务器地址。"
            "如果后端和客户端都在同一台电脑，使用 http://127.0.0.1:5000 。"
            "登录成功后，客户端会记住本次连接配置。"
        )
        hint_label.setObjectName("hintLabel")
        hint_label.setWordWrap(True)
        card_layout.addWidget(hint_label)

        card_layout.addWidget(self._create_field_label("服务器地址"))
        self.server_input = QLineEdit(self.config.get("server_url", "http://localhost:5000"))
        self.server_input.setPlaceholderText("例如：http://192.168.1.20:5000")
        self.server_input.setClearButtonEnabled(True)
        card_layout.addWidget(self.server_input)

        card_layout.addWidget(self._create_field_label("用户名"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入账号")
        self.username_input.setClearButtonEnabled(True)
        card_layout.addWidget(self.username_input)

        card_layout.addWidget(self._create_field_label("密码"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.do_login)
        card_layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.login_btn = QPushButton("登录")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.clicked.connect(self.do_login)
        self.login_btn.setDefault(True)
        self.login_btn.setAutoDefault(True)
        button_layout.addWidget(self.login_btn, 1)
        card_layout.addLayout(button_layout)

        outer_layout.addWidget(card)

        self.server_input.textChanged.connect(self._update_login_button)
        self.username_input.textChanged.connect(self._update_login_button)
        self.password_input.textChanged.connect(self._update_login_button)
        self.username_input.setFocus()
        self._update_login_button()

    def _lock_dialog_size(self):
        target_size = self.sizeHint().expandedTo(QSize(560, 430))
        self.setMinimumSize(target_size)
        self.setMaximumSize(target_size)

    def _create_field_label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _update_login_button(self):
        ready = all([
            self.server_input.text().strip(),
            self.username_input.text().strip(),
            self.password_input.text(),
        ])
        self.login_btn.setEnabled(bool(ready))

    def do_login(self):
        server = self.server_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not server or not username or not password:
            QMessageBox.warning(self, "提示", "请填写完整信息")
            return

        self.api.server_url = server
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        self.cancel_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            data = self.api.login(username, password)
            self.user_data = data["user"]
            self.config["server_url"] = server
            self.config["token"] = self.api.token
            self.config["user"] = data["user"]
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "登录失败", str(e))
        finally:
            self.cancel_btn.setEnabled(True)
            self.login_btn.setText("登录")
            self._update_login_button()


