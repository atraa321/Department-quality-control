from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import save_config


ROLE_LABELS = {
    "admin": "管理员",
    "doctor": "医师",
    "nurse": "护士",
}


class UserEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self._init_ui()

    def _init_ui(self):
        self.resize(420, 280)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.username_input = QLineEdit()
        self.real_name_input = QLineEdit()
        self.role_combo = QComboBox()
        for code, label in ROLE_LABELS.items():
            self.role_combo.addItem(label, code)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("留空则使用默认密码 123456")
        self.active_checkbox = QCheckBox("启用账号")
        self.active_checkbox.setChecked(True)

        form.addRow("用户名：", self.username_input)
        form.addRow("姓名：", self.real_name_input)
        form.addRow("角色：", self.role_combo)
        form.addRow("密码：", self.password_input)
        form.addRow("状态：", self.active_checkbox)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

    def open_for_create(self):
        self.user = None
        self.setWindowTitle("新增用户")
        self.username_input.setEnabled(True)
        self.username_input.clear()
        self.real_name_input.clear()
        self.role_combo.setCurrentIndex(1)
        self.password_input.clear()
        self.active_checkbox.setChecked(True)
        return self.exec_()

    def open_for_edit(self, user):
        self.user = user or {}
        self.setWindowTitle("编辑用户")
        self.username_input.setText(user.get("username") or "")
        self.username_input.setEnabled(False)
        self.real_name_input.setText(user.get("real_name") or "")
        self._set_combo_data(self.role_combo, user.get("role"))
        self.password_input.clear()
        self.password_input.setPlaceholderText("留空则不修改密码")
        self.active_checkbox.setChecked(bool(user.get("is_active")))
        return self.exec_()

    def get_payload(self):
        payload = {
            "username": self.username_input.text().strip(),
            "real_name": self.real_name_input.text().strip(),
            "role": self.role_combo.currentData(),
            "is_active": self.active_checkbox.isChecked(),
        }
        password = self.password_input.text()
        if self.user:
            if password:
                payload["password"] = password
        else:
            payload["password"] = password or "123456"
        return payload

    def _set_combo_data(self, combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)


class PasswordChangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("修改密码")
        self.resize(420, 220)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)

        form.addRow("原密码：", self.old_password_input)
        form.addRow("新密码：", self.new_password_input)
        form.addRow("确认密码：", self.confirm_password_input)
        layout.addLayout(form)

        hint = QLabel("新密码至少 4 位，仅修改当前登录账号密码。")
        hint.setStyleSheet("color: #64748b;")
        layout.addWidget(hint)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("确认修改")
        save_button.clicked.connect(self.accept)
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

    def open_dialog(self):
        self.old_password_input.clear()
        self.new_password_input.clear()
        self.confirm_password_input.clear()
        return self.exec_()

    def get_payload(self):
        return {
            "old_password": self.old_password_input.text(),
            "new_password": self.new_password_input.text(),
            "confirm_password": self.confirm_password_input.text(),
        }


class UserManageWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.users = []
        self.edit_dialog = UserEditDialog(self)
        self.password_dialog = PasswordChangeDialog(self)

        self.setWindowTitle("用户管理")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("user_manage_window_width", 1160) or 1160), int(self.config.get("user_manage_window_height", 720) or 720))
        x = self.config.get("user_manage_window_x")
        y = self.config.get("user_manage_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.summary_label = QLabel("用户数据加载中...")
        self.summary_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        filter_row = QHBoxLayout()
        self.role_filter = QComboBox()
        self.role_filter.addItem("全部角色", "")
        for code, label in ROLE_LABELS.items():
            self.role_filter.addItem(label, code)
        filter_row.addWidget(self.role_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", "")
        self.status_filter.addItem("启用", True)
        self.status_filter.addItem("禁用", False)
        filter_row.addWidget(self.status_filter)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("按用户名或姓名筛选")
        filter_row.addWidget(self.keyword_input, 1)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.refresh_content)
        filter_row.addWidget(query_button)

        change_password_button = QPushButton("修改我的密码")
        change_password_button.clicked.connect(self.change_my_password)
        filter_row.addWidget(change_password_button)

        create_button = QPushButton("新增用户")
        create_button.clicked.connect(self.create_user)
        filter_row.addWidget(create_button)
        layout.addLayout(filter_row)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["用户名", "姓名", "角色", "状态", "创建时间", "备注"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(lambda *_: self.edit_selected_user())
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        edit_button = QPushButton("编辑用户")
        edit_button.clicked.connect(self.edit_selected_user)
        reset_button = QPushButton("重置密码")
        reset_button.clicked.connect(self.reset_selected_password)
        button_row.addWidget(edit_button)
        button_row.addWidget(reset_button)
        button_row.addStretch()
        layout.addLayout(button_row)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["user_manage_window_x"] = pos.x()
        self.config["user_manage_window_y"] = pos.y()
        self.config["user_manage_window_width"] = size.width()
        self.config["user_manage_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_content(self, silent=False):
        user = self.config.get("user") or {}
        if user.get("role") != "admin":
            QMessageBox.warning(self, "无权限", "只有管理员可以使用用户管理页面")
            self.close()
            return

        try:
            users = self.api.list_users()
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "加载用户列表失败"):
                self.refresh_content(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            self.summary_label.setText("用户数据加载失败")
            return

        self.users = self._filter_users(users)
        self.summary_label.setText(f"当前共 {len(self.users)} 个用户")
        self._populate_table()

    def _filter_users(self, users):
        role_value = self.role_filter.currentData()
        status_value = self.status_filter.currentData()
        keyword = self.keyword_input.text().strip().lower()
        filtered = []
        for user in users or []:
            if role_value and user.get("role") != role_value:
                continue
            if status_value != "" and bool(user.get("is_active")) != status_value:
                continue
            searchable = f"{user.get('username') or ''} {user.get('real_name') or ''}".lower()
            if keyword and keyword not in searchable:
                continue
            filtered.append(user)
        return filtered

    def _populate_table(self):
        self.table.setRowCount(len(self.users))
        for row, user in enumerate(self.users):
            username_item = QTableWidgetItem(user.get("username") or "")
            username_item.setData(Qt.UserRole, user)
            self.table.setItem(row, 0, username_item)
            self.table.setItem(row, 1, QTableWidgetItem(user.get("real_name") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(ROLE_LABELS.get(user.get("role"), user.get("role") or "")))
            self.table.setItem(row, 3, QTableWidgetItem("启用" if user.get("is_active") else "禁用"))
            self.table.setItem(row, 4, QTableWidgetItem(user.get("created_at") or ""))
            note = "当前登录账号" if user.get("id") == (self.config.get("user") or {}).get("id") else ""
            self.table.setItem(row, 5, QTableWidgetItem(note))
        if self.users:
            self.table.selectRow(0)

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def create_user(self):
        if self.edit_dialog.open_for_create() != QDialog.Accepted:
            return
        payload = self.edit_dialog.get_payload()
        if not payload.get("username") or not payload.get("real_name"):
            QMessageBox.warning(self, "提示", "请填写用户名和姓名")
            return
        try:
            self.api.create_user(payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "创建用户失败")
            return
        self.refresh_content(silent=True)

    def edit_selected_user(self):
        user = self._selected_user()
        if not user:
            QMessageBox.information(self, "提示", "请先选择一名用户")
            return
        if self.edit_dialog.open_for_edit(user) != QDialog.Accepted:
            return
        payload = self.edit_dialog.get_payload()
        if not payload.get("real_name"):
            QMessageBox.warning(self, "提示", "请填写姓名")
            return
        payload.pop("username", None)
        try:
            self.api.update_user(user["id"], payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "更新用户失败")
            return
        self.refresh_content(silent=True)

    def reset_selected_password(self):
        user = self._selected_user()
        if not user:
            QMessageBox.information(self, "提示", "请先选择一名用户")
            return
        reply = QMessageBox.question(
            self,
            "重置密码",
            f"确认将 {user.get('real_name') or user.get('username')} 的密码重置为 123456 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.update_user(user["id"], {"password": "123456"})
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "重置密码失败")
            return
        QMessageBox.information(self, "完成", "密码已重置为 123456")

    def change_my_password(self):
        if self.password_dialog.open_dialog() != QDialog.Accepted:
            return
        payload = self.password_dialog.get_payload()
        if not payload.get("old_password") or not payload.get("new_password"):
            QMessageBox.warning(self, "提示", "请填写完整密码信息")
            return
        if payload["new_password"] != payload["confirm_password"]:
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return
        try:
            self.api.change_password(
                {
                    "old_password": payload["old_password"],
                    "new_password": payload["new_password"],
                }
            )
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "修改密码失败")
            return
        QMessageBox.information(self, "完成", "当前账号密码已更新")

