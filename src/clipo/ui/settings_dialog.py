from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clipo settings")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        heading = QLabel("Make it yours")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems(["System", "Light", "Dark"])
        self.theme.setCurrentText(settings.theme.title())
        form.addRow("Appearance", self.theme)
        self.limit = QSpinBox()
        self.limit.setRange(0, 1_000_000)
        self.limit.setSpecialValueText("Unlimited")
        self.limit.setValue(settings.history_limit)
        form.addRow("History item limit", self.limit)
        layout.addLayout(form)
        hint = QLabel("Reducing the limit deletes older items immediately.\nHistory is stored locally as unencrypted text.\nPause or use private mode before copying secrets.")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

