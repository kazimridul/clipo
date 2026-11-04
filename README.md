# Clipo

A native Linux clipboard manager built with Python, PySide6 / Qt 6, SQLite,
Pillow, qrcode, Pygments, and optional local Tesseract OCR. Ubuntu comes first.

**Version 0.3.5 — Ubuntu release candidate.** Fixes the database worker's duplicate
text/HTML filtering using a shared capture policy, with regression tests through
the real Qt worker thread and database.
Defaults to an 8 MiB text limit and
Super+V to open Clipo. QR sharing buttons appear only for supported text, including
code snippets and OCR text. Includes native X11 capture,
optional GNOME Wayland background integration, encrypted history, OCR/QR tools,
and explicit one-time phone sharing. See [release status](docs/ROADMAP.md) for
verified integration coverage and remaining hardware/manual checks.

![Clipo](docs/screenshots/clipo-light.png)

## Install on Ubuntu

The local 0.3.5 test build targets **Ubuntu 25.10 amd64** and requires glibc 2.42
or newer. GitHub Actions release builds target **Ubuntu 24.04+ amd64**.
Python and Qt are bundled; users do not need Python commands to launch the app.

```bash
sudo apt install ./dist/clipo_0.3.5_amd64.deb
```

Then open **Clipo** from the applications menu. Optional OCR uses `tesseract-ocr`
and language packs; the Debian package recommends the English engine/data.

To test the latest standalone build without installing it, run:

```bash
./dist/clipo/clipo
```

The older portable release is `dist/Clipo-0.3.0-x86_64.AppImage`:

```bash
chmod +x dist/Clipo-0.3.0-x86_64.AppImage
./dist/Clipo-0.3.0-x86_64.AppImage
```

If FUSE is unavailable, use `--appimage-extract-and-run`. See the generated
`dist/build-manifest.json` for checksums and the measured minimum glibc version.
These artifacts target amd64 Linux; other architectures need their own build.

Uninstall the Debian package with `sudo apt remove clipo`. User history/settings
are preserved. Login startup is opt-in in Settings. Close minimizes to tray only
when a tray host is available; otherwise close exits. Quit is available in the
tray and via the configured quit shortcut.

## What you can do

- Capture text, HTML, images, URLs, and copied-file URLs on X11 or through the optional GNOME Wayland bridge.
- Restore text, HTML, images, and file URLs; paste into your destination app.
- Search text, OCR results, snippet descriptions, titles, and tags.
- Filter by type, favorites, pins, collections, and date, including custom ranges.
- Sort newest, oldest, or most used; browse bounded history pages.
- Favorite, pin, edit, multi-delete, undo the last 20 individual deletions, or clear
  history with confirmation. Pinned items survive item-count and age cleanup.
- Organize with multiple collections/tags; rename, color, and pin collections.
- View image thumbnails/full images, zoom, copy images, and save PNGs.
- Save snippets with title, description, language, tags, and syntax coloring.
  Format Python with Black, SQL with sqlparse, and JSON with validation/pretty-print/minify.
- Open HTTP(S) links or compose an email through the desktop, on explicit action.
- Generate QR codes from saved or entered text, including OCR text. Configure
  correction, size, and colors; copy/print/export PNG or SVG. Large text can be
  split without truncation. This stays offline and creates no internet link.
- Extract text from images using installed Tesseract languages, save/copy it,
  search it, or generate a QR. Automatic OCR is opt-in.
- Use a searchable quick popup from the main window, tray, or `clipo --quick`.
- Configure shortcuts, with X11 global conflict reporting and opt-in Wayland desktop portal registration.
- Pause recording, use persistent private mode, exclude common credential patterns,
  set literal text/app exclusions, and choose session-only history.
- Set text limits, history count, expiration, appearance, OCR, and login startup.
- Export all, selected, or filtered history to JSON/TXT/CSV/HTML. Portable JSON
  backups include images, tags, snippets, flags, and collection colors/pins.
- Import validated backups, or schedule local backups (latest seven retained).
- Migrate history into a SQLCipher vault with encrypted images, thumbnails, QR files, and authenticated backups. Lock/unlock without saving a passphrase.
- Share selected text/images once with a phone over an explicitly created, expiring local TLS link. No automatic sync or Internet upload.

There are no seeded entries in normal use. Screenshots use a separate temporary
history with synthetic examples. No clipboard data is uploaded or executed automatically.

## Wayland and desktop integration

**GNOME Wayland background capture is available through the optional Clipo
Clipboard Bridge.** The Debian package includes it. Enable **Clipo Clipboard
Bridge** in GNOME's Extensions app; log out/in first if GNOME has not discovered
the newly installed extension. You can also use:

```bash
gnome-extensions enable clipo@clipo.local
```

Source/AppImage users can choose **Library → Install GNOME Wayland bridge**, then
log out/in and enable it. The bridge is opt-in, does not persist clipboard data in
GNOME Shell, checks recording/privacy state before reading, and uses local D-Bus.
Clipo shows whether it is connected and falls back to a limitation notice if its
heartbeat stops. Real background capture tests pass on isolated GNOME 49. Versions
45–50 are declared compatible; the other versions still need desktop acceptance.
Other Wayland compositors require their own backend; Qt/XWayland alone is not a
compositor-wide clipboard manager. See [integration details](docs/WAYLAND.md).

**Super+V (Windows key + V)** opens Clipo. On Ubuntu GNOME it registers a persistent
desktop launcher and removes Super+V from GNOME's notifications binding, preserving
other notification and custom shortcuts. A conflicting custom Super+V binding is
reported without replacing it. Other X11 shortcuts register natively. Other Wayland
desktops can use **Settings → Shortcuts → Request Wayland desktop shortcut permission**
or assign `clipo` manually. Existing saved shortcut and size preferences are retained;
new profiles default to Meta+V and 8 MiB. Other bindings work inside Clipo.

## Automatic GitHub releases

Pull requests targeting `main` run tests, native X11 checks and Ubuntu 24.04 builds.
Every successful push/merge to `main` also publishes a GitHub release with generated
change notes, a Debian installer, AppImage, build manifest and `SHA256SUMS`. GitHub
includes source archives. Builds run directly on GitHub's Ubuntu runners without Docker.

Tags use `v<version>+build.<workflow-run-number>` so each main build gets a unique
release even if the application version has not changed. Re-running a published
build leaves that release untouched. Releases are drafted until assets finish uploading.
The workflow uses the repository's `GITHUB_TOKEN`; it needs no personal token.
Push these workflow changes to GitHub to activate them. Manual workflow runs build
test artifacts without publishing a release.

Application exclusions use active-window hints on X11/the GNOME bridge, not
verified clipboard-owner identity. Unknown identities are skipped when exclusions
are configured. Private mode remains the reliable gate for sensitive work.

Copied files are stored as references, not archived file contents. Qt's PRIMARY
selection is not recorded. Content restoration does not inject an automatic
paste or execute scripts. Arbitrary custom MIME payloads are not preserved.

## Privacy and data

- Persistent database: `$XDG_DATA_HOME/clipo/history.sqlite3`, normally
  `~/.local/share/clipo/history.sqlite3`; images and QR files live alongside it.
- Settings: `$XDG_CONFIG_HOME/clipo/settings.json`, normally
  `~/.config/clipo/settings.json`. App directories use `0700`, private files `0600`.
- Storage is unencrypted by default. **Library → Encrypt history** migrates into
  `clipo/vault/` using SQLCipher, with AES-256-GCM protected images/thumbnails/QR
  files and authenticated `.clipo` automatic backups. Startup/unlock asks for the
  passphrase; it is never written to settings. Lock clears previews and key references.
- Migration verifies the new store before optionally removing original unencrypted
  files. External exports/backups are not removed; SSDs/snapshots may retain old
  data. Plain exports remain explicitly selectable. See [vault details](docs/SECURITY.md).
- Credential detection catches common patterns, Luhn-valid card-like numbers, and
  password-manager hints; it cannot recognize every secret. Use private mode.
- Pause/private mode persist across restarts. Resuming does not retrospectively
  ingest text copied while recording was off, or the clipboard present at startup.
- Turning persistence off opens fresh in-memory SQLite history. Temporary image
  files are deleted on exit. Previous disk history is preserved and returns when
  persistence is re-enabled. It is not imported into the session automatically.
- Deletion is logical, with no claim of forensic secure erasure on SSDs, SQLite
  journals, backups, or snapshots. Manual exports remain until you remove them.
- Default text limit: 8 MiB; maximum image: 32 megapixels. Oversized captures are
  rejected, never silently truncated. Large visible previews are explicitly bounded;
  copying restores the entire stored content. JSON backup size limit: 128 MiB.

## Development

Python 3.11+ is required. On Ubuntu 24.04+:

```bash
sudo apt install python3-venv libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,build]'
.venv/bin/clipo
```

Use `--data-dir /tmp/clipo-sandbox` for isolated history/settings. The optional
`scripts/install_desktop.py` installs a development launcher pointing at this
checkout's `.venv`; its `--uninstall` removes only that launcher.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/preview.py
```

The full suite passes **72 tests** in the clean Ubuntu 24.04 container, including
real Tesseract and single-instance local-socket tests. Restricted environments
skip unavailable engine/socket checks explicitly. A separate real X11 probe uses
an isolated Xvfb display. `scripts/run_wayland_probe.py` runs the GNOME bridge in
an independent headless session with temporary settings. Neither uses your desktop
clipboard. Portal tests use a private D-Bus daemon; sharing tests use loopback TLS.
Run `.venv/bin/clipo --self-test` to check bundled engines without user data.

See [validation](docs/VALIDATION.md), [Ubuntu testing](docs/UBUNTU_TESTING.md),
[architecture](docs/ARCHITECTURE.md), and [packaging](docs/PACKAGING.md).
