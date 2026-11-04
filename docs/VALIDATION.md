# Validation record

Date: 4 November 2026. Release candidate: Clipo 0.2.0.

| Check | Result |
| --- | --- |
| Clean Ubuntu 24.04 / Python 3.12 source suite | **56 passed**, including real Tesseract and local activation sockets |
| Development workspace, Python 3.13 / Qt 6.12 | Tests pass; isolated engine/socket requirements skip explicitly when unavailable |
| Existing Phase 1 database → schema 4 | Passed, with original text preserved |
| Images, normalized hashing, private files, deduplication, cleanup and undo | Passed |
| Favorites, pins, collections/colors, tags, snippet descriptions and FTS maintenance | Passed |
| Literal search, date boundaries, pagination, exact Unicode/whitespace restoration | Passed |
| JSON/image/collection backup round trip, invalid-input rejection, HTML/CSV safety | Passed |
| Pause/private mode, credential rules, session-only switching, retention and backups | Passed |
| Main-window/worker wiring, popup, GUI-thread job completion, editing-safe Delete key | Passed |
| QR PNG/SVG generation and independent ZXing decoding | Exact URL/code/Wi-Fi/Bangla/emoji/whitespace payloads passed |
| QR splitting, oversize, color/contrast and scan-size rejection | Passed |
| Real Tesseract 5.5 isolated workspace and Ubuntu container engine | Generated screenshot sentence extracted exactly |
| Real X11 cross-process capture on isolated Xvfb | Text, Unicode, duplicates, URL, image, file URLs, HTML passed |
| Real X11 image restore and no restore feedback capture | Passed |
| Native Wayland startup / clean shutdown | Passed with temporary empty data; Qt text-input focus warnings observed |
| Compositor-wide GNOME/Wayland capture | **Not implemented**; persistent limitation notice is intentional |
| Ubuntu 24.04 standalone binary | Built; minimum glibc dependency measured as 2.38 |
| Actual `.deb` install and remove in Ubuntu 24.04 | Passed; `/usr/bin/clipo --version` and frozen startup/shutdown passed; user-data marker preserved |
| AppImage | Built from Ubuntu 24.04 frozen bundle; final artifact smoke checks recorded below |
| GitHub workflow | Added; not pushed or remotely run |
| Physical desktop tray/login, phone scan, printer, upgrades, daily-use trial | Manual acceptance pending |

## Performance

`scripts/benchmark.py` creates 50,000 synthetic records with developer notes and
URLs. `docs/benchmark.json` stores the measured five-sample medians: recent page
about 0.7 ms, deep page about 2 ms, specific substring about 1 ms, broad common-word
search about 119 ms. These measurements describe this machine and corpus, not
all real-world payloads. One/two-character queries still use a scan.

## Isolation

Automated clipboard tests use process-local Qt clipboards, controlled MIME test
doubles, or an independent Xvfb display. They do not read/overwrite the user's
desktop clipboard. The native Wayland startup test did not read initial clipboard
contents. Screenshots use synthetic data in temporary history. Tesseract and Xvfb
packages used for additional workspace checks were extracted under `/tmp`; they
were not installed on the host. Container package installation/removal did not
modify the host application installation.

## Reproduction

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/preview.py
xvfb-run -a env -u WAYLAND_DISPLAY QT_QPA_PLATFORM=xcb XDG_SESSION_TYPE=x11 CLIPO_ISOLATED_DISPLAY=1 .venv/bin/python scripts/probe_x11.py
docker build -f packaging/Dockerfile.ubuntu24 -t clipo-build:ubuntu24 .
```

See `docs/PACKAGING.md` for artifacts, glibc compatibility, and build-tool pins.

## Final artifact checks

The final Ubuntu 24.04-based Debian artifact was installed again in a disposable
container after the metadata/launcher update. The desktop entry exists, version
reports 0.2.0, frozen startup/shutdown passes, removal succeeds, and the user-data
marker remains. The final AppImage reports 0.2.0 through its extract-and-run
fallback, extracts successfully, and its AppRun passes startup, storage,
SIGTERM shutdown, and lock cleanup checks. Manifest hashes were recomputed and
matched both exact files. Normal FUSE mounting on a physical desktop remains a
manual check. AppStream metadata passes `appstreamcli validate --no-net`.
