# Clipo

A native Linux clipboard manager built with Python, PySide6 / Qt 6, SQLite,
Pillow, qrcode, Pygments, and optional local Tesseract OCR. Ubuntu comes first.

**Version 0.2.0 — feature release candidate.** The core functionality from phases
2–6 is implemented and tested. This is not a declaration that every requirement
or desktop acceptance check in the full product specification is complete.
See [phase status and remaining work](docs/ROADMAP.md).

![Clipo](docs/screenshots/clipo-light.png)

## Install on Ubuntu

The release artifacts are built from an isolated **Ubuntu 24.04 amd64** environment.
Python and Qt are bundled; users do not need Python commands to launch the app.

```bash
sudo apt install ./dist/clipo_0.2.0_amd64.deb
```

Then open **Clipo** from the applications menu. Optional OCR uses `tesseract-ocr`
and language packs; the Debian package recommends the English engine/data.

The portable alternative is `dist/Clipo-0.2.0-x86_64.AppImage`:

```bash
chmod +x dist/Clipo-0.2.0-x86_64.AppImage
./dist/Clipo-0.2.0-x86_64.AppImage
```

If FUSE is unavailable, use `--appimage-extract-and-run`. See the generated
`dist/build-manifest.json` for checksums and the measured minimum glibc version.
These artifacts target amd64 Linux; other architectures need their own build.

Uninstall the Debian package with `sudo apt remove clipo`. User history/settings
are preserved. Login startup is opt-in in Settings. Close minimizes to tray only
when a tray host is available; otherwise close exits. Quit is available in the
tray and via the configured quit shortcut.

## What you can do

- Capture text, rich text/HTML, images, URLs, and copied-file URLs on X11.
- Restore text, HTML, images, and file URLs; paste into your destination app.
- Search text, OCR results, snippet descriptions, titles, and tags.
- Filter by type, favorites, pins, collections, and date, including custom ranges.
- Sort newest, oldest, or most used; browse bounded history pages.
- Favorite, pin, edit, multi-delete, undo the last 20 individual deletions, or clear
  history with confirmation. Pinned items survive item-count and age cleanup.
- Organize with multiple collections/tags; rename, color, and pin collections.
- View image thumbnails/full images, zoom, copy images, and save PNGs.
- Save snippets with title, description, language, tags, and syntax coloring.
  JSON can be validated through formatting, pretty-printed, and minified.
- Open HTTP(S) links or compose an email through the desktop, on explicit action.
- Generate QR codes from saved or entered text, including OCR text. Configure
  correction, size, and colors; copy/print/export PNG or SVG. Large text can be
  split without truncation. This stays offline and creates no internet link.
- Extract text from images using installed Tesseract languages, save/copy it,
  search it, or generate a QR. Automatic OCR is opt-in.
- Use a searchable quick popup from the main window, tray, or `clipo --quick`.
- Configure quick access and in-app shortcuts, with X11 global conflict reporting.
- Pause recording, use persistent private mode, exclude common credential patterns,
  set literal text/app exclusions, and choose session-only history.
- Set text limits, history count, expiration, appearance, OCR, and login startup.
- Export all, selected, or filtered history to JSON/TXT/CSV/HTML. Portable JSON
  backups include images, tags, snippets, flags, and collection colors/pins.
- Import validated backups, or schedule local backups (latest seven retained).

There are no seeded entries in normal use. Screenshots use a separate temporary
history with synthetic examples. No clipboard data is uploaded or executed.

## Wayland and desktop limitations

**Full GNOME/Wayland background capture is not implemented.** A persistent notice
reports restricted access; only clipboard events actually delivered by Qt are
recorded. XWayland does not establish compositor-wide access. Use an Ubuntu on
Xorg session for the implemented background backend. See
[Qt's clipboard API](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QClipboard.html).

On X11, Clipo registers its quick-popup shortcut natively. On Wayland, assign
**`clipo --quick`** to a shortcut in your desktop settings. Automatic portal binding
is not implemented. Other configurable bindings work inside Clipo.

Application exclusions use best-effort X11 active-window identity, not a verified
clipboard-owner identity. If exclusions are configured and identity is unavailable,
capture stops with an explanation. Use private mode for sensitive work.

Copied files are stored as references, not archived file contents. Qt's PRIMARY
selection is not recorded. Content restoration does not inject an automatic
paste or execute scripts. Arbitrary custom MIME payloads are not preserved.

## Privacy and data

- Persistent database: `$XDG_DATA_HOME/clipo/history.sqlite3`, normally
  `~/.local/share/clipo/history.sqlite3`; images and QR files live alongside it.
- Settings: `$XDG_CONFIG_HOME/clipo/settings.json`, normally
  `~/.config/clipo/settings.json`. App directories use `0700`, private files `0600`.
- Storage and backups are **unencrypted**. Database encryption is not implemented.
  Credential detection catches common patterns and password-manager MIME hints;
  it cannot recognize every secret. Private mode is the reliable recording gate.
- Pause/private mode persist across restarts. Resuming does not retrospectively
  ingest text copied while recording was off, or the clipboard present at startup.
- Turning persistence off opens fresh in-memory SQLite history. Temporary image
  files are deleted on exit. Previous disk history is preserved and returns when
  persistence is re-enabled. It is not imported into the session automatically.
- Deletion is logical, with no claim of forensic secure erasure on SSDs, SQLite
  journals, backups, or snapshots. Manual exports remain until you remove them.
- Default text limit: 1 MiB; maximum image: 32 megapixels. Oversized captures are
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

The full suite passes **56 tests** in the clean Ubuntu 24.04 container, including
real Tesseract and single-instance local-socket tests. Restricted environments
skip unavailable engine/socket checks explicitly. A separate real X11 probe uses
an isolated Xvfb display, never the user's desktop clipboard.

See [validation](docs/VALIDATION.md), [Ubuntu testing](docs/UBUNTU_TESTING.md),
[architecture](docs/ARCHITECTURE.md), and [packaging](docs/PACKAGING.md).
