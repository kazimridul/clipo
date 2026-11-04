"""SQLite repository; each instance is confined to its creating thread."""
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from clipo.config.settings import private_directory
from clipo.models.item import ClipboardItem, HistoryPage, HistoryQuery


class HistoryRepository:
    def __init__(self, path: Path):
        private_directory(path.parent)
        # Create privately before SQLite opens the file (including on first run).
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        path.chmod(0o600)
        self.connection = sqlite3.connect(path, timeout=5)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.connection.close()
            raise ValueError("This history was created by a newer Clipo version")
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS clipboard_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL DEFAULT 'text',
                content_text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            self.connection.execute("CREATE INDEX IF NOT EXISTS items_created ON clipboard_items(created_at DESC)")
            self.connection.execute("PRAGMA user_version=1")

    def add(self, text: str, history_limit: int) -> bool:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self.connection:
            previous = self.connection.execute(
                "SELECT content_hash FROM clipboard_items ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if previous and previous[0] == digest:
                return False
            self.connection.execute(
                "INSERT INTO clipboard_items(content_text, content_hash, created_at, updated_at) VALUES(?,?,?,?)",
                (text, digest, now, now),
            )
            self.prune(history_limit)
        return True

    def prune(self, limit: int) -> None:
        if limit > 0:
            self.connection.execute(
                "DELETE FROM clipboard_items WHERE id IN (SELECT id FROM clipboard_items ORDER BY id DESC LIMIT -1 OFFSET ?)",
                (limit,),
            )

    def set_limit(self, limit: int) -> None:
        with self.connection:
            self.prune(limit)

    def page(self, query: HistoryQuery) -> HistoryPage:
        if not 1 <= query.limit <= 200 or query.offset < 0:
            raise ValueError("Invalid pagination")
        clauses, arguments = [], []
        if query.text:
            # Literal substring search: '%' and '_' are text, not SQL wildcards.
            clauses.append("instr(lower(content_text), lower(?)) > 0")
            arguments.append(query.text)
        if query.today:
            start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
            clauses.append("created_at >= ?")
            arguments.append(start.astimezone(timezone.utc).isoformat(timespec="microseconds"))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        total = self.connection.execute("SELECT count(*) FROM clipboard_items" + where, arguments).fetchone()[0]
        # List previews stay small even if an item contains a megabyte of text.
        rows = self.connection.execute(
            "SELECT id, substr(content_text,1,240) AS content_text, content_hash, created_at, content_type "
            "FROM clipboard_items" + where + " ORDER BY id DESC LIMIT ? OFFSET ?",
            [*arguments, query.limit, query.offset],
        ).fetchall()
        return HistoryPage(query, tuple(ClipboardItem(**dict(row)) for row in rows), total)

    def get(self, item_id: int) -> ClipboardItem | None:
        row = self.connection.execute("SELECT id, content_text, content_hash, created_at, content_type FROM clipboard_items WHERE id=?", (item_id,)).fetchone()
        return ClipboardItem(**dict(row)) if row else None

    def delete(self, item_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM clipboard_items WHERE id=?", (item_id,))

    def clear(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM clipboard_items")

    def close(self) -> None:
        self.connection.close()

