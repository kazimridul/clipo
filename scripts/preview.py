#!/usr/bin/env python3
"""Render both themes with synthetic data, without accessing the desktop clipboard."""
import os
from pathlib import Path
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from clipo.application.controller import Controller
from clipo.config.settings import Settings
from clipo.storage.repository import HistoryRepository
from clipo.ui.theme import apply_theme


def main():
    project = Path(__file__).resolve().parents[1]
    output = project / "docs/screenshots"
    output.mkdir(exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="clipo-preview-") as folder:
        root = Path(folder)
        repo = HistoryRepository(root / "data/history.sqlite3")
        for text in (
            "Design notes\nKeep it simple. Make finding the right clip feel effortless.",
            "https://ubuntu.com/desktop",
            "git status --short",
            "A small place for everything you copy.\n\nClipo remembers useful text, so you can stay focused on what comes next.\n\nSaved on your device. Ready when you need it.",
        ):
            repo.add(text, 1000)
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
            app.quit()

        QTimer.singleShot(500, capture_light)
        app.exec()


if __name__ == "__main__":
    main()
