"""Background jobs with callbacks dispatched on the runner's GUI thread."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class JobSignals(QObject):
    done = Signal(int, object, str)


class Job(QRunnable):
    def __init__(self, key, function):
        super().__init__()
        self.key, self.function = key, function
        self.signals = JobSignals()

    def run(self):
        try:
            result = self.function()
            self.signals.done.emit(self.key, result, "")
        except Exception as error:
            message = str(error) if isinstance(error, ValueError) else "The operation failed. Check the selected file and available disk space."
            self.signals.done.emit(self.key, None, message)


class JobRunner(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.pending = {}
        self.serial = 0

    def submit(self, function, success, failure):
        self.serial += 1
        job = Job(self.serial, function)
        self.pending[self.serial] = (job, success, failure)
        job.signals.done.connect(self.complete)
        self.pool.start(job)

    @Slot(int, object, str)
    def complete(self, key, result, error):
        entry = self.pending.pop(key, None)
        if entry:
            _, success, failure = entry
            failure(error) if error else success(result)

    def close(self):
        self.pool.waitForDone()
        self.pending.clear()
