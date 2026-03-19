import json

from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.QtCore import QUrl

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - optional runtime dependency
    QWebEngineView = None


class BrowserWindow(QMainWindow):
    """内嵌浏览器窗口"""

    def __init__(self, server_url, token, title="科室质控平台", path="/", parent=None):
        super().__init__(parent)
        if QWebEngineView is None:
            raise RuntimeError("当前客户端未包含内嵌浏览器组件，请改用系统浏览器入口。")

        self.server_url = server_url.rstrip("/")
        self.token = token

        self.setWindowTitle(title)
        self.resize(1200, 800)

        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)

        # 注入token到localStorage
        page = self.web_view.page()
        page.renderProcessTerminated.connect(self._handle_render_process_terminated)
        url = f"{self.server_url}{path}"

        # 页面加载完成后注入token
        page.loadFinished.connect(lambda ok: self._inject_token() if ok else self._handle_load_failed(url))
        self.web_view.setUrl(QUrl(url))

    def _inject_token(self):
        token_json = json.dumps(self.token or "")
        js = f"localStorage.setItem('token', {token_json});"
        self.web_view.page().runJavaScript(js)

    def _handle_load_failed(self, url):
        QMessageBox.warning(self, "页面打开失败", f"无法加载页面：\n{url}")

    def _handle_render_process_terminated(self, status, exit_code):
        QMessageBox.critical(
            self,
            "页面渲染异常",
            f"内嵌页面渲染进程已退出。\n状态：{status}\n退出码：{exit_code}"
        )

    def navigate(self, path):
        url = f"{self.server_url}{path}"
        self.web_view.setUrl(QUrl(url))

