# Delivery and acceptance status

Version 0.3.0 closes the major software gaps identified in 0.2.0. Delivered code
and automated integration evidence are distinguished from physical/manual acceptance.
The original full requirements remain in PRODUCT_REQUIREMENTS.md.

| Phase | Delivered | Integration coverage / later scope |
| --- | --- | --- |
| 1 — Foundation | Modular Qt lifecycle, SQLite, exact capture/restore, migrations | X11 and GNOME Wayland background probes pass |
| 2 — Core history | Text/HTML/images/files, thumbnails, favorites/pins, editing, undo, tags, colored/pinned collections | Broader file-manager interoperability and endurance checks remain manual |
| 3 — Desktop UX | Three panels, small-screen scrolling, themes, quick popup, tray, configurable keys, X11 hotkey, opt-in Wayland portal, startup | Portal protocol tested with private D-Bus; actual desktop permission dialogs, tray/login/scaling need manual acceptance |
| 4 — Advanced tools | QR copy/export/print/split/history, OCR/languages, snippets/highlighting, Python/SQL/JSON formatting, content hints | Real OCR and QR decoding pass; physical phone scans/printers still need manual checks |
| 5 — Privacy/performance | SQLCipher vault, authenticated encrypted blobs/backups, lock/unlock, verified migration, privacy/exclusions, FTS5, 50k benchmark | Wrong-password/tamper/metadata-loss/stale-callback checks pass; app attribution remains a documented active-window hint; not an independent security audit |
| 6 — Distribution | Ubuntu 24.04 standalone/deb/AppImage, metadata/licenses/checksums, packaged-engine diagnostics, CI | Container tests validate installation/startup/removal/data preservation; physical FUSE/login/tray and other architectures remain acceptance work |
| 7 — Optional sharing | Explicit, expiring, one-use TLS LAN text/image transfer with phone QR, consent and revocation | Loopback TLS tests pass. Persistent pairing, native Android app, cloud sharing and automatic multi-device synchronization remain future extensions |

## Compatibility scope

GNOME's optional extension is required for full background capture on GNOME Wayland;
it must be enabled by the user. The real compositor probe runs GNOME 49; other
declared GNOME versions (45–50) need acceptance. Unsupported Wayland compositors
retain explicit limitation reporting. There is no claim of universal compositor
support, complete CopyQ parity, or that hardware/manual checks have been executed.

No percentage is used as a release gate. Automated tests, real X11/GNOME probes,
installed-binary diagnostics and package checks are the evidence. Daily-use trials,
physical phone/printer checks and broader desktop/accessibility acceptance remain
necessary before calling the application production-certified.
