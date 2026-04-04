from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class _AsyncRunner(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(object)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    @pyqtSlot()
    def run(self):
        try:
            result = self._fn()
        except Exception as exc:
            self.failed.emit(exc)
            return
        self.finished.emit(result)


def start_async_task(owner, fn, on_success, on_error=None):
    thread = QThread(owner)
    runner = _AsyncRunner(fn)
    runner.moveToThread(thread)

    active_tasks = getattr(owner, "_active_async_tasks", None)
    if active_tasks is None:
        active_tasks = []
        setattr(owner, "_active_async_tasks", active_tasks)

    task_state = {"thread": thread, "runner": runner}
    active_tasks.append(task_state)

    def cleanup(*_):
        if task_state in active_tasks:
            active_tasks.remove(task_state)
        thread.quit()
        thread.wait()
        runner.deleteLater()
        thread.deleteLater()

    thread.started.connect(runner.run)
    runner.finished.connect(on_success)
    runner.finished.connect(cleanup)
    if on_error is not None:
        runner.failed.connect(on_error)
    runner.failed.connect(cleanup)
    thread.start()
