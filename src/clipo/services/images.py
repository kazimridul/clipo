"""Worker-only, content-addressed image storage."""
import hashlib
import os
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt
from clipo.config.settings import private_directory


def store_image(image: QImage, directory, vault=None):
    if image.isNull() or image.width() * image.height() > 32_000_000:
        raise ValueError("Image is empty or exceeds the 32 megapixel limit")
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    digest = hashlib.sha256(bytes(image.constBits()) + f"{image.width()}x{image.height()}".encode()).hexdigest()
    path = directory / (digest + ".png")
    if not path.exists():
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise ValueError("Image encoding failed")
        from clipo.security.vault import private_write
        vault.write(path, bytes(buffer.data())) if vault else private_write(path, bytes(buffer.data()))
    thumb = private_directory(directory / "thumbnails") / path.name
    if not thumb.exists():
        small = image.scaled(160, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        small.save(buffer, "PNG")
        from clipo.security.vault import private_write
        vault.write(thumb, bytes(buffer.data())) if vault else private_write(thumb, bytes(buffer.data()))
    return path, digest
