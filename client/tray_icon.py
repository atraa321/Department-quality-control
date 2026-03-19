from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QApplication


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标"""

    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.ctx = app_context  # main.py中的AppContext

        # 设置图标（使用默认图标）
        icon = QApplication.style().standardIcon(QApplication.style().SP_ComputerIcon)
        self.setIcon(icon)
        self.setToolTip("科室质控平台")

        self._create_menu()
        self.activated.connect(self._on_activated)
        self.show()

    def _create_menu(self):
        menu = QMenu()

        user = self.ctx.config.get("user") or {}
        display_name = user.get("real_name") or user.get("username") or "未登录"
        current_user_action = menu.addAction(f"当前用户：{display_name}")
        current_user_action.setEnabled(False)
        menu.addSeparator()

        menu.addAction("打开原生工作台").triggered.connect(self.ctx.show_main_workspace)
        menu.addAction("打开我的待办").triggered.connect(self.ctx.show_todo_window)
        menu.addSeparator()
        menu.addAction("进入疑难病例讨论").triggered.connect(lambda: self.ctx.show_workspace_section("discussions"))
        menu.addAction("进入业务学习").triggered.connect(lambda: self.ctx.show_workspace_section("studies"))
        menu.addAction("进入病历质控检查").triggered.connect(lambda: self.ctx.show_workspace_section("checks"))
        menu.addAction("进入出院患者回访").triggered.connect(lambda: self.ctx.show_workspace_section("followups"))
        menu.addSeparator()

        if user and user.get("role") == "admin":
            menu.addAction("进入任务分配").triggered.connect(lambda: self.ctx.show_workspace_section("tasks"))
            menu.addAction("进入出院患者导入").triggered.connect(lambda: self.ctx.show_workspace_section("patients"))
            menu.addAction("进入数据汇总").triggered.connect(lambda: self.ctx.show_workspace_section("reports"))
            menu.addAction("进入用户管理").triggered.connect(lambda: self.ctx.show_workspace_section("users"))
            menu.addSeparator()

        browser_menu = menu.addMenu("浏览器备用入口")
        browser_menu.addAction("浏览器打开工作台").triggered.connect(lambda: self.ctx.open_browser("/dashboard"))
        browser_menu.addAction("浏览器打开疑难病例讨论").triggered.connect(lambda: self.ctx.open_browser("/discussions"))
        browser_menu.addAction("浏览器打开业务学习").triggered.connect(lambda: self.ctx.open_browser("/studies"))
        browser_menu.addAction("浏览器打开病历质控检查").triggered.connect(lambda: self.ctx.open_browser("/checks"))
        browser_menu.addAction("浏览器打开出院患者回访").triggered.connect(lambda: self.ctx.open_browser("/followups"))
        if user and user.get("role") == "admin":
            browser_menu.addAction("浏览器打开任务分配").triggered.connect(lambda: self.ctx.open_browser("/tasks"))
            browser_menu.addAction("浏览器打开出院患者导入").triggered.connect(lambda: self.ctx.open_browser("/patients"))
            browser_menu.addAction("浏览器打开数据汇总").triggered.connect(lambda: self.ctx.open_browser("/reports"))
            browser_menu.addAction("浏览器打开用户管理").triggered.connect(lambda: self.ctx.open_browser("/users"))
        menu.addSeparator()

        menu.addAction("立即刷新任务").triggered.connect(self.ctx.refresh_overlay)
        menu.addAction("显示/隐藏提醒窗").triggered.connect(self.ctx.toggle_overlay)
        menu.addAction("客户端设置").triggered.connect(self.ctx.open_settings)
        menu.addAction("切换用户").triggered.connect(self.ctx.switch_user)
        menu.addAction("退出登录").triggered.connect(self.ctx.logout)
        menu.addSeparator()
        ops_menu = menu.addMenu("运行控制")
        ops_menu.addAction("启动服务端").triggered.connect(self.ctx.start_server_runtime)
        ops_menu.addAction("启动客户端").triggered.connect(self.ctx.start_client_runtime)
        ops_menu.addAction("停止全部").triggered.connect(self.ctx.stop_all_runtime)
        ops_menu.addAction("重启全部").triggered.connect(self.ctx.restart_all_runtime)
        menu.addSeparator()
        menu.addAction("退出").triggered.connect(self.ctx.quit_app)

        self.setContextMenu(menu)

    def refresh_menu(self):
        self._create_menu()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.ctx.show_main_workspace()

