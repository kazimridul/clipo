"""A local, opt-in GNOME Shell bridge. Clipboard data never leaves the session bus."""
import base64
import json
import os
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QObject, Signal, Slot, ClassInfo, QTimer
from PySide6.QtDBus import QDBusConnection
from clipo.security.policy import excluded_application, excluded_payload

SERVICE = "com.clipo.Clipboard"
OBJECT = "/com/clipo/Clipboard"


@ClassInfo({"D-Bus Interface": "com.clipo.Clipboard1"})
class GnomeBridge(QObject):
    payload = Signal(object)
    status = Signal(bool)
    error = Signal(str)

    def __init__(self, monitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.bus = QDBusConnection.sessionBus()
        platform = QGuiApplication.platformName()
        wayland = "wayland" in platform or os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
        # Offscreen and isolated X11 tests must never claim the user's live bridge.
        self.available = platform not in ("offscreen", "minimal") and wayland and self.bus.isConnected() and self.bus.registerService(SERVICE)
        if self.available:
            self.available = self.bus.registerObject(OBJECT, self, QDBusConnection.RegisterOption.ExportAllSlots)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(25000)
        self.timer.timeout.connect(self.expired)

    def allowed(self, source):
        policy = self.monitor.policy
        if not self.monitor.enabled or self.monitor.private or self.monitor.paused:
            return False
        return not (policy and policy.excluded_apps and (not source or excluded_application(source, policy.excluded_apps)))

    @Slot(str, result=str)
    def Status(self, source):
        self.timer.start()
        self.status.emit(True)
        return json.dumps({"enabled": self.allowed(source), "max_text_bytes": self.monitor.max_text_bytes, "max_image_bytes": 16 * 1024 * 1024})

    @Slot(str, result=bool)
    def Ingest(self, value):
        if len(value) > 24 * 1024 * 1024:
            self.error.emit("GNOME bridge rejected an oversized clipboard payload")
            return False
        try:
            data = json.loads(value)
            if not isinstance(data, dict) or not isinstance(data.get("source", ""), str) or not self.allowed(data.get("source", "")) or self.monitor.clipboard.ownsClipboard():
                return False
            kind = data.get("kind")
            if kind == "image":
                raw = base64.b64decode(data["data"], validate=True)
                if len(raw) > 16 * 1024 * 1024:
                    raise ValueError()
                self.payload.emit({"encoded_image": raw})
            elif kind in ("text", "files"):
                text, html = data.get("text", ""), data.get("html", "")
                if not isinstance(text, str) or not isinstance(html, str) or len(text.encode()) + len(html.encode()) > self.monitor.max_text_bytes:
                    raise ValueError()
                policy = self.monitor.policy
                # VS Code includes highlighted HTML. Appending it to Python source
                # makes valid code unparsable and defeats reference recognition.
                if policy and excluded_payload(text, html, policy.block_sensitive, policy.excluded_patterns):
                    self.error.emit("Sensitive or excluded text was not saved. Check Settings → Privacy if this is unexpected.")
                    return False
                if kind == "files":
                    urls = [line for line in text.splitlines() if line and not line.startswith("#")]
                    if not urls:
                        return False
                    if all(url.startswith(("https://", "http://")) for url in urls):
                        self.payload.emit({"kind": "text", "text": "\n".join(urls)})
                    elif all(url.startswith("file:///") for url in urls):
                        self.payload.emit({"kind": "files", "text": "\n".join(urls), "metadata": json.dumps(urls)})
                    else:
                        raise ValueError()
                elif text.strip():
                    self.payload.emit({"text": text, "html": html, "kind": "text"})
            else:
                raise ValueError()
            return True
        except (ValueError, KeyError, TypeError):
            self.error.emit("GNOME bridge rejected invalid clipboard content")
            return False

    @Slot(str)
    def ReportError(self, message):
        # Never display arbitrary clipboard contents supplied as an error.
        self.error.emit("GNOME bridge could not capture this item (unsupported format or size limit).")

    def expired(self):
        self.status.emit(False)

    def close(self):
        self.timer.stop()
        if self.available:
            self.bus.unregisterObject(OBJECT)
            self.bus.unregisterService(SERVICE)
