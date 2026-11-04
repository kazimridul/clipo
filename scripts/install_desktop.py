#!/usr/bin/env python3
"""Install/remove a development launcher without root or altering saved history."""
import argparse
import os
from pathlib import Path
import sys


def desktop_quote(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("Desktop launcher paths cannot contain line breaks")
    # Desktop Entry string escaping followed by Exec argument escaping.
    value = value.replace("\\", "\\\\\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return '"' + value.replace("%", "%%") + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    xdg = Path(os.environ.get("XDG_DATA_HOME", ""))
    data = xdg if xdg.is_absolute() else Path.home() / ".local/share"
    target = data / "applications" / "clipo.desktop"
    if args.uninstall:
        target.unlink(missing_ok=True)
        print("Clipo launcher removed. History and settings preserved.")
        return
    root = Path(__file__).resolve().parents[1]
    executable = root / ".venv/bin/clipo"
    if not executable.exists():
        sys.exit("Install Clipo in .venv first; see README.md.")
    target.parent.mkdir(parents=True, exist_ok=True)
    icon = str(root / "src/clipo/resources/clipo.svg").replace("\\", "\\\\")
    if "\n" in icon or "\r" in icon:
        sys.exit("Unsupported line break in checkout path")
    target.write_text(
        "[Desktop Entry]\nType=Application\nVersion=1.0\nName=Clipo\n"
        "Comment=Local clipboard history\n"
        f"Exec={desktop_quote(str(executable))}\nIcon={icon}\n"
        "Terminal=false\nCategories=Utility;\nStartupNotify=true\n",
        encoding="utf-8",
    )
    print(f"Clipo launcher installed: {target}")


if __name__ == "__main__":
    main()
