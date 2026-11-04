from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout, QLineEdit, QPlainTextEdit, QTabWidget, QWidget, QKeySequenceEdit
from PySide6.QtGui import QKeySequence


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clipo settings")
        self.resize(740, 560)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        def page(title):
            widget = QWidget()
            form = QFormLayout(widget)
            form.setContentsMargins(20, 25, 20, 25)
            tabs.addTab(widget, title)
            return form

        def spin(value, maximum, zero="Disabled"):
            widget = QSpinBox()
            widget.setRange(0, maximum)
            widget.setSpecialValueText(zero)
            widget.setValue(value)
            return widget

        def check(value):
            widget = QCheckBox()
            widget.setChecked(value)
            return widget

        def note(form, text):
            label = QLabel(text)
            label.setWordWrap(True)
            form.addRow(label)

        form = page("General")
        self.theme = QComboBox()
        self.theme.addItems(["System", "Light", "Dark"])
        self.theme.setCurrentText(settings.theme.title())
        form.addRow("Appearance", self.theme)
        self.limit = spin(settings.history_limit, 1000000, "Unlimited")
        form.addRow("Unpinned history limit", self.limit)
        self.retention = spin(settings.retention_days, 36500)
        self.retention.setSuffix(" days")
        form.addRow("Expire unpinned items after", self.retention)
        note(form, "Reducing limits removes older unpinned history immediately.")
        self.max_bytes = spin(settings.max_text_bytes // 1024, 16384)
        self.max_bytes.setMinimum(1)
        self.max_bytes.setSuffix(" KiB")
        form.addRow("Maximum text size", self.max_bytes)

        form = page("Privacy")
        self.sensitive = check(settings.block_sensitive)
        form.addRow("Skip common credential patterns", self.sensitive)
        self.persist = check(settings.persist_history)
        form.addRow("Persist clipboard history", self.persist)
        note(form, "Turning persistence off starts fresh in-memory history. Disk history is preserved and returns when re-enabled. Temporary image files are removed on exit. Storage is unencrypted.")
        self.patterns = QPlainTextEdit(settings.excluded_patterns)
        self.patterns.setPlaceholderText("One literal text pattern per line")
        self.patterns.setMaximumHeight(100)
        form.addRow("Excluded text", self.patterns)
        self.apps = QLineEdit(settings.excluded_apps)
        form.addRow("Excluded app globs (comma separated)", self.apps)
        note(form, "App exclusions use best-effort X11 active-window identity. When identity is unavailable, including Wayland, configured exclusions stop capture. Use private mode for secrets.")

        form = page("Shortcuts")
        self.shortcut = QLineEdit(settings.quick_shortcut)
        form.addRow("Quick clipboard", self.shortcut)
        self.keys = {}
        for name, value in settings.key_bindings.items():
            self.keys[name] = QKeySequenceEdit(QKeySequence(value))
            form.addRow(name.title(), self.keys[name])
        note(form, "X11: native global binding with conflict reporting.\nWayland: assign ‘clipo --quick’ in desktop keyboard settings.\n\nIn-app: Ctrl+F search, Ctrl+P pin, Delete selected items, Ctrl+Q quit.")

        form = page("OCR")
        self.ocr_language = QLineEdit(settings.ocr_language)
        form.addRow("Tesseract language codes", self.ocr_language)
        self.auto_ocr = check(settings.auto_ocr)
        form.addRow("Automatically OCR new images", self.auto_ocr)
        note(form, "Install Tesseract and language packs with Ubuntu's package manager. Examples: eng, ben, eng+ben. OCR stays local and runs in the background. Use ‘tesseract --list-langs’ to see installed languages.")

        form = page("Backups")
        self.backup_hours = spin(settings.backup_hours, 8760)
        self.backup_hours.setSuffix(" hours")
        form.addRow("Automatic backup interval", self.backup_hours)
        self.backup_directory = QLineEdit(settings.backup_directory)
        form.addRow("Backup directory (absolute path)", self.backup_directory)
        note(form, "JSON backups include text and images and stay local and unencrypted. The latest seven automatic backups are kept. Disabled for session-only history. Use Library in the main window for manual import/export.")

        form = page("Startup")
        self.autostart = check(settings.autostart)
        form.addRow("Start Clipo at login", self.autostart)
        note(form, "Starts in the tray when a tray host is available. Otherwise the window opens so Clipo stays accessible. Closing the window keeps capture active only when a tray host is present.")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
