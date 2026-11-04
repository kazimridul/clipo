# Clipo 0.3 validation

Date: 4 November 2026. Tests and integration probes use synthetic data.

| Check | Evidence |
| --- | --- |
| Automated suite, all optional local engines/sockets present | 72 tests; final Ubuntu build result and artifact checks are recorded in RELEASE_MANIFEST.json/build logs |
| Phase 1 schema migration, exact Unicode/whitespace restore, search/index maintenance | Passed |
| Image hashing, private permissions, organization/flags, deletion/undo, bounded pages | Passed |
| JSON/image/collection backup round trips, invalid input, escaped HTML/CSV | Passed |
| QR PNG/SVG, independent ZXing payload decoding, splitting/limits/contrast | Passed |
| Real Tesseract screenshot extraction | Passed |
| Python/SQL/JSON formatting | Passed; comments retained and code never executed |
| SQLCipher migration, metadata/image/search preservation, plaintext SQLite rejection | Passed |
| Wrong password, modified blob/backup, missing vault metadata | Rejected explicitly |
| GUI lock/unlock and stale preview suppression | Passed |
| Encrypted backup round trip, no plaintext intermediate backup file | Passed |
| Real X11/Xvfb cross-process clipboard | Text/Unicode, dedupe, URLs, image, file URLs, HTML, image restore and no feedback capture passed |
| Real headless GNOME 49 Wayland bridge | Background text/Unicode, dedupe, URL, PNG, file URLs, private/resume passed |
| GNOME extension lifecycle | Loaded ACTIVE in isolated GNOME; temporary settings only |
| GlobalShortcuts portal wire protocol | Registration, session/binding, activation, denial, request/session cleanup passed on private fake portal |
| One-time TLS LAN transfer on loopback | Certificate verified; GET reveals no payload; one POST receives it; replay denied; HTML escaped; public/wildcard binding rejected |
| Installed bundled engines | `clipo --self-test` checks QR, Python/SQL formatter, encrypted DB/FTS, encrypted image and authenticated backup |
| Small-window rendering | 850×570 inspected with scroll access; light/dark, QR, popup and settings screenshots inspected |
| Physical phone certificate UX/scans, printer, normal FUSE mount, real login/tray, accessibility/endurance | Manual acceptance still required |

## Reproduce

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/clipo --self-test
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/preview.py
xvfb-run -a env -u WAYLAND_DISPLAY QT_QPA_PLATFORM=xcb XDG_SESSION_TYPE=x11 CLIPO_ISOLATED_DISPLAY=1 .venv/bin/python scripts/probe_x11.py
.venv/bin/python scripts/run_wayland_probe.py
docker build -f packaging/Dockerfile.ubuntu24 -t clipo-build:ubuntu24 .
```

The full suite requires Tesseract, a D-Bus daemon and local Unix/loopback sockets;
missing/restricted optional integration requirements skip with explicit reasons.
The GNOME probe uses its own D-Bus session, headless compositor, temporary XDG
settings, and a test-only producer extension which is never distributed.
Portal tests never open the host's permission dialog. TLS tests bind loopback,
never an external interface. The user's desktop clipboard is not used.

The recorded 50k-row benchmark is in benchmark.json (about 0.7 ms recent page,
2 ms deep page, 1 ms specific search, 119 ms broad search on this corpus/machine).
This is not a universal workload guarantee or an independent security audit.

A focused GUI shutdown probe exposed an interpreter-finalization fault when a
Python-constructed QMimeData remained owned by Qt's global clipboard. Native Qt
MIME allocation and the native plain-text path avoid that lifetime trampoline.
A subprocess regression verifies rich-text/file restoration and clean exit;
three repeated focused GUI runs and the full suite pass. The native X11 producer
is also required to exit with status 0.

The encrypted 50k-row benchmark is in benchmark-encrypted.json: about 2.4 ms recent
page, 4.5 ms deep page, 7 ms specific search, and 1.19 s for a query matching all
records. It includes encryption/security overhead and runs off the GUI thread.

Migration safeguards also prevent stale queued settings from disabling a new
vault, and source removal requires successfully reopening the migrated store.
Backup import retention/sorting uses original timestamps so older imported data
cannot displace newer live history merely because it was inserted later.

Final release evidence: Ubuntu 24.04 source suite passes 72 tests with engines and
local sockets enabled; the installed frozen diagnostics report all engines passed.
The actual 0.2 → 0.3 Debian upgrade preserves Unicode text, pins, tags and
collections, starts cleanly, and preserves data on removal. Final AppImage hashes,
engine diagnostics and extracted AppRun startup/shutdown are checked against the
same Ubuntu-built bundle. Manifest hashes identify the exact downloadable files.
