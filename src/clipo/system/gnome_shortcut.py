"""Register Clipo's desktop launcher without replacing other custom shortcuts."""
import ast
import shutil
import subprocess

MEDIA_KEYS = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM = MEDIA_KEYS + ".custom-keybinding"
PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/clipo/"


def install_super_v():
    if not shutil.which("gsettings") or not shutil.which("clipo"):
        raise ValueError("Super+V needs gsettings and the installed clipo launcher.")

    def get(schema, key):
        result = subprocess.run(["gsettings", "get", schema, key], capture_output=True, text=True, check=True, timeout=3)
        return ast.literal_eval(result.stdout.strip().removeprefix("@as "))

    def put(schema, key, value):
        subprocess.run(["gsettings", "set", schema, key, repr(value)], capture_output=True, text=True, check=True, timeout=3)

    paths = get(MEDIA_KEYS, "custom-keybindings")
    for path in paths:
        if path != PATH and get(CUSTOM + ":" + path, "binding").lower() in ("<super>v", "<meta>v"):
            raise ValueError("Super+V is assigned to another custom shortcut. Change it in Ubuntu Keyboard Settings first.")
    schema = CUSTOM + ":" + PATH
    put(schema, "name", "Open Clipo")
    put(schema, "command", "clipo")
    put(schema, "binding", "<Super>v")
    if PATH not in paths:
        put(MEDIA_KEYS, "custom-keybindings", paths + [PATH])
    # GNOME normally uses Super+V for notifications. Keep its other bindings.
    shell = "org.gnome.shell.keybindings"
    bindings = get(shell, "toggle-message-tray")
    remaining = [key for key in bindings if key.lower() not in ("<super>v", "<meta>v")]
    if remaining != bindings:
        put(shell, "toggle-message-tray", remaining)
