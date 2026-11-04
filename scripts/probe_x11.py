#!/usr/bin/env python3
"""Run on an isolated X11 display only: exercises real cross-process clipboard I/O."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from PySide6.QtCore import QTimer, QMimeData, QUrl, QThread, QObject, Slot
from PySide6.QtGui import QImage, QColor, QIcon
from PySide6.QtWidgets import QApplication
from clipo.application.controller import Controller
from clipo.config.settings import Settings
from clipo.models.item import HistoryQuery
from clipo.storage.repository import HistoryRepository


def producer():
    app = QApplication([])
    clipboard = app.clipboard()
    text = "  Native X11 বাংলা 👋\n\tExact whitespace  "
    def image():
        value = QImage(80, 50, QImage.Format.Format_RGBA8888)
        value.fill(QColor("#6754d9"))
        clipboard.setImage(value)
    def files():
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile("/tmp/clipo-probe-file.txt")])
        clipboard.setMimeData(mime)
    def rich():
        mime = QMimeData()
        mime.setText("Rich text")
        mime.setHtml("<b>Rich text</b>")
        clipboard.setMimeData(mime)
    for delay, callback in ((100, lambda: clipboard.setText(text)), (350, lambda: clipboard.setText(text)), (600, lambda: clipboard.setText("https://ubuntu.com")), (850, image), (1100, files), (1350, rich), (2000, app.quit)):
        QTimer.singleShot(delay, callback)
    app.exec()


def main():
    if "--producer" in sys.argv:
        producer()
        return
    if os.environ.get("CLIPO_ISOLATED_DISPLAY") != "1":
        sys.exit("Use an isolated Xvfb display and set CLIPO_ISOLATED_DISPLAY=1. This probe modifies that display's clipboard.")
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix="clipo-x11-probe-") as folder:
        root = Path(folder)
        controller = Controller(app, Settings(), root / "settings.json", root / "data", QIcon())
        child = None
        failures = []
        class Probe(QObject):
            @Slot()
            def start(self):
                start()

            @Slot()
            def verify(self):
                verify_restore()

        probe = Probe()
        def start():
            nonlocal child
            print("probe: storage ready on GUI thread", QThread.currentThread() == app.thread(), flush=True)
            child = subprocess.Popen([sys.executable, __file__, "--producer"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            QTimer.singleShot(2500, lambda: controller.command.emit("restore", 3))
            QTimer.singleShot(2900, probe.verify)
        def verify_restore():
            print("probe: verifying clipboard restoration", flush=True)
            image = app.clipboard().image()
            if image.isNull() or image.pixelColor(0, 0) != QColor("#6754d9"):
                failures.append("Image clipboard restore failed")
            app.quit()
        controller.worker.ready.connect(probe.start)
        controller.worker.changed.connect(lambda: print("probe: history changed", flush=True))
        QTimer.singleShot(8000, app.quit)
        app.exec()
        print("probe: event loop closed", flush=True)
        if child:
            child.communicate(timeout=5)
        repo = HistoryRepository(root / "data/history.sqlite3")
        page = repo.page(HistoryQuery())
        assert page.total == 5, f"Expected 5 captures, got {page.total}"
        assert not failures, failures
        text = repo.get(1)
        assert text.content_text == "  Native X11 বাংলা 👋\n\tExact whitespace  "
        assert repo.get(2).content_type == "url"
        assert repo.get(3).content_type == "image"
        assert repo.get(4).content_type == "files"
        assert repo.get(5).content_html == "<b>Rich text</b>"
        repo.close()
        print("PASS: real X11 text/Unicode, consecutive deduplication, URLs, images, file URLs, rich text, image restoration, no restore feedback, clean shutdown")


if __name__ == "__main__":
    main()
