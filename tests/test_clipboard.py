import pytest
from PySide6.QtCore import QMimeData, QObject, Signal

from clipo.clipboard.monitor import ClipboardMonitor
from clipo.clipboard.platform import capability


class ExternalClipboard(QObject):
    """Simulate a clipboard event from another application, including MIME hints."""
    dataChanged = Signal()

    def __init__(self):
        super().__init__()
        self.mime = QMimeData()
        self.owned = False

    def ownsClipboard(self):
        return self.owned

    def mimeData(self):
        return self.mime

    def setText(self, text):
        self.mime.setText(text)
        self.dataChanged.emit()


def test_capture_pause_private_and_restore(qtbot):
    clipboard = ExternalClipboard()
    monitor = ClipboardMonitor(clipboard, 1024)
    monitor.enabled = True
    saved = []
    monitor.captured.connect(saved.append)
    clipboard.setText("first")
    monitor.set_paused(True)
    clipboard.setText("paused secret")
    monitor.set_paused(False)
    monitor.set_private(True)
    clipboard.setText("private secret")
    monitor.set_private(False)
    assert saved == ["first"]  # Resuming does not ingest the private clipboard.
    monitor.restore("previous text")
    assert clipboard.mime.text() == "previous text"
    assert saved == ["first"]
    clipboard.setText("second")
    assert saved == ["first", "second"]


@pytest.mark.parametrize("hint", ["application/x-keepassxc", "x-kde-passwordManagerHint", "application/x-qt-avoid-clipboard-history"])
def test_password_manager_hints_are_respected(qtbot, hint):
    clipboard = ExternalClipboard()
    monitor = ClipboardMonitor(clipboard, 1024)
    monitor.enabled = True
    saved = []
    monitor.captured.connect(saved.append)
    clipboard.mime.setData(hint, b"secret")
    clipboard.setText("do not keep")
    assert not saved


def test_oversize_and_own_clipboard_are_skipped(qtbot):
    clipboard = ExternalClipboard()
    monitor = ClipboardMonitor(clipboard, 8)
    monitor.enabled = True
    saved, errors = [], []
    monitor.captured.connect(saved.append)
    monitor.error.connect(errors.append)
    clipboard.setText("🙂🙂🙂")
    assert errors and not saved
    clipboard.owned = True
    clipboard.setText("mine")
    assert not saved


def test_real_qclipboard_restores_exact_text(qapp):
    monitor = ClipboardMonitor(qapp.clipboard(), 1024)
    text = "  বাংলা\nhello 👋\t"
    monitor.restore(text)
    assert qapp.clipboard().text() == text


def test_wayland_and_xwayland_are_reported_as_limited(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert not capability("wayland").background_supported
    assert not capability("xcb").background_supported
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert capability("xcb").background_supported
    assert not capability("offscreen").background_supported
