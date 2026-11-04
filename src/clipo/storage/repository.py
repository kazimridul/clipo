"""SQLite repository; each instance is confined to its creating thread."""
import hashlib
import os
import sqlite3
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from clipo.config.settings import private_directory
from clipo.models.item import ClipboardItem, HistoryPage, HistoryQuery


class HistoryRepository:
    def __init__(self, path: Path, memory=False, password=None):
        private_directory(path.parent)
        # Create privately before SQLite opens the file (including on first run).
        if not memory:
            fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(fd)
            path.chmod(0o600)
        self.temporary = tempfile.TemporaryDirectory(prefix="clipo-session-") if memory else None
        self.vault = None
        if password and not memory:
            from clipo.security.vault import open_database, BlobVault
            fresh = path.stat().st_size == 0
            self.connection, row_factory = open_database(path, password)
            try:
                self.vault = BlobVault(path.parent, password, create=fresh)
            except Exception:
                self.connection.close()
                raise
        else:
            self.connection = sqlite3.connect(":memory:" if memory else path, timeout=5)
            row_factory = sqlite3.Row
        self.connection.row_factory = row_factory
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 4:
            self.connection.close()
            raise ValueError("This history was created by a newer Clipo version")
        self.connection.execute("BEGIN IMMEDIATE")
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
            if version < 2:
                for name, declaration in {
                    "image_path": "TEXT NOT NULL DEFAULT ''", "is_favorite": "INTEGER NOT NULL DEFAULT 0",
                    "is_pinned": "INTEGER NOT NULL DEFAULT 0", "title": "TEXT NOT NULL DEFAULT ''",
                    "language": "TEXT NOT NULL DEFAULT ''", "ocr_text": "TEXT NOT NULL DEFAULT ''",
                    "content_html": "TEXT NOT NULL DEFAULT ''", "file_metadata": "TEXT NOT NULL DEFAULT ''",
                    "use_count": "INTEGER NOT NULL DEFAULT 0",
                }.items():
                    self.connection.execute(f"ALTER TABLE clipboard_items ADD COLUMN {name} {declaration}")
                migration = '''
                    CREATE TABLE categories(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, color TEXT NOT NULL DEFAULT '#6754d9');
                    CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
                    CREATE TABLE item_categories(item_id INTEGER REFERENCES clipboard_items(id) ON DELETE CASCADE, category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE, PRIMARY KEY(item_id,category_id));
                    CREATE TABLE item_tags(item_id INTEGER REFERENCES clipboard_items(id) ON DELETE CASCADE, tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY(item_id,tag_id));
                    CREATE INDEX items_flags ON clipboard_items(is_pinned,is_favorite);
                    CREATE TABLE qr_history(id INTEGER PRIMARY KEY, clipboard_item_id INTEGER REFERENCES clipboard_items(id) ON DELETE SET NULL, qr_image_path TEXT NOT NULL, created_at TEXT NOT NULL);
                '''
                for statement in migration.split(';'):
                    if statement.strip():
                        self.connection.execute(statement)
            if version < 3:
                self.connection.execute("ALTER TABLE clipboard_items ADD COLUMN search_tags TEXT NOT NULL DEFAULT ''")
                self.connection.execute("UPDATE clipboard_items SET search_tags=coalesce((SELECT group_concat(name,' ') FROM tags JOIN item_tags ON tags.id=tag_id WHERE item_id=clipboard_items.id),'')")
                self.connection.execute("CREATE VIRTUAL TABLE item_search USING fts5(content_text,title,ocr_text,search_tags,content='clipboard_items',content_rowid='id',tokenize='trigram')")
                self.connection.execute("INSERT INTO item_search(item_search) VALUES('rebuild')")
                self.connection.execute("""CREATE TRIGGER items_search_insert AFTER INSERT ON clipboard_items BEGIN
                    INSERT INTO item_search(rowid,content_text,title,ocr_text,search_tags) VALUES(new.id,new.content_text,new.title,new.ocr_text,new.search_tags); END""")
                self.connection.execute("""CREATE TRIGGER items_search_delete AFTER DELETE ON clipboard_items BEGIN
                    INSERT INTO item_search(item_search,rowid,content_text,title,ocr_text,search_tags) VALUES('delete',old.id,old.content_text,old.title,old.ocr_text,old.search_tags); END""")
                self.connection.execute("""CREATE TRIGGER items_search_update AFTER UPDATE OF content_text,title,ocr_text,search_tags ON clipboard_items BEGIN
                    INSERT INTO item_search(item_search,rowid,content_text,title,ocr_text,search_tags) VALUES('delete',old.id,old.content_text,old.title,old.ocr_text,old.search_tags);
                    INSERT INTO item_search(rowid,content_text,title,ocr_text,search_tags) VALUES(new.id,new.content_text,new.title,new.ocr_text,new.search_tags); END""")
            if version < 4:
                self.connection.execute("ALTER TABLE clipboard_items ADD COLUMN description TEXT NOT NULL DEFAULT ''")
                self.connection.execute("ALTER TABLE categories ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")
                for trigger in ("items_search_insert", "items_search_delete", "items_search_update"):
                    self.connection.execute(f"DROP TRIGGER {trigger}")
                self.connection.execute("DROP TABLE item_search")
                self.connection.execute("CREATE VIRTUAL TABLE item_search USING fts5(content_text,title,ocr_text,search_tags,description,content='clipboard_items',content_rowid='id',tokenize='trigram')")
                self.connection.execute("INSERT INTO item_search(item_search) VALUES('rebuild')")
                fields = "content_text,title,ocr_text,search_tags,description"
                new_values = ",".join("new." + name for name in fields.split(","))
                old_values = ",".join("old." + name for name in fields.split(","))
                self.connection.execute(f"CREATE TRIGGER items_search_insert AFTER INSERT ON clipboard_items BEGIN INSERT INTO item_search(rowid,{fields}) VALUES(new.id,{new_values}); END")
                self.connection.execute(f"CREATE TRIGGER items_search_delete AFTER DELETE ON clipboard_items BEGIN INSERT INTO item_search(item_search,rowid,{fields}) VALUES('delete',old.id,{old_values}); END")
                self.connection.execute(f"CREATE TRIGGER items_search_update AFTER UPDATE OF {fields} ON clipboard_items BEGIN INSERT INTO item_search(item_search,rowid,{fields}) VALUES('delete',old.id,{old_values}); INSERT INTO item_search(rowid,{fields}) VALUES(new.id,{new_values}); END")
            self.connection.execute("PRAGMA user_version=4")
            self.connection.execute("CREATE INDEX IF NOT EXISTS items_pin_order ON clipboard_items(is_pinned DESC,id DESC)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS items_usage ON clipboard_items(use_count DESC,id DESC)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS items_pin_time ON clipboard_items(is_pinned DESC,created_at DESC,id DESC)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS items_usage_time ON clipboard_items(use_count DESC,created_at DESC,id DESC)")
        self.images = private_directory((Path(self.temporary.name) if self.temporary else path.parent) / "images")
        self._undo = []

    @staticmethod
    def _columns(preview=False):
        text = "substr(content_text,1,240) AS content_text" if preview else "content_text"
        large = "substr(ocr_text,1,240) AS ocr_text,'' AS content_html,'' AS file_metadata" if preview else "ocr_text,content_html,file_metadata"
        return ("id," + text + ",content_hash,created_at,content_type,image_path,is_favorite,is_pinned,title,language,"
                + large + (",use_count,substr(description,1,240) AS description," if preview else ",use_count,description,")
                + "coalesce((SELECT group_concat(name,', ') FROM tags JOIN item_tags ON tags.id=tag_id WHERE item_id=clipboard_items.id),'') AS tags,"
                "coalesce((SELECT group_concat(name,', ') FROM categories JOIN item_categories ON categories.id=category_id WHERE item_id=clipboard_items.id),'') AS collections")

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
                "DELETE FROM clipboard_items WHERE id IN (SELECT id FROM clipboard_items WHERE is_pinned=0 ORDER BY created_at DESC,id DESC LIMIT -1 OFFSET ?)",
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
            if len(query.text) >= 3 and "\x00" not in query.text:
                clauses.append("id IN (SELECT rowid FROM item_search WHERE item_search MATCH ?)")
                arguments.append('"' + query.text.replace('"', '""') + '"')
            else:
                clauses.append("(instr(lower(content_text),lower(?))>0 OR instr(lower(ocr_text),lower(?))>0 OR instr(lower(title),lower(?))>0 OR instr(lower(search_tags),lower(?))>0 OR instr(lower(description),lower(?))>0)")
                arguments.extend([query.text] * 5)
        if query.today:
            start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
            clauses.append("created_at >= ?")
            arguments.append(start.astimezone(timezone.utc).isoformat(timespec="microseconds"))
        if query.view in ("favorites", "pinned"):
            clauses.append("is_favorite=1" if query.view == "favorites" else "is_pinned=1")
        elif query.view in ("text", "image", "url", "files", "snippet"):
            clauses.append("content_type=?")
            arguments.append(query.view)
        elif query.view == "qr":
            clauses.append("id IN (SELECT clipboard_item_id FROM qr_history)")
        if query.collection:
            clauses.append("id IN (SELECT item_id FROM item_categories JOIN categories ON category_id=categories.id WHERE name=?)")
            arguments.append(query.collection)
        for value, operator in ((query.since, ">="), (query.until, "<")):
            if value:
                clauses.append(f"created_at {operator} ?")
                arguments.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        total = self.connection.execute("SELECT count(*) FROM clipboard_items" + where, arguments).fetchone()[0]
        # List previews stay small even if an item contains a megabyte of text.
        rows = self.connection.execute(
            "SELECT " + self._columns(True) + " FROM clipboard_items" + where +
            {"oldest": " ORDER BY created_at ASC,id ASC", "frequent": " ORDER BY use_count DESC,created_at DESC,id DESC"}.get(query.sort, " ORDER BY is_pinned DESC,created_at DESC,id DESC") + " LIMIT ? OFFSET ?",
            [*arguments, query.limit, query.offset],
        ).fetchall()
        return HistoryPage(query, tuple(ClipboardItem(**dict(row)) for row in rows), total)

    def get(self, item_id: int) -> ClipboardItem | None:
        row = self.connection.execute("SELECT " + self._columns() + " FROM clipboard_items WHERE id=?", (item_id,)).fetchone()
        return ClipboardItem(**dict(row)) if row else None

    def delete(self, item_id: int) -> None:
        row = self.connection.execute("SELECT * FROM clipboard_items WHERE id=?", (item_id,)).fetchone()
        if row:
            self._undo.append((dict(row), self.get(item_id)))
            self._undo = self._undo[-20:]
        with self.connection:
            self.connection.execute("DELETE FROM clipboard_items WHERE id=?", (item_id,))

    def undo(self):
        if not self._undo:
            return
        row, item = self._undo.pop()
        with self.connection:
            self.connection.execute("INSERT INTO clipboard_items(" + ",".join(row) + ") VALUES(" + ",".join("?" for _ in row) + ")", list(row.values()))
            self.organize(item.id, item.tags, item.collections)

    def flag(self, item_id, field):
        if field not in ("is_favorite", "is_pinned"):
            raise ValueError("Invalid item flag")
        with self.connection:
            self.connection.execute(f"UPDATE clipboard_items SET {field}=NOT {field} WHERE id=?", (item_id,))

    def edit(self, item_id, text, title="", language="", description=""):
        if len(title) > 300 or len(language) > 100 or len(description) > 4000:
            raise ValueError("Title, language, or description is too long")
        with self.connection:
            self.connection.execute("UPDATE clipboard_items SET content_text=?,title=?,language=?,description=?,content_hash=?,updated_at=? WHERE id=? AND content_type!='image'",
                (text, title, language, description, hashlib.sha256(text.encode()).hexdigest(), datetime.now(timezone.utc).isoformat(), item_id))

    def organize(self, item_id, tags, collections):
        if len(tags) > 10000 or len(collections) > 10000:
            raise ValueError("Tags and collections must each be at most 10,000 characters")
        with self.connection:
            for values, table, relation, key in ((tags, "tags", "item_tags", "tag_id"), (collections, "categories", "item_categories", "category_id")):
                self.connection.execute(f"DELETE FROM {relation} WHERE item_id=?", (item_id,))
                for name in dict.fromkeys(v.strip() for v in values.split(",") if v.strip()):
                    if len(name) > 100:
                        raise ValueError("Names must be at most 100 characters")
                    self.connection.execute(f"INSERT OR IGNORE INTO {table}(name) VALUES(?)", (name,))
                    self.connection.execute(f"INSERT INTO {relation}(item_id,{key}) SELECT ?,id FROM {table} WHERE name=?", (item_id, name))
            self.connection.execute("UPDATE clipboard_items SET search_tags=? WHERE id=?", (tags, item_id))

    def collections_list(self):
        return [dict(row) for row in self.connection.execute("SELECT name,color,is_pinned FROM categories ORDER BY is_pinned DESC,name")]

    def style_collection(self, name, color=None):
        import re
        with self.connection:
            if color is None:
                self.connection.execute("UPDATE categories SET is_pinned=NOT is_pinned WHERE name=?", (name,))
            elif re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                self.connection.execute("UPDATE categories SET color=? WHERE name=?", (color, name))
            else:
                raise ValueError("Invalid collection color")

    def manage_collection(self, old, new):
        with self.connection:
            if new:
                if not new.strip() or len(new) > 100 or any(character in new for character in ",\n\r"):
                    raise ValueError("Collection name must be 1–100 characters")
                if old:
                    self.connection.execute("UPDATE categories SET name=? WHERE name=?", (new.strip(), old))
                else:
                    self.connection.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (new.strip(),))
            else:
                self.connection.execute("DELETE FROM categories WHERE name=?", (old,))

    def add_payload(self, text, kind, limit, *, image_path="", content_html="", metadata="", digest=None):
        digest = digest or hashlib.sha256((kind + text + content_html + metadata).encode()).hexdigest()
        previous = self.connection.execute("SELECT content_hash FROM clipboard_items ORDER BY id DESC LIMIT 1").fetchone()
        if previous and previous[0] == digest:
            return False
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self.connection:
            self.connection.execute("INSERT INTO clipboard_items(content_text,content_type,image_path,content_html,file_metadata,content_hash,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (text, kind, image_path, content_html, metadata, digest, now, now))
            self.prune(limit)
        return True

    def collect_images(self):
        referenced = {row[0] for row in self.connection.execute("SELECT image_path FROM clipboard_items WHERE image_path!=''")}
        referenced.update(row[0]["image_path"] for row in self._undo if row[0]["image_path"])
        for path in self.images.glob("*.png"):
            if str(path) not in referenced:
                path.unlink(missing_ok=True)
                (self.images / "thumbnails" / path.name).unlink(missing_ok=True)

    def clear(self) -> None:
        self._undo.clear()
        with self.connection:
            self.connection.execute("DELETE FROM clipboard_items")
        self.collect_images()

    def close(self) -> None:
        self.connection.close()
        if self.temporary:
            self.temporary.cleanup()
        self.vault = None

    def read_blob(self, path):
        path = Path(path)
        return self.vault.read(path) if self.vault else path.read_bytes()

    def write_blob(self, path, data):
        from clipo.security.vault import private_write
        self.vault.write(Path(path), data) if self.vault else private_write(Path(path), data)

