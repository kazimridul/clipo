"""Qt clipboard access stays on the GUI thread; persistence is queued elsewhere."""
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QClipboard


class ClipboardMonitor(QObject):
    captured = Signal(str)
    error = Signal(str)
    state_changed = Signal(bool)

    def __init__(self, clipboard: QClipboard, max_text_bytes: int):
        super().__init__()
        self.clipboard = clipboard
        self.max_text_bytes = max_text_bytes
        self.paused = False
        self.private = False
        self.enabled = False
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
            if mime is None or not mime.hasText() or mime.hasImage() or mime.hasUrls():
                return
            # Respect common password manager hints; general secret detection is Phase 5.
            if any(mime.hasFormat(name) for name in (
                "application/x-keepassxc", "x-kde-passwordManagerHint", "application/x-qt-avoid-clipboard-history",
            )):
                return
            text = mime.text()
            if len(text) > self.max_text_bytes or len(text.encode("utf-8")) > self.max_text_bytes:
                self.error.emit("Clipboard text is too large; it was not saved.")
                return
            if text.strip():
                self.captured.emit(text)
        except (RuntimeError, UnicodeError):
            self.error.emit("Clipboard could not be read. Try copying the item again.")

    def restore(self, text: str):
        self._restoring = True
        try:
            self.clipboard.setText(text)
        finally:
            self._restoring = False

