# Validation record

Date: 4 November 2026.

Environment: Python 3.13.7, PySide6/Qt 6.12.0, pytest 9.2.0, Linux development
workspace. This is not an Ubuntu release certification.

| Check | Result |
| --- | --- |
| Automated suite with local Unix sockets permitted | 26 passed |
| Text persistence, exact Unicode/whitespace restore, duplicates, limits | Passed |
| Search, pagination, local Today boundary, delete/clear | Passed |
| Pause, private-mode persistence, password-manager MIME hints | Passed |
| GUI-thread clipboard → worker storage → UI → restore | Passed with controlled external-event double and real process-local Qt clipboard |
| Two real offscreen app processes, single-instance activation | Passed |
| SIGTERM shutdown, worker/lock cleanup | Passed |
| Development desktop-launcher install/remove in temporary XDG directory | Passed |
| Light/dark screenshots | Rendered and visually inspected; selected-text contrast and horizontal overflow corrected |
| Native Wayland startup, database creation, clean shutdown | Passed with empty temporary history; Qt emitted text-input focus warnings |
| Cross-application native Wayland background clipboard | Not verified; explicitly reported as limited |
| Cross-application X11 on Ubuntu | Manual acceptance pending |
| `.deb` / AppImage installation | Not implemented (Phase 6) |

The initial restricted-sandbox launch check correctly exposed a denied local
Unix socket. The process test passed when run with sockets permitted. In
environments that forbid Unix sockets, that test skips with an explicit reason.
Native display startup also required desktop socket access outside the sandbox.

Regenerate the synthetic-data UI screenshots with:

```bash
.venv/bin/python scripts/preview.py
```

No screenshots or tests capture the user's clipboard history.
