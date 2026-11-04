import json

import pytest

from clipo.config.settings import Settings, xdg_path


def test_new_install_defaults():
    assert Settings().max_text_bytes == 8 * 1024 * 1024
    assert Settings().quick_shortcut == "Meta+V"


def test_settings_roundtrip_and_permissions(tmp_path):
    path = tmp_path / "config" / "settings.json"
    settings = Settings(theme="dark", history_limit=0, paused=True, private=True)
    settings.save(path)
    assert Settings.load(path) == settings
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("data", [[], {"history_limit": -1}, {"theme": "unknown"}, {"paused": "false"}, {"private": 1}, {"max_text_bytes": 0}])
def test_reject_bad_settings(tmp_path, data):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data))
    with pytest.raises((ValueError, TypeError)):
        Settings.load(path)


def test_xdg_ignores_relative_directory(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "relative")
    assert xdg_path("XDG_DATA_HOME", ".local/share").is_absolute()
