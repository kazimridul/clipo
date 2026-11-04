"""Vault passphrases are never written to settings or logs."""
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QVBoxLayout, QLabel, QCheckBox
from clipo.services.jobs import JobRunner
from clipo.security.vault import verify_password


class VaultDialog(QDialog):
    def __init__(self, path=None, parent=None, create=False):
        super().__init__(parent)
        self.setWindowTitle("Encrypt Clipo history" if create else "Unlock Clipo vault")
        self.resize(470, 260)
        self.path, self.create = path, create
        self.jobs = JobRunner(self)
        self.alive = True
        layout = QVBoxLayout(self)
        self.message = QLabel("Use at least 12 characters. Keep your passphrase safe; it cannot be recovered." if create else "Enter the vault passphrase to access your history.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        form = QFormLayout()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Passphrase", self.password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        if create:
            form.addRow("Confirm", self.confirm)
        layout.addLayout(form)
        self.remove_original = QCheckBox("Remove old unencrypted history files after verified migration")
        self.remove_original.setChecked(True)
        if create:
            layout.addWidget(self.remove_original)
            label = QLabel("Existing external exports/backups are not removed. SSDs and snapshots may retain old data; secure erasure is not guaranteed.")
            label.setWordWrap(True)
            layout.addWidget(label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.validate)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.password.returnPressed.connect(self.validate)

    def validate(self):
        value = self.password.text()
        if self.create:
            if len(value) < 12 or value != self.confirm.text():
                self.message.setText("Use at least 12 characters and enter the same passphrase twice.")
                return
            self.accept()
            return
        self.buttons.setEnabled(False)
        self.message.setText("Unlocking…")
        self.jobs.submit(lambda: verify_password(self.path, value), lambda _: self.accept() if self.alive else None, self.failed)

    def failed(self, message):
        if self.alive:
            self.buttons.setEnabled(True)
            self.message.setText(message)

    def done(self, result):
        self.alive = False
        self.jobs.close()
        super().done(result)
