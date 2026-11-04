# Ubuntu acceptance checklist

Status: **not executed on a physical/virtual Ubuntu desktop in this workspace**.
Offscreen automation verifies core logic and Qt wiring, not compositor behavior.

Use only disposable test text and a separate data directory. Do not use real
credentials for these checks.

## Installation and launch

- [ ] Install on a clean Ubuntu 24.04 or later system using README steps.
- [ ] Run `clipo --data-dir /tmp/clipo-acceptance` from the virtual environment.
- [ ] Install the optional development launcher and open Clipo from the app menu.
- [ ] Launch a second instance with the same data directory: first window opens,
      no duplicate tray/process remains, no database corruption occurs.
- [ ] Test dark/light/system themes and a 100% / 200% scaled display.

## Ubuntu on Xorg

- [ ] Sign out and select **Ubuntu on Xorg** on the login screen if available.
- [ ] Copy text from Text Editor, Terminal, and Firefox while Clipo is unfocused.
- [ ] Each appears once, with correct timestamp and exact content.
- [ ] Test A→A and A→B→A; verify consecutive duplicate behavior.
- [ ] Copy multiline, Unicode/Bangla, tabs, and leading/trailing whitespace.
- [ ] Restore with Enter and the Copy button; paste into another app and compare.
- [ ] Verify restore does not create another history row.
- [ ] Search and Today filter work; copy more than 100 items and page both ways.
- [ ] Set history limit to 3 and verify only newest items remain; set 0 for unlimited.
- [ ] Restart Clipo and verify saved history and appearance persist.
- [ ] Where a tray is available, close the window, copy text, reopen from tray,
      and verify capture continued. Check Quit terminates the process.
- [ ] Without a tray host, closing the window exits cleanly.

## Privacy and errors

- [ ] Pause, copy disposable private text, resume: text never appears in history.
- [ ] Repeat with private mode; restart and verify private mode stays enabled.
- [ ] Turn private mode off without copying anything new: previous private text
      does not suddenly appear.
- [ ] Copy a test password from KeePassXC; verify its history-exclusion MIME hint
      is honored where provided. Do not assume arbitrary secrets are recognized.
- [ ] Copy >1 MiB text: warning appears and no truncated record is stored.
- [ ] Delete an item, cancel clearing, then confirm clearing; current clipboard
      remains intact while saved records disappear.
- [ ] Check directory/file permissions; no text contents appear in console logs.
- [ ] Test an unwritable data directory and malformed settings: startup fails
      clearly without replacing the existing database.

## Ubuntu Wayland

- [ ] Launch in the normal Ubuntu Wayland session; persistent limitation notice
      appears, with no claim of full background monitoring.
- [ ] Record which cross-app clipboard events arrive while focused/unfocused.
- [ ] Repeat using XWayland Qt (`QT_QPA_PLATFORM=xcb`); limitation stays visible.
- [ ] Verify text restoration and paste work for receiving native Wayland and
      XWayland apps; document any failures by desktop/Qt version.
- [ ] Do not mark Wayland background support accepted until a compositor-aware
      backend has been implemented and these checks pass.

## Evidence to record

Record Ubuntu version, desktop/compositor, session type, Python/Qt versions,
tray host/extension, each result, and reproduction steps for failures.
QR/OCR/images/global shortcuts/`.deb` acceptance is deferred to its feature phase.
