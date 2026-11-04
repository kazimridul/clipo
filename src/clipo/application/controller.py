"""Composition and lifecycle; widgets never talk to SQLite directly."""
import logging

from PySide6.QtCore import QObject, QMetaObject, QThread, Qt, Signal
from PySide6.QtWidgets import QDialog, QMessageBox, QSystemTrayIcon

from clipo.clipboard.monitor import ClipboardMonitor
from clipo.clipboard.platform import capability
from clipo.core.worker import HistoryWorker
from clipo.system.tray import Tray
from clipo.ui.settings_dialog import SettingsDialog
from clipo.ui.theme import apply_theme
from clipo.ui.window import MainWindow


class Controller(QObject):
    command = Signal(str, object)

    def __init__(self, app, settings, config_path, data_path, icon):
        super().__init__()
        self.app = app
        self.settings = settings
        self.config_path = config_path
        self.capability = capability(app.platformName())
        self.window = MainWindow(self.capability.message)
        self.window.setWindowIcon(icon)
        self.monitor = ClipboardMonitor(app.clipboard(), settings.max_text_bytes)
        self.thread = QThread(self)
        self.worker = HistoryWorker(data_path / "history.sqlite3", settings.history_limit, settings.max_text_bytes)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.initialize)
        self.thread.finished.connect(self.worker.deleteLater)
        self.command.connect(self.worker.execute)
        self.worker.ready.connect(self.on_ready)
        self.worker.changed.connect(self.window.refresh)
        self.worker.page_ready.connect(self.window.show_page)
        self.worker.item_ready.connect(self.on_item)
        self.worker.error.connect(self.on_error)
        self.monitor.error.connect(self.on_error)
        self.monitor.captured.connect(lambda text: self.command.emit("capture", text))
        self.window.query_requested.connect(lambda query, generation: self.command.emit("page", (query, generation)))
        self.window.preview_requested.connect(lambda item_id: self.command.emit("preview", item_id))
        self.window.restore_requested.connect(lambda item_id: self.command.emit("restore", item_id))
        self.window.delete_requested.connect(lambda item_id: self.command.emit("delete", item_id))
        self.window.clear_requested.connect(lambda: self.command.emit("clear", None))
        self.window.pause_requested.connect(self.pause)
        self.window.private_requested.connect(self.private)
        self.window.settings_requested.connect(self.show_settings)
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = Tray(icon, self.window, app.quit)
            self.tray.show()
            self.window.hide_to_tray = True
            app.setQuitOnLastWindowClosed(False)
        self.window.pause_button.setChecked(settings.paused)
        self.monitor.set_paused(settings.paused)
        self.window.private_button.setChecked(settings.private)
        self.monitor.set_private(settings.private)
        app.aboutToQuit.connect(self.shutdown)
        app.styleHints().colorSchemeChanged.connect(lambda _: apply_theme(app, self.settings.theme))
        self.thread.start()

    def on_ready(self):
        self.monitor.enabled = True
        self.window.refresh()
        self.show_state()

    def show_state(self):
        if self.monitor.private:
            status = "Private mode · recording is off"
        elif self.monitor.paused:
            status = "Capture paused"
        elif self.capability.background_supported:
            status = "Monitoring clipboard · text history"
        else:
            status = "Limited clipboard access · see desktop notice above"
        self.window.statusBar().showMessage(status)
        self.window.pause_button.setText("Resume capture" if self.monitor.paused else "Pause capture")
        self.window.private_button.setText("Private mode · ON" if self.monitor.private else "Private mode")
        if self.tray:
            self.tray.setToolTip(f"Clipo · {status}")

    def pause(self, value):
        self.monitor.set_paused(value)
        self.settings.paused = value
        self.save_settings()
        self.show_state()

    def private(self, value):
        self.monitor.set_private(value)
        self.settings.private = value
        self.save_settings()
        self.show_state()

    def on_item(self, item, purpose):
        if item is None:
            self.window.statusBar().showMessage("This item no longer exists.", 5000)
        elif purpose == "restore":
            self.monitor.restore(item.content_text)
            self.window.statusBar().showMessage("Copied. Switch to your app and paste with Ctrl+V.", 5000)
        else:
            self.window.show_preview(item)

    def on_error(self, message):
        self.window.statusBar().showMessage(message)

    def save_settings(self):
        try:
            self.settings.save(self.config_path)
            return True
        except OSError:
            logging.getLogger(__name__).error("Could not save application settings")
            QMessageBox.warning(self.window, "Settings could not be saved", "Check your configuration directory permissions and disk space.")
            return False

    def show_settings(self):
        dialog = SettingsDialog(self.settings, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.theme = dialog.theme.currentText().lower()
            self.settings.history_limit = dialog.limit.value()
            self.save_settings()
            apply_theme(self.app, self.settings.theme)
            self.command.emit("limit", self.settings.history_limit)

    def shutdown(self):
        self.monitor.enabled = False
        if self.tray:
            self.tray.hide()
        if self.thread.isRunning():
            # Drain queued writes before closing the connection on its owning thread.
            QMetaObject.invokeMethod(self.worker, "close", Qt.ConnectionType.BlockingQueuedConnection)
            self.thread.quit()
            self.thread.wait()

