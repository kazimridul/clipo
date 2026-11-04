# Delivery roadmap

The original specification requests incremental implementation. No phase is
declared accepted until its applicable automated and real-desktop checks pass.

| Phase | Status | Acceptance work |
| --- | --- | --- |
| 1 — Foundation | Implemented; Ubuntu desktop acceptance pending | Modular Python/Qt app, SQLite, text capture, exact restore, tests; verify cross-app capture, tray lifecycle, relaunch, and limitations on real Ubuntu sessions |
| 2 — Clipboard core | Planned | Images, deduplication, favorites, pins, collections, tags, history editing, cleanup |
| 3 — Desktop experience | Partly started | Themes, main window, basic tray implemented; quick popup, global shortcuts, configurable key bindings, accessibility review still required |
| 4 — Advanced tools | Planned | QR payload integrity/decoding tests, QR history, OCR workers, smart recognition, snippets, JSON tools |
| 5 — Privacy and performance | Partly started | Private mode, limits, worker isolation implemented; secret patterns, app exclusions, FTS5, retention by age, optional encryption, 50k benchmarks still required |
| 6 — Distribution | Planned | Reproducible `.deb`, AppImage, clean Ubuntu install/upgrade/removal tests, autostart and metadata |
| 7 — Sharing | Future, disabled | Explicitly authorized sharing and optional encrypted sync |

## Immediate follow-up

1. Complete the Ubuntu checklist and establish the supported desktop matrix.
2. Implement robust Wayland integration with explicit capability probing. Evaluate
   compositor data-control protocols separately from GNOME's restricted access;
   don't treat QClipboard foreground behavior as success.
3. Add image storage by content hash with worker-generated thumbnails and
   asynchronous full-size previews, then the rest of Phase 2.
4. Keep the original requirements as the product target; do not substitute UI
   placeholders for unfinished features.
