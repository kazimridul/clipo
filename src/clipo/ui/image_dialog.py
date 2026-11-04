from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout


class ImageDialog(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Image · {image.width()} × {image.height()}")
        self.resize(900, 700)
        self.image = image
        self.zoom = 1.0
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        for title, factor in (("Zoom out", 0.8), ("Zoom in", 1.25), ("Actual size", 0)):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, value=factor: self.scale(value))
            controls.addWidget(button)
        layout.addLayout(controls)
        area = QScrollArea()
        self.label = QLabel()
        area.setWidget(self.label)
        layout.addWidget(area)
        self.scale(0)

    def scale(self, factor):
        self.zoom = max(0.1, min(4, self.zoom * factor)) if factor else 1
        pixmap = QPixmap.fromImage(self.image).scaled(int(self.image.width() * self.zoom), int(self.image.height() * self.zoom), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.size())
