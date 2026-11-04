# Ubuntu desktop acceptance checklist

Automated source, native X11/Xvfb, and Debian install/remove checks pass in a clean
Ubuntu 24.04 container. The following physical/full-desktop checks remain. Use
synthetic test content and `clipo --data-dir /tmp/clipo-acceptance`.

## Desktop and clipboard

- [ ] On Ubuntu on Xorg, copy from Firefox, Text Editor, Terminal, and LibreOffice
      while Clipo is hidden/unfocused. Verify exact text/HTML restoration.
- [ ] Copy files in Nautilus, restore references, and paste into another directory.
      Confirm the action copies, does not cut, and missing files are handled by
      the receiving file manager.
- [ ] Copy real screenshots, verify thumbnails, zoom, save, and restore pixels.
- [ ] Close/reopen from tray; test a desktop without a tray host as well.
- [ ] Run a second instance and `clipo --quick`; verify popup activation and
      keyboard search, arrows, Enter, and Escape.
- [ ] Test the X11 global key, a conflicting binding, and changed in-app bindings.
- [ ] Check scaling at 100%/200%, minimum window sizes, keyboard focus, and a
      screen reader. Check light/dark/system appearance transitions.
- [ ] Enable login startup, sign out/in, then disable it and verify reversal.

## Organization, privacy, data

- [ ] Use favorites, pins, multiple collections/tags, colors, collection pins,
      rename/delete, text edits, and multi-delete/undo.
- [ ] Exercise all date filters, sorts, snippet description/language editing,
      syntax coloring, JSON formatting, and large-preview/full-copy behavior.
- [ ] Verify pause/private state survives restart and resuming does not ingest
      private clipboard text; test KeePassXC's exclusion MIME hint.
- [ ] Test app exclusions on X11. Confirm fail-closed behavior when app identity
      is unavailable; do not treat active-window hints as owner guarantees.
- [ ] Switch persistence modes, restart, and check prior disk history is preserved
      while temporary session history disappears.
- [ ] Confirm unpinned expiration/count cleanup, pin protection, and orphan cleanup.
- [ ] Export/import real mixed selections/collections, reject malformed imports,
      and verify manual/scheduled backups and seven-backup retention.
- [ ] Test full disk, read-only config/data paths, and abrupt process termination.

## QR, OCR, and installation

- [ ] Scan generated plain/URL/Wi-Fi/Unicode QR codes with physical phone cameras,
      including multipart sequences. Confirm no content is truncated or uploaded.
- [ ] Test SVG/PNG exports, copy image/original text, configured colors, and print.
- [ ] Install English/Bangla OCR data and check eng, ben, and eng+ben on real
      screenshots; test missing engine/data, failures, and automatic OCR privacy.
- [ ] Install/remove/reinstall the `.deb` on a real Ubuntu desktop and verify
      launcher, tray, user history, and optional OCR dependencies.
- [ ] Run AppImage with and without FUSE; test autostart using its persistent
      original path. Validate upgrades with a copy of prior-release data.

## Wayland

- [ ] Verify the limitation banner remains visible for native Wayland and
      XWayland. Record foreground/unfocused event behavior without treating it
      as compositor-wide background access.
- [ ] Assign `clipo --quick` in desktop keyboard settings and test activation.
- [ ] Verify text/image/file restoration into native Wayland and XWayland apps.
- [ ] Enable the Clipo GNOME Clipboard Bridge, confirm its connected status, and
      repeat background cross-app checks on this GNOME version. The automated
      headless GNOME 49 probe already passes; unsupported compositors remain limited.

Record Ubuntu/desktop/compositor versions, Qt/Python versions, session type, tray
host, test results, and reproduction steps for failures. Unencrypted storage,
unimplemented network sharing, and other release gates are listed in ROADMAP.md.

## New 0.3 desktop checks

- [ ] Enable the GNOME bridge, copy while Clipo is hidden, pause/private/lock,
      disable the bridge, and confirm the heartbeat limitation fallback.
- [ ] Approve/deny the shortcut portal's actual desktop permission UI and verify
      hotkey conflict/rebinding, session cleanup, and the manual fallback.
- [ ] Migrate a disposable history into a vault, restart/unlock, copy and OCR images,
      lock while dialogs/jobs are open, and restore an authenticated backup.
- [ ] Create an expiring local link on Wi-Fi, compare the phone's certificate
      fingerprint, receive text/image once, test expiry/revoke/private mode, and
      verify firewall-denied behavior. No server should exist before Create.
- [ ] Run a prolonged mixed-content capture trial and review CPU/memory/disk use.
