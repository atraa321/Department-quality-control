import sys
import os
import subprocess
import traceback
import json
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# 确保当前目录在path中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, save_config
from runtime_profile import build_runtime_profile, preferred_browser_paths

BOOT_CONFIG = load_config()
RUNTIME_PROFILE = build_runtime_profile(BOOT_CONFIG)
START_HIDDEN = any(arg == "--start-hidden" for arg in sys.argv[1:])


def _prepare_qt_runtime(runtime_profile):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if runtime_profile.enable_high_dpi_scaling:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
        os.environ.pop("QT_SCALE_FACTOR", None)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ.pop("QT_SCALE_FACTOR_ROUNDING_POLICY", None)
    if runtime_profile.use_software_opengl:
        os.environ["QT_OPENGL"] = "software"

    try:
        import PyQt5
    except Exception:
        return

    pyqt_dir = os.path.dirname(PyQt5.__file__)
    plugin_candidates = [
        os.path.join(pyqt_dir, "Qt5", "plugins"),
        os.path.join(pyqt_dir, "Qt", "plugins"),
        os.path.join(pyqt_dir, "plugins"),
    ]
    for plugin_path in plugin_candidates:
        if os.path.exists(plugin_path):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
            os.environ["QT_PLUGIN_PATH"] = plugin_path
            break

    # 兼容从项目根目录直接启动时的相对资源定位
    os.chdir(base_dir)


_prepare_qt_runtime(RUNTIME_PROFILE)

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from api_client import ApiClient, ApiError
from login_dialog import LoginDialog
from overlay_widget import OverlayWidget
from settings_dialog import SettingsDialog
from tray_icon import TrayIcon
from window_manager import WindowManager


class AppContext:
    """应用上下文，管理所有窗口和状态"""

    def __init__(self):
        self.runtime_profile = RUNTIME_PROFILE
        self.start_hidden = START_HIDDEN
        if self.runtime_profile.enable_high_dpi_scaling and hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy") and hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor)
        if self.runtime_profile.enable_high_dpi_scaling:
            if hasattr(Qt, "AA_EnableHighDpiScaling"):
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            if hasattr(Qt, "AA_UseHighDpiPixmaps"):
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        elif hasattr(Qt, "AA_DisableHighDpiScaling"):
            QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
        if self.runtime_profile.use_software_opengl:
            QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出

        from PyQt5.QtGui import QFont
        # 用 pt(点数) 替代硬编码 px 来配置全局字体，完美适配高 DPI 屏幕缩放
        app_font = QFont("Microsoft YaHei", 11)
        self.app.setFont(app_font)

        # 全局样式优化：保留输入框放大和现代化属性，去除对字体大小的强制改变
        self.app.setStyleSheet("""
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QDateTimeEdit {
                padding: 6px 10px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #ffffff;
                selection-background-color: #0078d7;
                min-height: 28px;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {
                border: 1px solid #0078d7;
                outline: none;
            }
            QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {
                background-color: #f5f5f5;
                color: #888888;
            }
            QPushButton {
                padding: 6px 16px;
                border-radius: 4px;
                border: 1px solid #cccccc;
                background-color: #f8f9fa;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #e2e6ea;
            }
            QPushButton[text="登录"], QPushButton[text="保存"], QPushButton[text="确认"], QPushButton[type="primary"] {
                background-color: #0078d7;
                color: white;
                border: none;
            }
            QPushButton[text="登录"]:hover, QPushButton[text="保存"]:hover, QPushButton[text="确认"]:hover {
                background-color: #005a9e;
            }
            QTableView {
                gridline-color: #e0e0e0;
                selection-background-color: #e6f2ff;
                selection-color: #000000;
                alternate-background-color: #fafafa;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                padding: 6px;
                border: none;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
                color: #333333;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)

        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config = dict(BOOT_CONFIG)
        self.api = ApiClient(self.config["server_url"], self.config.get("token", ""))
        self.overlay = None
        self.tray = None
        self.window_manager = WindowManager(self)

    def run(self):
        # 登录
        if not self._try_auto_login() and not self._show_login_dialog():
            return  # 用户取消

        if not self.start_hidden:
            self.window_manager.show_main_workspace()

        self._register_client_pid()
        self._schedule_shell_components_initialization()

        return self.app.exec_()

    def _try_auto_login(self):
        """尝试用保存的token自动登录"""
        if not self.config.get("token"):
            return False
        try:
            self.api.token = self.config["token"]
            user = self.api.get_me()
            self.config["user"] = user
            return True
        except Exception:
            self.clear_session(save=False, close_windows=False)
            return False

    def is_logged_in(self):
        return bool(self.api.token and self.config.get("user"))

    def _show_login_dialog(self, parent=None):
        dialog = LoginDialog(self.api, self.config, parent)
        if dialog.exec_() != dialog.Accepted:
            return False
        save_config(self.config)
        self._handle_session_changed(refresh_overlay=False)
        return True

    def _handle_session_changed(self, refresh_overlay=True):
        if self.tray:
            self.tray.refresh_menu()
        if self.overlay:
            if refresh_overlay and self.is_logged_in():
                self.overlay.refresh_tasks()
            else:
                self.overlay.show_logged_out_state()

    def clear_session(self, save=True, close_windows=True):
        self.config["token"] = ""
        self.config["user"] = None
        self.api.token = ""
        if close_windows:
            self.window_manager.close_all_windows()
        if save:
            save_config(self.config)
        self._handle_session_changed(refresh_overlay=False)

    def ensure_logged_in(self, parent=None):
        if self.is_logged_in():
            return True
        if not self._show_login_dialog(parent):
            self._handle_session_changed(refresh_overlay=False)
            return False
        self.refresh_overlay()
        return True

    def open_browser(self, path="/"):
        """使用系统默认浏览器打开页面"""
        if not self.ensure_logged_in():
            return
        try:
            url = self._build_browser_url(path)
            browser_path = self._resolve_browser_path()
            if browser_path:
                subprocess.Popen([browser_path, url], cwd=os.path.dirname(browser_path) or None)
            elif os.name == "nt":
                os.startfile(url)
            else:
                import webbrowser
                webbrowser.open(url)
        except Exception as exc:
            self._notify_client_error(f"打开浏览器失败：{exc}")
            traceback.print_exc()

    def open_task(self, task):
        if not self.ensure_logged_in():
            return

        if self._open_task_in_native_window(task):
            return

        route = self._route_for_task(task)
        if route == "/dashboard":
            self.show_main_workspace("dashboard")
            return
        self.open_browser(route)

    def show_todo_window(self):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_todo_window()

    def show_main_workspace(self, section="dashboard"):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_main_workspace(section=section)

    def show_workspace_section(self, section):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_main_workspace(section=section)

    def show_rectification_window(self, task):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_rectification_window(task)

    def show_discussion_window(self, task=None, auto_create=False):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_discussion_window(task=task, auto_create=auto_create)

    def show_study_window(self, task=None, auto_create=False):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_study_window(task=task, auto_create=auto_create)

    def show_followup_window(self, task=None):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_followup_window(task=task)

    def show_check_window(self, task=None, check_id=None):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_check_window(task=task, check_id=check_id)

    def show_task_manage_window(self):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_task_manage_window()

    def show_user_manage_window(self):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_user_manage_window()

    def show_report_window(self):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_report_window()

    def show_patient_import_window(self):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_patient_import_window()

    def show_task_detail_window(self, task):
        if not self.ensure_logged_in():
            return
        self.window_manager.show_task_detail_window(task)

    def _build_browser_url(self, path):
        parsed = urlsplit(self.config["server_url"].rstrip("/"))
        root_path = parsed.path.rstrip("/") or "/"
        query_items = parse_qsl(parsed.query, keep_blank_values=True)

        query_items = [(key, value) for key, value in query_items if key != "client_route"]
        query_items.append(("client_route", path or "/"))

        if self.api.token:
            query_items = [(key, value) for key, value in query_items if key != "client_token"]
            query_items.append(("client_token", self.api.token))

        user = self.config.get("user") or {}
        if user:
            query_items = [(key, value) for key, value in query_items if key != "client_user"]
            query_items.append(("client_user", json.dumps(user, ensure_ascii=False, separators=(",", ":"))))

        return urlunsplit((
            parsed.scheme,
            parsed.netloc,
            root_path,
            urlencode(query_items),
            parsed.fragment,
        ))

    def _notify_client_error(self, message):
        print(message)
        if self.tray and self.tray.supportsMessages():
            self.tray.showMessage("科室质控平台", message)

    def handle_api_error(self, exc, parent=None, context_message=None):
        if isinstance(exc, ApiError) and exc.status_code == 401:
            self.clear_session(close_windows=False)
            QMessageBox.warning(parent, "登录失效", "登录已失效，请重新登录")
            if self.relogin(parent):
                return True
            return False

        message = str(exc)
        if context_message:
            message = f"{context_message}\n{message}"
        QMessageBox.warning(parent, "操作失败", message)
        return False

    def relogin(self, parent=None):
        if not self._show_login_dialog(parent):
            return False
        self.refresh_overlay()
        return True

    def switch_user(self):
        from PyQt5.QtWidgets import QMessageBox

        current_user = self.config.get("user") or {}
        display_name = current_user.get("real_name") or current_user.get("username") or "当前账号"
        reply = QMessageBox.question(
            None,
            "切换用户",
            f"是否退出 {display_name} 并重新登录其他账号？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.clear_session()
        if self.ensure_logged_in():
            self.refresh_overlay()

    def logout(self):
        from PyQt5.QtWidgets import QMessageBox

        if not self.is_logged_in():
            self.clear_session()
            return

        reply = QMessageBox.question(
            None,
            "退出登录",
            "退出登录后客户端将停止同步待办，是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.clear_session()

    def refresh_overlay(self):
        if self.overlay:
            self.overlay.refresh_tasks()
        self.window_manager.refresh_open_windows()

    def toggle_overlay(self):
        if self.overlay:
            if self.overlay.isVisible():
                self.overlay.hide()
            else:
                self.overlay.show()

    def open_settings(self):
        previous_mode = self.config.get("compatibility_mode", "auto")
        overlay_was_visible = self.overlay.isVisible() if self.overlay else False
        dialog = SettingsDialog(self.config)
        if dialog.exec_() == dialog.Accepted:
            self.api.server_url = self.config["server_url"]
            save_config(self.config)
            if self.overlay:
                if overlay_was_visible and not self.overlay.isVisible():
                    self.overlay.show()
                QTimer.singleShot(0, self.overlay.apply_settings)
            if previous_mode != self.config.get("compatibility_mode", "auto"):
                QMessageBox.information(
                    dialog,
                    "已保存设置",
                    "运行兼容档位已更新，重启客户端后生效。",
                )

    def quit_app(self):
        self._cleanup_client_pid()
        save_config(self.config)
        self.app.quit()

    def start_server_runtime(self):
        self._run_batch_script("启动服务器.bat")

    def start_client_runtime(self):
        self._run_batch_script("启动客户端.bat")

    def stop_all_runtime(self):
        self._run_batch_script("退出运行.bat")

    def restart_all_runtime(self):
        self._run_batch_script("重启全部.bat")

    def _route_for_task(self, task):
        task_type = task.get("type")
        if task_type == "check":
            if task.get("linked_check_id"):
                return f"/checks?checkId={task['linked_check_id']}"
            if task.get("id"):
                return f"/checks?taskId={task['id']}"
            return "/checks"

        route_map = {
            "discussion": "/discussions",
            "study": "/studies",
            "followup": "/followups",
        }
        return route_map.get(task_type, "/dashboard")

    def _open_task_in_native_window(self, task):
        task_type = task.get("type")
        native_handler = self._native_task_handler(task_type, task)
        if native_handler is None:
            return False
        native_handler()
        return True

    def _native_task_handler(self, task_type, task):
        if task_type == "check":
            if task.get("check_task_kind") == "rectification":
                return lambda: self.show_rectification_window(task)
            return lambda: self.show_check_window(task=task, check_id=task.get("linked_check_id"))
        if task_type == "discussion":
            return lambda: self.show_discussion_window(task=task, auto_create=True)
        if task_type == "study":
            return lambda: self.show_study_window(task=task, auto_create=True)
        if task_type == "followup":
            return lambda: self.show_followup_window(task=task)
        return None

    def _run_batch_script(self, script_name):
        script_path = os.path.join(self.root_dir, script_name)
        if not os.path.exists(script_path):
            self._notify_client_error(f"未找到脚本：{script_name}")
            return
        try:
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    f"Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','""{script_path}""' -WorkingDirectory '{self.root_dir}' -WindowStyle Hidden",
                ],
                cwd=self.root_dir,
            )
        except Exception as exc:
            self._notify_client_error(f"执行脚本失败：{exc}")

    def _register_client_pid(self):
        runtime_dir = os.path.join(self.root_dir, ".runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        with open(os.path.join(runtime_dir, "client.pid"), "w", encoding="utf-8") as file:
            file.write(str(os.getpid()))

    def _cleanup_client_pid(self):
        pid_file = os.path.join(self.root_dir, ".runtime", "client.pid")
        if not os.path.exists(pid_file):
            return
        try:
            with open(pid_file, "r", encoding="utf-8") as file:
                current = (file.read() or "").strip()
            if current == str(os.getpid()):
                os.remove(pid_file)
        except OSError:
            pass

    def _schedule_shell_components_initialization(self):
        delay = max(int(self.runtime_profile.defer_shell_init_ms or 0), 0)
        QTimer.singleShot(delay, self._initialize_shell_components)

    def _initialize_shell_components(self):
        if self.tray is None and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = TrayIcon(self)
        elif self.tray is None:
            print("系统托盘不可用，已跳过托盘图标初始化。")
        QTimer.singleShot(300, self._initialize_overlay)

    def _initialize_overlay(self):
        if self.overlay is not None:
            return
        self.overlay = OverlayWidget(self)
        self.overlay.show()

    def _resolve_browser_path(self):
        browser_path = (self.config.get("browser_path") or "").strip()
        if browser_path and os.path.exists(browser_path):
            return browser_path
        if self.runtime_profile.prefer_chromium_browser:
            for candidate in preferred_browser_paths():
                if os.path.exists(candidate):
                    return candidate
        return ""


if __name__ == "__main__":
    ctx = AppContext()
    sys.exit(ctx.run())

