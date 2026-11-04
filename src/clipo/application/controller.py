"""Composition and lifecycle; widgets never talk to SQLite directly."""
import logging

from PySide6.QtCore import QObject, QMetaObject, QThread, Qt, Signal, QTimer, Slot
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QDialog, QMessageBox, QSystemTrayIcon, QInputDialog, QFileDialog

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
        from clipo.services.jobs import JobRunner
        self.jobs = JobRunner(self)
        self.capability = capability(app.platformName())
        self.window = MainWindow(self.capability.message)
        self.window.apply_keys(settings.key_bindings)
        from clipo.ui.quick_popup import QuickPopup
        from clipo.system.shortcuts import GlobalShortcut
        self.popup = QuickPopup(self.window)
        self.shortcuts = GlobalShortcut(self)
        self.shortcuts.activated.connect(self.popup.reveal)
        self.shortcuts.status.connect(self.window.statusBar().showMessage)
        self.quick_key = QShortcut(QKeySequence(settings.quick_shortcut), self.window, activated=self.popup.reveal)
        self.window.setWindowIcon(icon)
        self.monitor = ClipboardMonitor(app.clipboard(), settings.max_text_bytes)
        self.monitor.policy = settings
        self.thread = QThread(self)
        self.worker = HistoryWorker(data_path / "history.sqlite3", settings.history_limit, settings.max_text_bytes, settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.initialize)
        self.thread.finished.connect(self.worker.deleteLater)
        self.command.connect(self.worker.execute)
        self.worker.ready.connect(self.on_ready)
        self.worker.changed.connect(self.window.refresh)
        self.worker.page_ready.connect(self.on_page)
        self.worker.item_ready.connect(self.on_item)
        self.worker.error.connect(self.on_error)
        self.worker.notice.connect(self.on_notice)
        self.worker.image_ready.connect(self.on_image)
        self.worker.collections_ready.connect(self.window.show_collections)
        self.worker.image_stored.connect(self.auto_ocr)
        self.worker.changed.connect(self.refresh_collections)
        self.monitor.error.connect(self.on_error)
        self.monitor.captured.connect(lambda text: self.command.emit("capture", text))
        self.monitor.payload_captured.connect(lambda payload: self.command.emit("payload", payload))
        self.window.operation_requested.connect(self.operation)
        # Negative generations route popup responses without disturbing main-window search.
        self.popup.query_requested.connect(lambda query, generation: self.command.emit("page", (query, -generation)))
        self.popup.restore_requested.connect(lambda item_id: self.command.emit("restore", item_id))
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
        self.maintenance = QTimer(self)
        self.maintenance.setInterval(60000)
        self.maintenance.timeout.connect(lambda: self.command.emit("cleanup", None))
        self.maintenance.timeout.connect(lambda: self.command.emit("scheduled_backup", None) if not self.monitor.private else None)
        self.maintenance.start()

    @Slot()
    def on_ready(self):
        self.monitor.enabled = True
        self.window.refresh()
        self.command.emit("collections", None)
        self.command.emit("cleanup", None)
        if not self.monitor.private:
            self.command.emit("scheduled_backup", None)
        self.show_state()
        self.shortcuts.bind(self.settings.quick_shortcut, self.app.platformName())

    @Slot(object, int)
    def on_page(self, page, generation):
        if generation < 0:
            self.popup.show_page(page, -generation)
        else:
            self.window.show_page(page, generation)

    @Slot(str)
    def on_notice(self, message):
        self.window.statusBar().showMessage(message, 8000)

    @Slot()
    def refresh_collections(self):
        self.command.emit("collections", None)

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
            self.monitor.restore_payload(item)
            self.window.statusBar().showMessage("Copied. Switch to your app and paste with Ctrl+V.", 5000)
        elif purpose in ("edit_item", "organize_item"):
            from clipo.ui.item_dialog import ItemDialog
            if purpose == "edit_item" and item.content_type == "image":
                self.on_error("Use OCR to extract text from images; images cannot be edited as text.")
                return
            dialog = ItemDialog(item, self.window, purpose == "organize_item")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if purpose == "edit_item":
                    self.command.emit("edit", (item.id, dialog.text.toPlainText(), dialog.title.text(), dialog.language.currentText(), dialog.description.text()))
                self.command.emit("organize", (item.id, dialog.tags.text(), dialog.collections.text()))
        elif purpose == "save_image":
            if item.content_type != "image":
                self.on_error("Select an image first.")
                return
            path, _ = QFileDialog.getSaveFileName(self.window, "Save image", "clipboard.png", "PNG images (*.png)")
            if path:
                self.command.emit("export_image", (item.id, path))
        elif purpose == "qr":
            self.open_qr(item.ocr_text if item.content_type == "image" else item.content_text, item.id)
        elif purpose == "ocr":
            self.run_ocr(item)
        elif purpose == "snippet":
            if item.content_type == "image":
                self.on_error("Extract image text first.")
            else:
                self.command.emit("make_snippet", item.id)
                self.on_item(item, "edit_item")
        elif purpose in ("json_pretty", "json_minify"):
            from clipo.services.recognition import format_json
            try:
                text = format_json(item.content_text, purpose == "json_minify")
                self.command.emit("edit", (item.id, text, item.title, "JSON", item.description))
            except ValueError as error:
                self.on_error(str(error))
        elif purpose == "open_url":
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            from clipo.services.recognition import recognize
            kind, _ = recognize(item.content_text)
            if kind in ("url", "email"):
                QDesktopServices.openUrl(QUrl(("mailto:" if kind == "email" else "") + item.content_text.strip()))
            else:
                self.on_error("This item is not an HTTP(S) link or email address.")
        else:
            self.window.show_preview(item)

    def on_image(self, item, image, purpose):
        if purpose == "restore":
            try:
                self.monitor.restore_payload(item, image)
                self.window.statusBar().showMessage("Image copied to clipboard.", 5000)
            except ValueError as error:
                self.on_error(str(error))
        elif purpose == "view_image":
            from clipo.ui.image_dialog import ImageDialog
            ImageDialog(image, self.window).exec()
        else:
            self.window.show_image(item, image)

    def operation(self, action, item_id):
        if action in ("favorite", "pin"):
            self.command.emit("flag", (item_id, "is_favorite" if action == "favorite" else "is_pinned"))
        elif action == "undo":
            self.command.emit("undo", None)
        elif action == "quick":
            self.popup.reveal()
        elif action == "manual_qr":
            self.open_qr()
        elif action == "new_item":
            from clipo.models.item import ClipboardItem
            from clipo.ui.item_dialog import ItemDialog
            dialog = ItemDialog(ClipboardItem(0, "", "", ""), self.window)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.text.toPlainText().strip():
                self.command.emit("new_item", (dialog.text.toPlainText(), dialog.title.text(), dialog.language.currentText(), dialog.tags.text(), dialog.collections.text(), dialog.description.text()))
        elif action.startswith("export_"):
            self.export(action)
        elif action == "import":
            path, _ = QFileDialog.getOpenFileName(self.window, "Import Clipo backup", "", "Clipo JSON (*.json)")
            if path:
                self.command.emit("import", path)
        elif action in ("edit_item", "organize_item", "save_image", "view_image", "qr", "ocr", "snippet", "json_pretty", "json_minify", "open_url"):
            self.command.emit(action, item_id)
        elif action in ("new_collection", "rename_collection", "delete_collection"):
            old = item_id or ""
            if action != "new_collection" and not old:
                self.on_error("Select a collection first.")
                return
            if action == "delete_collection":
                if QMessageBox.question(self.window, "Delete collection?", "Remove this collection? Its clipboard items will remain.") == QMessageBox.StandardButton.Yes:
                    self.command.emit("collection", (old, ""))
            else:
                name, ok = QInputDialog.getText(self.window, "Collection", "Collection name:", text=old)
                if ok and name.strip():
                    self.command.emit("collection", (old if action == "rename_collection" else "", name))
        elif action in ("collection_color", "collection_pin"):
            if not item_id:
                self.on_error("Select a collection first.")
                return
            if action == "collection_pin":
                self.command.emit("collection_style", (item_id, None))
            else:
                from PySide6.QtWidgets import QColorDialog
                color = QColorDialog.getColor(parent=self.window)
                if color.isValid():
                    self.command.emit("collection_style", (item_id, color.name()))

    def open_qr(self, text="", item_id=None):
        from clipo.ui.qr_dialog import QRDialog
        dialog = QRDialog(text, self.jobs, self.window)
        dialog.generated.connect(lambda data: self.command.emit("qr_record", (item_id, data)) if not self.monitor.private else None)
        dialog.exec()

    def export(self, scope):
        from clipo.models.item import HistoryQuery
        query, selected = None, None
        if scope == "export_selected":
            selected = [entry.data(Qt.ItemDataRole.UserRole) for entry in self.window.items.selectedItems()]
            if not selected:
                self.on_error("Select items to export first.")
                return
        elif scope == "export_view":
            query = self.window.history_query()
        path, chosen = QFileDialog.getSaveFileName(self.window, "Export clipboard history", "clipo-backup.json", "JSON (*.json);;Text (*.txt);;CSV (*.csv);;HTML (*.html)")
        if path:
            format = {"JSON (*.json)": "json", "Text (*.txt)": "txt", "CSV (*.csv)": "csv", "HTML (*.html)": "html"}[chosen]
            self.command.emit("export", (path, format, query, selected))

    def auto_ocr(self, item):
        if self.settings.auto_ocr and not self.monitor.private and not self.monitor.paused:
            self.run_ocr(item, automatic=True)

    def run_ocr(self, item, automatic=False):
        if item.content_type != "image":
            self.on_error("Select an image to extract text.")
            return
        from clipo.services.ocr import extract_text
        self.window.statusBar().showMessage("Extracting text in the background…")
        language = self.settings.ocr_language
        def complete(text):
            if automatic and (self.monitor.private or self.monitor.paused):
                return
            self.command.emit("ocr_result", (item.id, text))
            if not automatic:
                from clipo.ui.ocr_dialog import OCRDialog
                dialog = OCRDialog(text, self.window)
                dialog.save_requested.connect(lambda value: self.command.emit("capture", value))
                dialog.qr_requested.connect(lambda value: self.open_qr(value))
                dialog.exec()
            self.window.statusBar().showMessage("Text extraction finished.", 5000)
        self.jobs.submit(lambda: extract_text(item.image_path, language), complete, self.on_error)

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
            from clipo.system.shortcuts import parse_shortcut
            try:
                parse_shortcut(dialog.shortcut.text())
            except ValueError as error:
                self.on_error(str(error))
                return
            from dataclasses import replace, asdict
            candidate = replace(self.settings, quick_shortcut=dialog.shortcut.text(), theme=dialog.theme.currentText().lower(), history_limit=dialog.limit.value(),
                retention_days=dialog.retention.value(), max_text_bytes=dialog.max_bytes.value() * 1024, block_sensitive=dialog.sensitive.isChecked(),
                persist_history=dialog.persist.isChecked(), excluded_patterns=dialog.patterns.toPlainText(), excluded_apps=dialog.apps.text(),
                auto_ocr=dialog.auto_ocr.isChecked(), ocr_language=dialog.ocr_language.text(), backup_hours=dialog.backup_hours.value(), backup_directory=dialog.backup_directory.text(), autostart=dialog.autostart.isChecked(),
                key_bindings={name: widget.keySequence().toString() for name, widget in dialog.keys.items()})
            sequences = [QKeySequence(value).toString() for value in [candidate.quick_shortcut, *candidate.key_bindings.values()] if value]
            if len(sequences) != len(set(sequences)):
                self.on_error("Two actions use the same keyboard shortcut. Choose distinct bindings.")
                return
            import re
            from pathlib import Path
            if not re.fullmatch(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*", candidate.ocr_language) or (candidate.backup_hours and not Path(candidate.backup_directory).is_absolute()):
                self.on_error("Check OCR language codes and the absolute backup directory path.")
                return
            try:
                from clipo.system.startup import configure_autostart
                if candidate.autostart != self.settings.autostart:
                    configure_autostart(candidate.autostart)
                candidate.save(self.config_path)
            except (OSError, ValueError):
                self.on_error("Settings could not be applied. Check configuration permissions.")
                return
            for key, value in asdict(candidate).items():
                setattr(self.settings, key, value)
            self.monitor.max_text_bytes = candidate.max_text_bytes
            self.command.emit("configure", candidate)
            apply_theme(self.app, self.settings.theme)
            self.command.emit("limit", self.settings.history_limit)
            self.quick_key.setKey(QKeySequence(self.settings.quick_shortcut))
            self.window.apply_keys(self.settings.key_bindings)
            self.shortcuts.bind(self.settings.quick_shortcut, self.app.platformName())
            self.command.emit("cleanup", None)

    def shutdown(self):
        self.monitor.enabled = False
        self.maintenance.stop()
        self.shortcuts.close()
        self.jobs.close()
        if self.tray:
            self.tray.hide()
        if self.thread.isRunning():
            # Drain queued writes before closing the connection on its owning thread.
            QMetaObject.invokeMethod(self.worker, "close", Qt.ConnectionType.BlockingQueuedConnection)
            self.thread.quit()
            self.thread.wait()

