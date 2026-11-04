#!/usr/bin/env python3
"""Check an executable's startup and clean shutdown using isolated data."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def main():
    executable = sys.argv[1]
    with tempfile.TemporaryDirectory(prefix="clipo-binary-check-") as folder:
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        process = subprocess.Popen([executable, "--data-dir", folder], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not (Path(folder) / "history.sqlite3").exists():
                if process.poll() is not None:
                    raise RuntimeError(process.communicate()[1])
                if time.monotonic() > deadline:
                    raise RuntimeError("Executable did not initialize storage")
                time.sleep(.05)
            time.sleep(.2)
        finally:
            process.terminate()
            output, errors = process.communicate(timeout=8)
        if process.returncode != 0:
            raise RuntimeError(f"Unclean executable shutdown: {process.returncode}\n{errors}")
        if (Path(folder) / "instance.lock").exists():
            raise RuntimeError("Instance lock was not removed")
        print(f"PASS: executable startup, storage initialization, SIGTERM shutdown, lock cleanup: {executable}")


if __name__ == "__main__":
    main()
