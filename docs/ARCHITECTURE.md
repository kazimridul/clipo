# Architecture

Clipo separates presentation, OS clipboard access, domain services, and storage.

```text
GUI thread                             Storage QThread
QClipboard → ClipboardMonitor ───────→ HistoryWorker → HistoryService
                  ↑                         └────────→ HistoryRepository
              Controller ←── queued signals ─────────────────┘
                ↕     ↕
        MainWindow   QuickPopup        Background job pool (2 workers)
                └────────────────────→ QR encoding / OCR subprocess / file saves
```

## Boundaries

| Module | Responsibility |
| --- | --- |
| application | Composition, lifecycle, instance lock, local activation, coordination |
| clipboard | GUI-thread MIME reads, exact restoration, privacy gate, capability report |
| config | Validated settings, atomic private writes, XDG paths |
| core | Capture rules and serialized worker commands |
| models | Immutable item/query/page records |
| storage | SQLite migrations, transactions, retention, FTS5, metadata, pagination |
| services | Content-addressed images, QR, OCR, content recognition, import/export, job pool |
| security | Sensitive-pattern and literal/glob exclusion policies |
| system | Tray, X11 hotkey registration, active-window hint, user autostart |
| ui | Main/quick windows, editors, settings, QR/OCR/image dialogs, highlighting |

MIME data is read during its Qt event; an owned string or detached QImage crosses
a queued signal. Encoding, hashing, thumbnails, persistence, import/export, and
search run on the storage worker. QR/OCR jobs run in a separate pool so OCR does
not stop database access. Completion slots dispatch results on the GUI thread.

Search generations reject stale main-window/popup responses; selection IDs guard
preview responses. Page queries return bounded previews, never full HTML/image
blobs. Full items are retrieved only for selection, restoration, editing, or export.

QLockFile prevents simultaneous writers to a history. A user-scoped QLocalServer
handles show/quick activation. SIGTERM/Ctrl+C disable capture, finish background
jobs and queued writes, close SQLite on its owning thread, and release the lock.

## Schema and search

Schema version **4**, recorded through `PRAGMA user_version`, upgrades existing
Phase 1 databases in an explicit transaction. Unknown newer versions are rejected.

- `clipboard_items`: text/HTML, type/hash, UTC timestamps, image reference, file
  metadata, flags, OCR text, snippet title/description/language, usage count,
  cached search tags.
- `categories`, `tags`, `item_categories`, `item_tags`: many-to-many organization;
  categories have colors and pins.
- `qr_history`: references to generated QR files and source items.
- `item_search`: external-content SQLite FTS5 trigram index, synchronized by
  insert/update/delete triggers. Text, title, description, tags, and OCR are indexed.

Searches of three or more characters use quoted literal FTS phrases; one/two
character searches fall back to substring scans. Pins/newest and usage have order
indexes. Today/custom dates are converted from local time to UTC. Export iterates
bounded pages; JSON import validates the entire bounded input before a transaction.
Images are inline in portable backups; supplied filesystem paths are not trusted.
HTML exports escape content and CSV exports protect against formula interpretation.

## Retention and image ownership

Text deduplication compares the newest capture's exact text hash. Image hashing
uses normalized RGBA pixels and dimensions, with external PNGs and small thumbnails.
Count/age retention excludes pinned records. Twenty individual deletions are held
for in-process undo, including organization; their images remain referenced until
undo expires. Managed orphan images are collected periodically. Clearing history
also clears generated QR history/files; independent manual exports remain external.

Session-only mode uses SQLite in memory and a private temporary image directory.
Switching modes reopens the appropriate repository; old disk data is preserved.
No encryption or network synchronization is claimed. GNOME/Wayland data-control
integration remains a separate release requirement, not a QClipboard assumption.
