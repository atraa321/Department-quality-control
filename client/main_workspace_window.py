from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from check_window import CheckWindow
from dashboard_page import DashboardPage
from discussion_window import DiscussionWindow
from followup_window import FollowupWindow
from patient_import_window import PatientImportWindow
from report_window import ReportWindow
from study_window import StudyWindow
from task_manage_window import TaskManageWindow
from todo_panel import TodoPanel
from user_manage_window import UserManageWindow


ROLE_LABELS = {
    "admin": "管理员",
    "doctor": "医生",
    "nurse": "护士",
}


SECTION_DEFINITIONS = {
    "dashboard": {
        "title": "工作台首页",
        "description": "查看当前登录状态、待办概况和高频入口。",
        "browser_path": "/dashboard",
    },
    "todo": {
        "title": "我的待办",
        "description": "进入已原生化的待办、整改和详情处理流程。",
        "browser_path": "/dashboard",
    },
    "discussions": {
        "title": "疑难病例讨论",
        "description": "已支持原生列表、详情、编辑、删除和 Word 导出。",
        "browser_path": "/discussions",
    },
    "studies": {
        "title": "业务学习",
        "description": "已支持原生列表、详情、编辑、删除和 Word 导出。",
        "browser_path": "/studies",
    },
    "checks": {
        "title": "病历质控检查",
        "description": "已支持原生列表、日期筛选、整改状态筛选和任务定位。",
        "browser_path": "/checks",
    },
    "followups": {
        "title": "出院患者回访",
        "description": "已支持待回访患者、回访记录、统计摘要和角色权限控制。",
        "browser_path": "/followups",
    },
    "tasks": {
        "title": "任务分配",
        "description": "已支持原生任务筛选、批量分配、编辑、单删和批量删除。",
        "browser_path": "/tasks",
    },
    "patients": {
        "title": "出院患者导入",
        "description": "已支持原生文件预览、列映射、正式导入、模板下载、备份和批次管理。",
        "browser_path": "/patients",
    },
    "reports": {
        "title": "数据汇总",
        "description": "已支持原生汇总查询、检查统计表和 Excel/Word 导出。",
        "browser_path": "/reports",
    },
    "users": {
        "title": "用户管理",
        "description": "已支持原生用户列表、新增、编辑、重置密码和当前账号改密。",
        "browser_path": "/users",
    },
}


class MainWorkspaceWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.current_section = "dashboard"
        self._nav_items = {}
        self._section_pages = {}

        self.setWindowTitle("科室质控平台")
        self.resize(1180, 760)
        self._init_ui()
        self.refresh_content(silent=True)

    def _style_action_button(self, button, primary=False):
        button.setMinimumHeight(42)
        if primary:
            button.setStyleSheet(
                "QPushButton { background: #1d4ed8; color: white; border: none; border-radius: 10px; "
                "padding: 0 18px; font-size: 11pt; font-weight: 600; }"
                "QPushButton:hover { background: #1e40af; }"
            )
        else:
            button.setStyleSheet(
                "QPushButton { background: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 10px; "
                "padding: 0 18px; font-size: 11pt; font-weight: 600; }"
                "QPushButton:hover { background: #f8fafc; }"
            )

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(260)
        self.nav_list.setStyleSheet(
            "QListWidget { background: #0f172a; color: #e2e8f0; border: none; padding: 16px 0; font-size: 13pt; }"
            "QListWidget::item { padding: 18px 22px; margin: 4px 12px; border-radius: 10px; min-height: 26px; }"
            "QListWidget::item:selected { background: #1d4ed8; color: white; }"
        )
        self.nav_list.currentItemChanged.connect(self._handle_nav_changed)
        layout.addWidget(self.nav_list)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 28, 30, 28)
        content_layout.setSpacing(22)
        layout.addWidget(content, 1)

        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)
        self.page_title_label = QLabel("工作台首页")
        self.page_title_label.setStyleSheet("font-size: 22pt; font-weight: 700; color: #0f172a;")
        self.page_desc_label = QLabel("统一工作台已接管客户端主入口。")
        self.page_desc_label.setStyleSheet("font-size: 14pt; color: #475569;")
        title_layout.addWidget(self.page_title_label)
        title_layout.addWidget(self.page_desc_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        user_layout = QVBoxLayout()
        user_layout.setSpacing(8)
        self.user_label = QLabel()
        self.user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.user_label.setStyleSheet("font-size: 13pt; font-weight: 600; color: #0f172a;")
        self.status_label = QLabel("状态：准备就绪")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setStyleSheet("font-size: 11pt; color: #64748b;")
        user_layout.addWidget(self.user_label)
        user_layout.addWidget(self.status_label)
        header_layout.addLayout(user_layout)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_content)
        self._style_action_button(self.refresh_button)
        header_layout.addWidget(self.refresh_button)

        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.app_context.open_settings)
        self._style_action_button(self.settings_button)
        header_layout.addWidget(self.settings_button)

        self.browser_button = QPushButton("浏览器打开")
        self.browser_button.clicked.connect(self._open_current_section_in_browser)
        self._style_action_button(self.browser_button)
        header_layout.addWidget(self.browser_button)

        self.switch_user_button = QPushButton("切换用户")
        self.switch_user_button.clicked.connect(self.app_context.switch_user)
        self._style_action_button(self.switch_user_button)
        header_layout.addWidget(self.switch_user_button)
        content_layout.addLayout(header_layout)

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage(self.app_context, self)
        self.todo_page = TodoPanel(self.app_context, self)
        self._section_pages["dashboard"] = self.dashboard_page
        self._section_pages["todo"] = self.todo_page
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.todo_page)
        content_layout.addWidget(self.stack, 1)

        self._rebuild_navigation()

    def _rebuild_navigation(self):
        self.nav_list.blockSignals(True)
        self.nav_list.clear()
        self._nav_items = {}

        user = self.config.get("user") or {}
        role = user.get("role")
        sections = ["dashboard", "todo", "discussions", "studies", "checks", "followups"]
        if role == "admin":
            sections.extend(["tasks", "patients", "reports", "users"])

        for key in sections:
            item = QListWidgetItem(SECTION_DEFINITIONS[key]["title"])
            item.setData(Qt.UserRole, key)
            self.nav_list.addItem(item)
            self._nav_items[key] = item

        self.nav_list.blockSignals(False)
        if self.current_section not in self._nav_items:
            self.current_section = "dashboard"
        self.open_section(self.current_section, refresh=False)

    def get_section_page(self, section):
        return self._ensure_section_page(section)

    def open_section(self, section, refresh=True):
        if section not in self._nav_items:
            section = "dashboard"

        self.current_section = section
        item = self._nav_items[section]
        if self.nav_list.currentItem() is not item:
            self.nav_list.blockSignals(True)
            self.nav_list.setCurrentItem(item)
            self.nav_list.blockSignals(False)

        self._apply_section(section, refresh=refresh)

    def refresh_content(self, silent=False):
        user = self.config.get("user") or {}
        display_name = user.get("real_name") or user.get("username") or "未登录"
        role = ROLE_LABELS.get(user.get("role"), user.get("role") or "未知角色")
        self.user_label.setText(f"{display_name} | {role}")
        self.status_label.setText("状态：准备就绪")
        self._rebuild_navigation()
        refreshed = self._refresh_section(self.current_section, silent=silent)
        self.status_label.setText("状态：已同步最新数据" if refreshed else "状态：同步失败")

    def _handle_nav_changed(self, current, previous):
        if current is None:
            return
        self.open_section(current.data(Qt.UserRole))

    def _apply_section(self, section, refresh=True):
        definition = SECTION_DEFINITIONS[section]
        self.page_title_label.setText(definition["title"])
        self.page_desc_label.setText(definition["description"])
        self.browser_button.setVisible(bool(definition.get("browser_path")))
        self.stack.setCurrentWidget(self._ensure_section_page(section))
        if refresh:
            self._refresh_section(section, silent=True)

    def _ensure_section_page(self, section):
        page = self._section_pages.get(section)
        if page is not None:
            return page

        page = self._create_section_page(section)
        page.setParent(self.stack)
        page.setWindowFlags(Qt.Widget)
        self._section_pages[section] = page
        self.stack.addWidget(page)
        return page

    def _create_section_page(self, section):
        if section == "discussions":
            return DiscussionWindow(self.app_context, self)
        if section == "studies":
            return StudyWindow(self.app_context, self)
        if section == "checks":
            return CheckWindow(self.app_context, self)
        if section == "followups":
            return FollowupWindow(self.app_context, self)
        if section == "tasks":
            return TaskManageWindow(self.app_context, self)
        if section == "patients":
            return PatientImportWindow(self.app_context, self)
        if section == "reports":
            return ReportWindow(self.app_context, self)
        if section == "users":
            return UserManageWindow(self.app_context, self)
        if section == "todo":
            return self.todo_page
        return self.dashboard_page

    def _refresh_section(self, section, silent=False):
        page = self._ensure_section_page(section)
        try:
            if section == "dashboard":
                return bool(page.refresh_content(silent=silent))
            if section == "todo":
                page.refresh_tasks(silent=silent)
                return True

            refresh = getattr(page, "refresh_content", None)
            if not callable(refresh):
                return True
            try:
                result = refresh(silent=silent)
            except TypeError:
                result = refresh()
            return True if result is None else bool(result)
        except Exception:
            return False

    def _open_current_section_in_browser(self):
        definition = SECTION_DEFINITIONS.get(self.current_section, {})
        path = definition.get("browser_path")
        if path:
            self.app_context.open_browser(path)
