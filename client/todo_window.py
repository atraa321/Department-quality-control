from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from config import save_config
from todo_panel import TodoPanel


class TodoWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.config = app_context.config

        self.setWindowTitle("我的待办")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        width = int(self.config.get("todo_window_width", 920) or 920)
        height = int(self.config.get("todo_window_height", 560) or 560)
        self.resize(width, height)

        x = self.config.get("todo_window_x")
        y = self.config.get("todo_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)
        self.todo_panel = TodoPanel(self.app_context, self)
        layout.addWidget(self.todo_panel)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["todo_window_x"] = pos.x()
        self.config["todo_window_y"] = pos.y()
        self.config["todo_window_width"] = size.width()
        self.config["todo_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_tasks(self, silent=False):
        return self.todo_panel.refresh_tasks(silent=silent)

