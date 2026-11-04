"""User-scoped freedesktop autostart; no root changes."""
import os
from pathlib import Path
import sys


def configure_autostart(enabled):
    value = Path(os.environ.get("XDG_CONFIG_HOME", ""))
    root = value if value.is_absolute() else Path.home() / ".config"
    path = root / "autostart/clipo.desktop"
    if not enabled:
        path.unlink(missing_ok=True)
        return
    frozen = getattr(sys, "frozen", False)
    executable = os.environ.get("APPIMAGE") or str(Path(sys.executable).absolute())
    if any(character in executable for character in "\n\r"):
        raise ValueError("Invalid executable path")
    executable = executable.replace("\\", "\\\\\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`").replace("%", "%%")
    path.parent.mkdir(parents=True, exist_ok=True)
    arguments = "" if frozen or os.environ.get("APPIMAGE") else " -m clipo"
    path.write_text(f'[Desktop Entry]\nType=Application\nName=Clipo\nExec="{executable}"{arguments} --background\nTerminal=false\nX-GNOME-Autostart-enabled=true\n', encoding="utf-8")
