"""Conservative capability reporting; QClipboard is not a Wayland data-control adapter."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ClipboardCapability:
    background_supported: bool
    message: str


def capability(qt_platform: str) -> ClipboardCapability:
    wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
    if qt_platform in ("offscreen", "minimal"):
        return ClipboardCapability(False, "Test display · clipboard access is limited to this process.")
    if "wayland" in qt_platform or wayland:
        return ClipboardCapability(False, "Wayland · enable the optional Clipo GNOME Clipboard Bridge for background capture (Library → Install bridge). Without a supported bridge, only events Qt delivers can be recorded.")
    if qt_platform == "xcb":
        return ClipboardCapability(True, "X11 · background clipboard monitoring available")
    return ClipboardCapability(False, "Unverified display backend · background capture is not guaranteed.")

