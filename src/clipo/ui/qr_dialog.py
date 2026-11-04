from PySide6.QtCore import Signal
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton, QComboBox, QSpinBox, QLineEdit, QFileDialog, QApplication
from clipo.services.qr import QROptions, generate_qr, split_payload


class QRDialog(QDialog):
    generated = Signal(bytes)

    def __init__(self, text, runner, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share with a QR code")
        self.resize(610, 800)
        self.runner, self.png, self.svg = runner, b"", b""
        self.alive = True
        self.serial = 0
        self.chunks = []
        layout = QVBoxLayout(self)
        self.image = QLabel()
        self.image.setMinimumHeight(260)
        from PySide6.QtCore import Qt
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image)
        self.text = QPlainTextEdit(text)
        self.text.setMaximumHeight(130)
        layout.addWidget(self.text)
        form = QFormLayout()
        self.correction = QComboBox()
        self.correction.addItems(["L", "M", "Q", "H"])
        self.correction.setCurrentText("M")
        self.size = QSpinBox()
        self.size.setRange(128, 2048)
        self.size.setValue(512)
        self.foreground, self.background = QLineEdit("#000000"), QLineEdit("#ffffff")
        for label, widget in (("Error correction", self.correction), ("Maximum image size", self.size), ("Foreground", self.foreground), ("Background", self.background)):
            form.addRow(label, widget)
        layout.addLayout(form)
        self.message = QLabel("Offline sharing. A phone scan reads the text directly; nothing is uploaded.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        actions = QHBoxLayout()
        for label, callback in (("Generate", self.generate), ("Split into parts", self.split), ("Next part", self.next_part)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        actions = QHBoxLayout()
        for label, callback in (("Copy image", self.copy), ("PNG", lambda: self.save(False)), ("SVG", lambda: self.save(True)), ("Print", self.print_qr), ("Copy text", lambda: QApplication.clipboard().setText(self.text.toPlainText()))):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.text.textChanged.connect(self.invalidate)
        for widget in (self.correction, self.size, self.foreground, self.background):
            signal = widget.currentTextChanged if isinstance(widget, QComboBox) else widget.valueChanged if isinstance(widget, QSpinBox) else widget.textChanged
            signal.connect(self.invalidate)
        self.generate()

    def invalidate(self, *_):
        self.serial += 1
        self.png, self.svg = b"", b""
        self.image.clear()

    def generate(self):
        self.invalidate()
        serial = self.serial
        text = self.text.toPlainText()
        options = QROptions(self.correction.currentText(), self.size.value(), self.foreground.text(), self.background.text())
        self.message.setText("Generating…")
        def done(result):
            if not self.alive or serial != self.serial:
                return
            self.png, self.svg = result
            self.image.setPixmap(QPixmap.fromImage(QImage.fromData(self.png)).scaledToHeight(260))
            self.message.setText(f"{len(text.encode())} bytes · scan to read this text." + (" Large payload: test scanning before sharing." if len(text.encode()) > 700 else ""))
            self.generated.emit(self.png)
        self.runner.submit(lambda: generate_qr(text, options), done, lambda error: self.message.setText(error) if self.alive and serial == self.serial else None)

    def split(self):
        self.chunks = split_payload(self.text.toPlainText())
        self.part = 0
        if self.chunks:
            self.show_part()

    def next_part(self):
        if self.chunks:
            self.part = (self.part + 1) % len(self.chunks)
            self.show_part()

    def show_part(self):
        self.setWindowTitle(f"QR part {self.part + 1} of {len(self.chunks)} · scan in order")
        self.text.setPlainText(self.chunks[self.part])
        self.generate()

    def copy(self):
        if self.png:
            QApplication.clipboard().setImage(QImage.fromData(self.png))

    def save(self, svg):
        if not self.png:
            return
        from pathlib import Path
        suffix = "svg" if svg else "png"
        path, _ = QFileDialog.getSaveFileName(self, "Save QR", "clipo-qr." + suffix, suffix.upper() + " (*." + suffix + ")")
        if path:
            data = self.svg if svg else self.png
            self.runner.submit(lambda: Path(path).write_bytes(data), lambda _: self.message.setText("Saved") if self.alive else None, lambda error: self.message.setText(error) if self.alive else None)

    def print_qr(self):
        if not self.png:
            return
        printer = QPrinter()
        if QPrintDialog(printer, self).exec() == QDialog.DialogCode.Accepted:
            painter = QPainter(printer)
            image = QImage.fromData(self.png)
            painter.drawImage(0, 0, image)
            painter.end()

    def closeEvent(self, event):
        self.alive = False
        super().closeEvent(event)

    def done(self, result):
        self.alive = False
        super().done(result)
