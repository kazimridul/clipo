import ast
from types import SimpleNamespace

import pytest
from clipo.system.gnome_shortcut import CUSTOM, MEDIA_KEYS, PATH, install_super_v


def desktop(monkeypatch, conflict=False):
    other = "/existing-shortcut/"
    state = {
        (MEDIA_KEYS, "custom-keybindings"): [other],
        (CUSTOM + ":" + other, "binding"): "<Super>v" if conflict else "<Super>x",
        ("org.gnome.shell.keybindings", "toggle-message-tray"): ["<Super>v", "<Super>m"],
    }

    def run(args, **kwargs):
        _, operation, schema, key, *value = args
        if operation == "set":
            state[schema, key] = ast.literal_eval(value[0])
        return SimpleNamespace(stdout=repr(state.get((schema, key), "")))

    monkeypatch.setattr("clipo.system.gnome_shortcut.shutil.which", lambda command: "/usr/bin/" + command)
    monkeypatch.setattr("clipo.system.gnome_shortcut.subprocess.run", run)
    return state


def test_super_v_preserves_other_shortcuts_and_is_idempotent(monkeypatch):
    state = desktop(monkeypatch)
    install_super_v()
    install_super_v()
    assert state[MEDIA_KEYS, "custom-keybindings"] == ["/existing-shortcut/", PATH]
    assert state[CUSTOM + ":" + PATH, "binding"] == "<Super>v"
    assert state[CUSTOM + ":" + PATH, "command"] == "clipo"
    assert state["org.gnome.shell.keybindings", "toggle-message-tray"] == ["<Super>m"]


def test_super_v_does_not_overwrite_another_custom_shortcut(monkeypatch):
    state = desktop(monkeypatch, conflict=True)
    before = dict(state)
    with pytest.raises(ValueError, match="another custom shortcut"):
        install_super_v()
    assert state == before
