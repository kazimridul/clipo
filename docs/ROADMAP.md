# Roadmap and acceptance status

The original roadmap remains the target. Implemented features and test evidence
are distinguished from complete product acceptance; unverified requirements are
not marked complete.

| Phase | Implemented | Remaining acceptance / scope |
| --- | --- | --- |
| 1 — Foundation | Modular Qt app, SQLite, text capture/restore, lifecycle and persistence | Real cross-process X11 passes; GNOME/Wayland background adapter still required |
| 2 — Core history | Images/thumbnails, rich text/file references, search, favorites, pins, editing, multi-delete/undo, tags, colored/pinned collections | Broader file-manager/desktop interoperability and long-running reliability checks |
| 3 — Desktop UX | Three-panel UI, themes, quick popup, tray, native X11 quick hotkey, configurable in-app bindings, desktop activation and autostart | Automatic Wayland portal shortcut integration; GNOME/KDE tray, scaling, accessibility acceptance |
| 4 — Advanced tools | Offline QR with PNG/SVG/copy/print/split/history, local OCR workers/languages, snippets/descriptions/highlighting, recognition, JSON tools | Physical-phone scanning, printer testing, more content detectors/optional code and SQL formatters |
| 5 — Privacy/performance | Pattern/app exclusions with explicit limits, private/pause/session-only mode, age/count cleanup, FTS5, worker isolation, portable/manual/scheduled backups, 50k-record benchmark | Optional encrypted database/images; verified clipboard-owner attribution; broad stress/resource testing |
| 6 — Distribution | Standalone bundle, Debian installer, portable AppImage, launcher/icon/metadata/licenses/checksums, Ubuntu 24.04 container and CI workflow | Physical-desktop AppImage/FUSE, login/tray and upgrade acceptance across supported Ubuntu releases; other architectures |
| 7 — Future sharing | Runtime is local-only; no sync service or network upload enabled | Android/device pairing, consent UI, local-network/remote sharing, encryption and expiry remain future modules |

## Release gate

Version 0.2.0 is a feature release candidate, not a claim of complete CopyQ parity
or completion of all seven phases. The largest remaining functional gap is full
GNOME/Wayland background capture. Optional storage encryption and cross-device
sharing are also unimplemented. The UI reports Wayland restrictions explicitly.

The Ubuntu 24.04 container verifies source tests, real X11 clipboard events,
packaging, actual Debian installation, frozen-app startup/shutdown, removal, and
preservation of a user-data marker. It does not replace a real GNOME desktop,
physical phone/printer, or a long-running daily-use trial.
