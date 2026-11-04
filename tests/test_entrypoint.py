import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest


def test_process_launch_single_instance_and_clean_termination(tmp_path):
    # Restricted containers may forbid Unix sockets even with an offscreen GUI.
    with socket.socket(socket.AF_UNIX) as probe:
        probe_path = str(tmp_path / "probe.sock")
        try:
            probe.bind(probe_path)
        except PermissionError:
            pytest.skip("This sandbox blocks the local activation socket; run outside it")
    Path(probe_path).unlink()
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    command = [sys.executable, "-m", "clipo", "--data-dir", str(tmp_path)]
    first = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 8
        while not (tmp_path / "history.sqlite3").exists():
            assert first.poll() is None, first.communicate()
            assert time.monotonic() < deadline, "First instance did not initialize"
            time.sleep(0.05)
        second = subprocess.run(command, env=env, capture_output=True, text=True, timeout=8)
        assert second.returncode == 0, second.stderr
        assert first.poll() is None
    finally:
        first.terminate()
        output, errors = first.communicate(timeout=8)
    assert first.returncode == 0, errors
    assert not (tmp_path / "instance.lock").exists()
    assert "QThread: Destroyed" not in errors


def test_desktop_launcher_install_remove_preserves_history(tmp_path):
    env = {**os.environ, "XDG_DATA_HOME": str(tmp_path)}
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/install_desktop.py"
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    desktop = tmp_path / "applications/clipo.desktop"
    assert f'Exec="{root}/.venv/bin/clipo"' in desktop.read_text()
    history = tmp_path / "clipo/history.sqlite3"
    history.parent.mkdir()
    history.write_text("preserved")
    removed = subprocess.run([sys.executable, str(script), "--uninstall"], env=env, capture_output=True, text=True)
    assert removed.returncode == 0
    assert not desktop.exists()
    assert history.read_text() == "preserved"
