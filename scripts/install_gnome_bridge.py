#!/usr/bin/env python3
"""Install/remove the opt-in GNOME bridge for the current user, without root."""
import argparse
import os
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    value = Path(os.environ.get("XDG_DATA_HOME", ""))
    data = value if value.is_absolute() else Path.home() / ".local/share"
    target = data / "gnome-shell/extensions/clipo@clipo.local"
    if args.uninstall:
        shutil.rmtree(target, ignore_errors=True)
        print("Removed Clipo bridge. Disable it in Extensions first if currently enabled.")
    else:
        source = Path(__file__).resolve().parents[1] / "integrations/gnome/clipo@clipo.local"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
        print("Bridge installed. Log out/in if newly installed, then enable Clipo Clipboard Bridge in Extensions.")


if __name__ == "__main__":
    main()
