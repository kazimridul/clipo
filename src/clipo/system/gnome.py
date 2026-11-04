"""Install the bundled bridge only after an explicit user action."""
import os
from pathlib import Path
import shutil
import sys


def install_bridge():
    candidate = Path(os.environ.get("XDG_DATA_HOME", ""))
    data = candidate if candidate.is_absolute() else Path.home() / ".local/share"
    source = Path(__file__).parents[1] / "resources/gnome/clipo@clipo.local"
    if not source.exists():
        source = Path(__file__).parents[3] / "integrations/gnome/clipo@clipo.local"
    if not source.exists():
        source = Path(sys.prefix) / "share/clipo/gnome/clipo@clipo.local"
    target = data / "gnome-shell/extensions/clipo@clipo.local"
    shutil.copytree(source, target, dirs_exist_ok=True)
    return str(target)
