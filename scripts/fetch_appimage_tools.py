#!/usr/bin/env python3
"""Download official AppImage tools and verify the repository's pinned hashes."""
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen


def main():
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=True)
    pins = json.loads((Path(__file__).resolve().parents[1] / "packaging/appimage-tools.json").read_text())
    for name, pin in pins.items():
        with urlopen(pin["url"], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != pin["sha256"]:
            raise SystemExit(f"{name} checksum mismatch: update the pinned tool only after verification")
        file = target / name
        file.write_bytes(data)
        file.chmod(0o755)
        print(f"Verified {name}")


if __name__ == "__main__":
    main()
