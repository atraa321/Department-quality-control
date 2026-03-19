from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QMenu
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush


class OverlayWidget(QWidget):
    """透明悬浮窗 - 显示任务提醒"""

    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_ctx = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.runtime_profile = app_context.runtime_profile
        self.tasks = []
        self._drag_pos = None

        self.setObjectName("overlayRoot")
        self.setWindowTitle("任务提醒")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self._apply_topmost_flag(initial=True)
        if self.runtime_profile.use_translucent_overlay:
            self.setAttribute(Qt.WA_TranslucentBackground)
        else:
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setStyleSheet(
                """
                QWidget#overlayRoot {
                    background-color: #20303d;
                    border: 1px solid #3f5668;
                    border-radius: 8px;
                }
                """
            )
        self.setMinimumSize(420, 130)
        self.resize(460, 240)

        # 恢复位置
        x = self.config.get("window_x", -1)
        y = self.config.get("window_y", -1)
        
        valid_pos = False
        if x != -1 and y != -1:
            for screen in QApplication.screens():
                geo = screen.availableGeometry()
                # 只要原先记录的中心点或者左上角在任意一个有效屏幕内，就认为是合法位置
                if geo.contains(x + 50, y + 50):
                    valid_pos = True
                    break
                    
        if valid_pos:
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            # 默认右下角，避免因历史坐标越界导致看不到窗口
            self.move(screen.right() - self.width() - 20, screen.bottom() - self.height() - 40)
            
        self._init_ui()
        self._start_timer()

    def _apply_topmost_flag(self, initial=False):
        should_topmost = bool(self.config.get("overlay_always_on_top", True))
        if initial:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, should_topmost)
            return

        was_visible = self.isVisible()
        geometry = self.geometry()
        if was_visible:
            self.hide()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, should_topmost)
        self.setGeometry(geometry)
        if was_visible:
            self.show()
            self.raise_()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(8)

        self.title_label = QLabel("任务提醒")
        self.title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #fff;")
        self.layout.addWidget(self.title_label)

        self.content_label = QLabel("正在加载...")
        self.content_label.setFont(QFont("Microsoft YaHei", 11))
        self.content_label.setStyleSheet("color: #eee;")
        self.content_label.setWordWrap(True)
        self.layout.addWidget(self.content_label)

        self.layout.addStretch()

        self.tip_label = QLabel("左键拖动，右键打开业务入口")
        self.tip_label.setFont(QFont("Microsoft YaHei", 10))
        self.tip_label.setStyleSheet("color: rgba(255,255,255,0.75);")
        self.layout.addWidget(self.tip_label)

    def paintEvent(self, event):
        if not self.runtime_profile.use_translucent_overlay:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        if self.runtime_profile.overlay_antialiasing:
            painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(30, 30, 50, 200)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            # 保存位置
            pos = self.pos()
            self.config["window_x"] = pos.x()
            self.config["window_y"] = pos.y()
            from config import save_config
            save_config(self.config)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        user = self.config.get("user") or {}
        display_name = user.get("real_name") or user.get("username") or "未登录"
        current_user_action = menu.addAction(f"当前用户：{display_name}")
        current_user_action.setEnabled(False)
        menu.addSeparator()
        menu.addAction("打开原生工作台").triggered.connect(self.app_ctx.show_main_workspace)
        menu.addAction("打开我的待办").triggered.connect(self.app_ctx.show_todo_window)
        menu.addSeparator()
        menu.addAction("进入疑难病例讨论").triggered.connect(lambda: self.app_ctx.show_workspace_section("discussions"))
        menu.addAction("进入业务学习").triggered.connect(lambda: self.app_ctx.show_workspace_section("studies"))
        menu.addAction("进入病历质控检查").triggered.connect(lambda: self.app_ctx.show_workspace_section("checks"))
        menu.addAction("进入出院患者回访").triggered.connect(lambda: self.app_ctx.show_workspace_section("followups"))

        if user.get("role") == "admin":
            menu.addSeparator()
            menu.addAction("进入任务分配").triggered.connect(lambda: self.app_ctx.show_workspace_section("tasks"))
            menu.addAction("进入出院患者导入").triggered.connect(lambda: self.app_ctx.show_workspace_section("patients"))
            menu.addAction("进入数据汇总").triggered.connect(lambda: self.app_ctx.show_workspace_section("reports"))
            menu.addAction("进入用户管理").triggered.connect(lambda: self.app_ctx.show_workspace_section("users"))

        menu.addSeparator()
        browser_menu = menu.addMenu("浏览器备用入口")
        browser_menu.addAction("浏览器打开工作台").triggered.connect(lambda: self.app_ctx.open_browser("/dashboard"))
        browser_menu.addAction("浏览器打开疑难病例讨论").triggered.connect(lambda: self.app_ctx.open_browser("/discussions"))
        browser_menu.addAction("浏览器打开业务学习").triggered.connect(lambda: self.app_ctx.open_browser("/studies"))
        browser_menu.addAction("浏览器打开病历质控检查").triggered.connect(lambda: self.app_ctx.open_browser("/checks"))
        browser_menu.addAction("浏览器打开出院患者回访").triggered.connect(lambda: self.app_ctx.open_browser("/followups"))
        if user.get("role") == "admin":
            browser_menu.addAction("浏览器打开任务分配").triggered.connect(lambda: self.app_ctx.open_browser("/tasks"))
            browser_menu.addAction("浏览器打开出院患者导入").triggered.connect(lambda: self.app_ctx.open_browser("/patients"))
            browser_menu.addAction("浏览器打开数据汇总").triggered.connect(lambda: self.app_ctx.open_browser("/reports"))
            browser_menu.addAction("浏览器打开用户管理").triggered.connect(lambda: self.app_ctx.open_browser("/users"))

        menu.addSeparator()
        menu.addAction("客户端设置").triggered.connect(self.app_ctx.open_settings)
        menu.addAction("立即刷新任务").triggered.connect(self.refresh_tasks)
        menu.addAction("切换用户").triggered.connect(self.app_ctx.switch_user)
        menu.addAction("退出登录").triggered.connect(self.app_ctx.logout)
        menu.addAction("隐藏提醒窗").triggered.connect(self.hide)
        menu.exec_(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.app_ctx.show_todo_window()
            event.accept()

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_tasks)
        self._apply_timer_interval()
        # 立即刷新一次
        QTimer.singleShot(500, self.refresh_tasks)

    def _apply_timer_interval(self):
        interval_minutes = max(int(self.config.get("overlay_refresh_minutes", 5) or 5), 1)
        self.timer.start(interval_minutes * 60 * 1000)

    def apply_settings(self):
        self._apply_topmost_flag()
        self._apply_timer_interval()
        self.refresh_tasks()

    def refresh_tasks(self):
        if not self.app_ctx.is_logged_in():
            self.show_logged_out_state()
            return
        try:
            self.tasks = self.api.get_pending_tasks()
            self._update_display()
        except Exception as exc:
            if self.app_ctx.handle_api_error(exc, self, "刷新待办失败"):
                self.refresh_tasks()
                return
            if self.app_ctx.is_logged_in():
                self.content_label.setText("无法连接服务器...")
            else:
                self.show_logged_out_state()

    def show_logged_out_state(self):
        self.tasks = []
        self.title_label.setText("任务提醒")
        self.content_label.setText("当前未登录，右键可切换用户或重新登录。")
        self.resize(460, 130)

    def _update_display(self):
        if not self.tasks:
            self.content_label.setText("当前暂无待办任务")
            self.resize(460, 130)
            return

        type_labels = {
            "discussion": "病例讨论",
            "study": "业务学习",
            "check": "病历检查",
            "followup": "患者回访",
        }
        summary = {}
        for task in self.tasks:
            task_type = task.get("type", "")
            summary[task_type] = summary.get(task_type, 0) + 1

        lines = []
        overdue_count = 0
        max_items = max(int(self.config.get("overlay_max_items", 8) or 8), 3)
        for t in self.tasks[:max_items]:
            prefix = "[逾期]" if t.get("is_overdue") else "[待办]"
            if t.get("is_overdue"):
                overdue_count += 1
            deadline = t.get("deadline", "")
            lines.append(f"{prefix} {t['title']}  [{deadline}]")

        if len(self.tasks) > max_items:
            lines.append(f"... 还有 {len(self.tasks) - max_items} 条任务")

        self.title_label.setText(f"待办任务 {len(self.tasks)} 项 | 过期 {overdue_count} 项")

        show_summary = bool(self.config.get("overlay_show_summary", True))
        summary_text = " | ".join(
            f"{type_labels.get(task_type, task_type)} {count}"
            for task_type, count in summary.items()
        )
        text = "\n".join(lines)
        if show_summary and summary_text:
            text = f"{summary_text}\n\n{text}"
        self.content_label.setText(text)
        # 自适应高度
        height = 110 + len(lines) * 28
        self.resize(460, min(height, 420))

