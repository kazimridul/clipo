# Architecture

Clipo keeps the UI, clipboard adapter, business rules, and persistence separate.

```text
Qt GUI thread                          Dedicated storage QThread
─────────────                          ─────────────────────────
QClipboard → ClipboardMonitor ────────→ HistoryWorker
                  ↑                     ├─ HistoryService (validation)
              Controller                └─ HistoryRepository (SQLite)
                  ↕                           │
              MainWindow ←── queued signals ──┘
```

## Module boundaries

| Module | Responsibility |
| --- | --- |
| `application` | Startup, instance lock, local activation socket, dependency composition, shutdown |
| `clipboard` | GUI-thread MIME reads, restore, pause/private gates, desktop capability reporting |
| `config` | Validated settings, atomic writes, XDG directories |
| `core` | Capture rules and worker request routing |
| `models` | Immutable clipboard item, query, and page records |
| `storage` | SQLite migration version, transactions, retention, bounded queries |
| `system` | Tray integration and window activation |
| `ui` | Main window, settings dialog, theme |
| `resources` | Application icon |
| `services`, `security` | Reserved extension modules for later phases |

Clipboard MIME objects are read synchronously during the Qt event, then an owned
Python string crosses a queued signal to the worker. SQLite connections are
created, used, and closed on that worker's thread. The GUI never opens SQLite.
Shutdown disables capture, drains queued writes, closes SQLite, then joins the
worker. QLockFile prevents simultaneous application instances writing the same
history. A user-scoped QLocalServer activates the first instance on relaunch.

The worker serializes commands. Page generations discard stale search results;
preview responses are checked against the selected item's ID. Queries return a
bounded number of short previews; selecting/copying retrieves complete text.
The full text is copied exactly, even when the visible preview is limited.

## Storage version 1

`PRAGMA user_version=1` records the schema version. A newer unknown version is
rejected, never overwritten. The Phase 1 table contains `id`, `content_type`,
`content_text`, `content_hash`, `created_at`, and `updated_at`, plus a created-time
index. IDs are monotonic and timestamps use UTC ISO 8601. Today filtering converts
local midnight to UTC. Future migrations must add the specified image, source,
favorite, pin, OCR, category, tag, and QR tables without resetting existing data.

WAL provides transactional writes. Capture hashes exact UTF-8 text and compares
it with the newest record: A→A saves once; A→B→A saves three entries. Restoring an
entry is suppressed by the monitor and does not create a new history row.

## Deliberate Phase 1 limits

- Substring search uses a bounded result page but scans text. FTS5 and 50,000-row
  realistic performance benchmarks are later work; no performance claim yet.
- QClipboard is the initial X11 adapter. Capability reporting treats Wayland and
  XWayland conservatively; an actual Wayland background adapter remains required.
- Source-application identification, exclusions by app, image capture, automatic
  cleanup by age, encryption, backups, OCR, QR, global shortcuts, and quick popup
  are not part of this phase.
- Only plain text is persisted. Native MIME payload replay is future work.
- Paused/private state is persistent. Turning either off never reads the current
  clipboard retroactively. Clipboard ownership and password manager hints reduce
  unintended captures, but cannot detect arbitrary secrets.
