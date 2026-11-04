"""Qt clipboard access stays on the GUI thread; persistence is queued elsewhere."""
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QClipboard, QImage
import json


class ClipboardMonitor(QObject):
    captured = Signal(str)
    payload_captured = Signal(object)
    error = Signal(str)
    state_changed = Signal(bool)

    def __init__(self, clipboard: QClipboard, max_text_bytes: int):
        super().__init__()
        self.clipboard = clipboard
        self.max_text_bytes = max_text_bytes
        self.paused = False
        self.private = False
        self.enabled = False
        self.policy = None
        self._restoring = False
        clipboard.dataChanged.connect(self.capture)

    def set_paused(self, paused: bool):
        self.paused = paused
        self.state_changed.emit(self.paused or self.private)

    def set_private(self, private: bool):
        self.private = private
        self.state_changed.emit(self.paused or self.private)

    @Slot()
    def capture(self):
        if not self.enabled or self.paused or self.private or self._restoring or self.clipboard.ownsClipboard():
            return
        try:
            mime = self.clipboard.mimeData()
            if mime is None:
                return
            if self.policy and self.policy.excluded_apps:
                from clipo.system.source import active_application
                from clipo.security.policy import excluded_application
                source = active_application()
                if source is None:
                    self.error.emit("Capture skipped: application exclusions need a reliable X11 application identity. Use private mode on Wayland.")
                    return
                if excluded_application(source, self.policy.excluded_apps):
                    return
            # Respect common password manager hints; general secret detection is Phase 5.
            if any(mime.hasFormat(name) for name in (
                "application/x-keepassxc", "x-kde-passwordManagerHint", "application/x-qt-avoid-clipboard-history",
            )):
                return
            if mime.hasImage():
                image = QImage(mime.imageData())
                if image.width() * image.height() > 32_000_000:
                    self.error.emit("Image exceeds the 32 megapixel limit; it was not saved.")
                elif not image.isNull():
                    self.payload_captured.emit({"image": image.copy()})
                return
            if mime.hasUrls() and any(url.isLocalFile() for url in mime.urls()):
                urls = [url.toString() for url in mime.urls()]
                self.payload_captured.emit({"text": "\n".join(urls), "kind": "files", "metadata": json.dumps(urls)})
                return
            if not mime.hasText():
                return
            text = mime.text()
            if self.policy:
                from clipo.security.policy import excluded_text
                if excluded_text(text, self.policy.block_sensitive, self.policy.excluded_patterns):
                    self.error.emit("Sensitive or excluded text was not saved.")
                    return
            if len(text) > self.max_text_bytes or len(text.encode("utf-8")) > self.max_text_bytes:
                self.error.emit("Clipboard text is too large; it was not saved.")
                return
            if text.strip():
                if mime.hasHtml():
                    html = mime.html()
                    if len(html.encode()) <= self.max_text_bytes:
                        self.payload_captured.emit({"text": text, "kind": "text", "html": html})
                    else:
                        self.captured.emit(text)
                else:
                    self.captured.emit(text)
        except (RuntimeError, UnicodeError):
            self.error.emit("Clipboard could not be read. Try copying the item again.")

    def restore(self, text: str):
        self._restoring = True
        try:
            self.clipboard.setText(text)
        finally:
            self._restoring = False

    def restore_payload(self, item, image=None):
        from PySide6.QtCore import QMimeData, QUrl
        self._restoring = True
        try:
            if item.content_type == "image":
                if image is None or image.isNull():
                    raise ValueError("Image file is missing or unreadable")
                self.clipboard.setImage(image)
            else:
                mime = QMimeData()
                mime.setText(item.content_text)
                if item.content_html:
                    mime.setHtml(item.content_html)
                if item.content_type == "files":
                    urls = json.loads(item.file_metadata)
                    mime.setUrls([QUrl(url) for url in urls])
                    mime.setData("x-special/gnome-copied-files", ("copy\n" + "\n".join(urls)).encode())
                self.clipboard.setMimeData(mime)
        finally:
            self._restoring = False

