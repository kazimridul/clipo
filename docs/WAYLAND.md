# Wayland integration

## GNOME

The production extension is `integrations/gnome/clipo@clipo.local`. It listens to
`Meta.Selection::owner-changed`, never polls clipboard content, and reads through
`St.Clipboard`. Before each read it asks Clipo whether recording is allowed, then
sends a bounded payload through the user's session D-Bus. Text, PNG images, HTML
alongside text, and file URLs are supported. Password-manager MIME hints are skipped.
There is no clipboard history stored in GNOME Shell, no initial clipboard read,
and no network endpoint in the bridge.

The bridge disconnects selection handlers, cancels pending D-Bus work, and removes
its heartbeat on disable. Clipo marks the backend disconnected after 25 seconds
without a heartbeat; capture then falls back to limited Qt behavior with a notice.
Without Clipo running, the extension does not read content. Pause/private/lock are
checked both before reading and again before ingest. Application identity is an
active-window hint; it is not a cryptographically verified clipboard-owner identity.

Debian installs the optional extension under `/usr/share/gnome-shell/extensions`.
AppImage/source users can install their bundled copy from Library. GNOME must
rediscover newly installed extensions (log out/in), then the user must enable it.
Clipo never enables an extension behind the user's back.

Enable: `gnome-extensions enable clipo@clipo.local`
Disable: `gnome-extensions disable clipo@clipo.local`

The UUID declares GNOME 45–50; automated real-compositor coverage currently uses
GNOME 49. The probe starts a private D-Bus daemon, an independent headless GNOME,
temporary XDG directories, and a test-only producer extension. It never changes
host extension settings or the user's clipboard:

```bash
.venv/bin/python scripts/run_wayland_probe.py
```

The test producer is never included in packages or installed by the app. Tests
verify background Unicode/whitespace, deduplication, URLs, PNG, file URLs, private
mode, and resume without ingesting the private clipboard.

## Global shortcuts

An opt-in `org.freedesktop.portal.GlobalShortcuts` client registers desktop identity,
creates a session, subscribes before requesting permissions, binds the quick action,
handles activation/denial, and closes requests/sessions. It runs off the UI thread.
Settings controls whether the portal is requested. The desktop owns the permission
dialog; Clipo cannot grant itself approval. A missing/denied portal produces an
explicit manual `clipo --quick` fallback. Private mock-portal tests exercise the
real D-Bus wire protocol, not a replacement for each desktop's permission UI.

References: [GNOME St clipboard API](https://gnome.pages.gitlab.gnome.org/gnome-shell/st/class.Clipboard.html),
[XDG GlobalShortcuts](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html),
[host portal registry](https://github.com/flatpak/xdg-desktop-portal/blob/main/data/org.freedesktop.host.portal.Registry.xml).

## Other compositors

X11 capture continues to work through Qt. GNOME-specific integration is not claimed
for KDE/wlroots. Those desktops show restricted access until a suitable adapter is
implemented. No foreground clipboard event is treated as proof of full background
support on an unsupported compositor.
