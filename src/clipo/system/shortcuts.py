"""Native X11 grab with conflict reporting; Wayland uses a desktop-owned binding."""
import os
from PySide6.QtCore import QObject, Signal, QSocketNotifier


def parse_shortcut(value):
    parts = value.split("+")
    if len(parts) < 2 or not parts[-1]:
        raise ValueError("Use a modifier and a key, for example Ctrl+Shift+V")
    modifiers = {"Ctrl": 4, "Shift": 1, "Alt": 8, "Meta": 64}
    mask = 0
    for part in parts[:-1]:
        if part not in modifiers:
            raise ValueError("Supported modifiers: Ctrl, Shift, Alt, Meta")
        mask |= modifiers[part]
    return parts[-1], mask


class GlobalShortcut(QObject):
    activated = Signal()
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.display = None
        self.notifier = None

    def bind(self, shortcut, platform):
        self.close()
        key, mask = parse_shortcut(shortcut)
        if platform != "xcb" or os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
            self.status.emit("Global shortcut: configure your desktop to run ‘clipo --quick’. In-app shortcut is available.")
            return
        try:
            from Xlib import X, XK, display
            from Xlib.error import CatchError, BadAccess
            self.display = display.Display()
            key = {"Space": "space", "Esc": "Escape", "Enter": "Return", "Del": "Delete"}.get(key, key)
            keysym = XK.string_to_keysym(key.lower() if len(key) == 1 else key)
            code = self.display.keysym_to_keycode(keysym)
            if not code:
                raise ValueError("The shortcut key is not available in the current keyboard layout")
            self.root = self.display.screen().root
            self.code, self.mask = code, mask
            catcher = CatchError(BadAccess)
            for locks in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                self.root.grab_key(code, mask | locks, False, X.GrabModeAsync, X.GrabModeAsync, onerror=catcher)
            self.display.sync()
            if catcher.get_error():
                raise ValueError("Global shortcut conflicts with another application")
            self.notifier = QSocketNotifier(self.display.fileno(), QSocketNotifier.Type.Read, self)
            self.notifier.activated.connect(self._events)
            self.status.emit(f"Global shortcut active: {shortcut}")
        except Exception as error:
            self.close()
            self.status.emit(str(error) if isinstance(error, ValueError) else "X11 global shortcut unavailable; bind clipo --quick in desktop settings.")

    def _events(self, *_):
        from Xlib import X
        while self.display and self.display.pending_events():
            event = self.display.next_event()
            if event.type == X.KeyPress and event.detail == self.code:
                self.activated.emit()

    def close(self):
        if self.notifier:
            self.notifier.setEnabled(False)
            self.notifier.deleteLater()
            self.notifier = None
        if self.display:
            self.display.close()
            self.display = None
