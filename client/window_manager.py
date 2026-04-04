from main_workspace_window import MainWorkspaceWindow
from check_window import CheckWindow
from discussion_window import DiscussionWindow
from followup_window import FollowupWindow
from patient_import_window import PatientImportWindow
from report_window import ReportWindow
from study_window import StudyWindow
from task_manage_window import TaskManageWindow
from user_manage_window import UserManageWindow
from todo_window import TodoWindow
from rectification_window import RectificationWindow
from task_detail_window import TaskDetailWindow


class WindowManager:
    def __init__(self, app_context):
        self.app_context = app_context
        self.main_workspace = None
        self.todo_window = None
        self.rectification_window = None
        self.task_detail_window = None
        self.page_windows = {}

    def show_main_workspace(self, section="dashboard"):
        created = False
        if self.main_workspace is None:
            self.main_workspace = MainWorkspaceWindow(self.app_context)
            self.main_workspace.destroyed.connect(lambda *_: self._clear_main_workspace())
            created = True

        self.main_workspace.open_section(section, refresh=False)
        if self.main_workspace.isMaximized():
            self.main_workspace.show()
        else:
            self.main_workspace.showMaximized()
        self.main_workspace.raise_()
        self.main_workspace.activateWindow()
        if created:
            self.main_workspace.schedule_section_refresh(section, delay_ms=120)
        elif self.main_workspace.should_auto_refresh_section(section):
            self.main_workspace.schedule_section_refresh(section, delay_ms=0)
        return self.main_workspace

    def show_page_window(self, key, factory):
        window = self.page_windows.get(key)
        if window is None:
            window = factory()
            window.destroyed.connect(lambda *_: self._clear_page_window(key))
            self.page_windows[key] = window

        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def show_todo_window(self):
        workspace = self.show_main_workspace(section="todo")
        page = workspace.get_section_page("todo")
        page.refresh_tasks(silent=True)
        return page

    def show_discussion_window(self, task=None, auto_create=False):
        workspace = self.show_main_workspace(section="discussions")
        window = workspace.get_section_page("discussions")
        window.open_for_task(task=task, auto_create=auto_create)
        return window

    def show_study_window(self, task=None, auto_create=False):
        workspace = self.show_main_workspace(section="studies")
        window = workspace.get_section_page("studies")
        window.open_for_task(task=task, auto_create=auto_create)
        return window

    def show_followup_window(self, task=None):
        workspace = self.show_main_workspace(section="followups")
        window = workspace.get_section_page("followups")
        window.open_for_task(task=task)
        return window

    def show_check_window(self, task=None, check_id=None):
        workspace = self.show_main_workspace(section="checks")
        window = workspace.get_section_page("checks")
        window.open_for_context(task=task, check_id=check_id)
        return window

    def show_task_manage_window(self):
        workspace = self.show_main_workspace(section="tasks")
        return workspace.get_section_page("tasks")

    def show_user_manage_window(self):
        workspace = self.show_main_workspace(section="users")
        return workspace.get_section_page("users")

    def show_report_window(self):
        workspace = self.show_main_workspace(section="reports")
        return workspace.get_section_page("reports")

    def show_patient_import_window(self):
        workspace = self.show_main_workspace(section="patients")
        return workspace.get_section_page("patients")

    def refresh_open_windows(self):
        if self.main_workspace is not None and self.main_workspace.isVisible():
            self.main_workspace.refresh_content(silent=True)
        if self.todo_window is not None and self.todo_window.isVisible():
            self.todo_window.refresh_tasks(silent=True)
        if self.rectification_window is not None and self.rectification_window.isVisible():
            self.rectification_window.reload_current()
        if self.task_detail_window is not None and self.task_detail_window.isVisible():
            self.task_detail_window.reload_current()

        for key, window in list(self.page_windows.items()):
            if window is None or not window.isVisible():
                continue
            refresh = getattr(window, "refresh_content", None)
            if callable(refresh):
                refresh(silent=True)

    def show_rectification_window(self, task):
        if self.rectification_window is None:
            self.rectification_window = RectificationWindow(self.app_context)
            self.rectification_window.destroyed.connect(lambda *_: self._clear_rectification_window())

        self.rectification_window.open_task(task)

    def show_task_detail_window(self, task):
        if self.task_detail_window is None:
            self.task_detail_window = TaskDetailWindow(self.app_context)
            self.task_detail_window.destroyed.connect(lambda *_: self._clear_task_detail_window())

        self.task_detail_window.open_task(task)

    def close_all_windows(self):
        for attr_name, clear_callback in (
            ("main_workspace", self._clear_main_workspace),
            ("todo_window", self._clear_todo_window),
            ("rectification_window", self._clear_rectification_window),
            ("task_detail_window", self._clear_task_detail_window),
        ):
            window = getattr(self, attr_name)
            if window is not None:
                window.close()
                clear_callback()

        for key, window in list(self.page_windows.items()):
            if window is not None:
                window.close()
            self._clear_page_window(key)

    def _clear_main_workspace(self):
        self.main_workspace = None

    def _clear_todo_window(self):
        self.todo_window = None

    def _clear_rectification_window(self):
        self.rectification_window = None

    def _clear_task_detail_window(self):
        self.task_detail_window = None

    def _clear_page_window(self, key):
        self.page_windows.pop(key, None)

