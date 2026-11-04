#!/usr/bin/env python3
"""Create an isolated headless GNOME session for the native clipboard probe."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def session():
    if os.environ.get("CLIPO_PRIVATE_GNOME_TEST") != "1":
        raise SystemExit("This entry point requires the isolated test environment")
    subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", "['clipo@clipo.local','test-producer@clipo.local']"], check=True)
    log_path = Path(os.environ["XDG_CACHE_HOME"]) / "shell.log"
    with log_path.open("w") as log:
        shell = subprocess.Popen(["gnome-shell", "--headless", "--wayland", "--no-x11", "--virtual-monitor", "1280x900", "--wayland-display", "clipo-test"], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 15
            while True:
                result = subprocess.run(["gnome-extensions", "info", "test-producer@clipo.local"], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and "ACTIVE" in result.stdout:
                    break
                if shell.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Isolated GNOME test producer did not start")
                time.sleep(.2)
            env = {**os.environ, "WAYLAND_DISPLAY": "clipo-test", "QT_QPA_PLATFORM": "wayland", "CLIPO_ISOLATED_DISPLAY": "1"}
            subprocess.run([sys.executable, str(ROOT / "scripts/probe_wayland.py")], env=env, check=True, timeout=20)
        finally:
            shell.terminate()
            shell.wait(timeout=8)


def main():
    if "--session" in sys.argv:
        session()
        return
    for executable in ("gnome-shell", "gnome-extensions", "dbus-run-session", "gsettings"):
        if not shutil.which(executable):
            raise SystemExit(f"This optional integration probe needs {executable}")
    with tempfile.TemporaryDirectory(prefix="clipo-gnome-test-", ignore_cleanup_errors=True) as folder:
        root = Path(folder)
        for name in ("runtime", "data", "config", "cache"):
            (root / name).mkdir(mode=0o700)
        for source in (ROOT / "integrations/gnome/clipo@clipo.local", ROOT / "scripts/fixtures/gnome-producer/test-producer@clipo.local"):
            shutil.copytree(source, root / "data/gnome-shell/extensions" / source.name)
        env = {**os.environ, "XDG_RUNTIME_DIR": str(root / "runtime"), "XDG_DATA_HOME": str(root / "data"), "XDG_CONFIG_HOME": str(root / "config"), "XDG_CACHE_HOME": str(root / "cache"),
            "GSETTINGS_BACKEND": "keyfile", "XDG_SESSION_TYPE": "wayland", "GNOME_SHELL_SESSION_MODE": "user", "LIBGL_ALWAYS_SOFTWARE": "1", "CLIPO_PRIVATE_GNOME_TEST": "1"}
        for name in ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
            env.pop(name, None)
        process = subprocess.Popen(["dbus-run-session", "--", sys.executable, __file__, "--session"], env=env, start_new_session=True)
        try:
            result = process.wait(timeout=50)
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.wait(timeout=8)
            # A private document portal can leave a dead FUSE mount on shutdown.
            unmount = shutil.which("fusermount3") or shutil.which("fusermount")
            if unmount:
                subprocess.run([unmount, "-uz", str(root / "runtime/doc")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result:
            print((root / "cache/shell.log").read_text()[-3000:])
            raise SystemExit(result)


if __name__ == "__main__":
    main()
