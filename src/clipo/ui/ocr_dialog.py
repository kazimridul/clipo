from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QApplication


class OCRDialog(QDialog):
    save_requested = Signal(str)
    qr_requested = Signal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Extracted text")
        self.resize(650, 500)
        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit(text)
        layout.addWidget(self.text)
        actions = QHBoxLayout()
        for title, callback in (("Copy", lambda: QApplication.clipboard().setText(self.text.toPlainText())), ("Save as clipboard item", lambda: self.save_requested.emit(self.text.toPlainText())), ("Generate QR", lambda: self.qr_requested.emit(self.text.toPlainText()))):
            button = QPushButton(title)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
