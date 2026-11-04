#!/usr/bin/env python3
"""Render both themes with synthetic data, without accessing the desktop clipboard."""
import os
from pathlib import Path
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication

from clipo.application.controller import Controller
from clipo.config.settings import Settings
from clipo.storage.repository import HistoryRepository
from clipo.ui.theme import apply_theme
from clipo.core.history import HistoryService
from clipo.services.qr import generate_qr
from clipo.services.images import store_image
from clipo.models.item import HistoryQuery


def main():
    project = Path(__file__).resolve().parents[1]
    output = project / "docs/screenshots"
    output.mkdir(exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="clipo-preview-") as folder:
        root = Path(folder)
        repo = HistoryRepository(root / "data/history.sqlite3")
        service = HistoryService(repo, 1000, 1024 * 1024)
        for text in (
            "Design notes\nKeep it simple. Make finding the right clip feel effortless.",
            "https://ubuntu.com/desktop",
            "def tidy_clip(text: str) -> str:\n    return text.strip()\n\n\n# Keep the useful things close.\nprint(tidy_clip('  Hello, Clipo!  '))",
        ):
            service.capture(text)
        snippet = repo.page(HistoryQuery()).items[0]
        repo.edit(snippet.id, snippet.content_text, "A little Python helper", "Python", "Clean up pasted text")
        repo.flag(snippet.id, "is_pinned")
        repo.flag(snippet.id, "is_favorite")
        repo.organize(snippet.id, "python, useful", "Programming")
        image = QImage.fromData(generate_qr("https://ubuntu.com/desktop")[0])
        path, digest = store_image(image, repo.images)
        repo.add_payload("Image · QR for Ubuntu", "image", 1000, image_path=str(path), digest=digest)
        service.capture("A small place for everything you copy.\n\nSaved on your device. Ready when you need it.")
        repo.close()
        apply_theme(app, "light")
        controller = Controller(app, Settings(theme="light"), root / "settings.json", root / "data", QIcon(str(project / "src/clipo/resources/clipo.svg")))
        controller.window.show()

        def capture_light():
            controller.window.grab().save(str(output / "clipo-light.png"))
            apply_theme(app, "dark")
            QTimer.singleShot(200, capture_dark)

        def capture_dark():
            controller.window.grab().save(str(output / "clipo-dark.png"))
            apply_theme(app, "light")
            from clipo.ui.qr_dialog import QRDialog
            controller.preview_qr = QRDialog("https://ubuntu.com/desktop", controller.jobs, controller.window)
            controller.preview_qr.show()
            controller.preview_qr.generated.connect(lambda _: QTimer.singleShot(100, capture_qr))

        def capture_qr():
            controller.preview_qr.grab().save(str(output / "qr-generator.png"))
            controller.preview_qr.close()
            controller.popup.reveal()
            QTimer.singleShot(200, capture_popup)

        def capture_popup():
            controller.popup.grab().save(str(output / "quick-clipboard.png"))
            controller.popup.hide()
            from clipo.ui.settings_dialog import SettingsDialog
            controller.preview_settings = SettingsDialog(controller.settings, controller.window)
            controller.preview_settings.show()
            QTimer.singleShot(100, capture_settings)

        def capture_settings():
            controller.preview_settings.grab().save(str(output / "settings.png"))
            controller.preview_settings.close()
            app.quit()

        QTimer.singleShot(500, capture_light)
        app.exec()


if __name__ == "__main__":
    main()
