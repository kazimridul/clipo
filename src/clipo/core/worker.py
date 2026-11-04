"""All SQLite work runs serially on a dedicated Qt thread."""
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Qt

from clipo.core.history import HistoryService
from clipo.storage.repository import HistoryRepository

logger = logging.getLogger(__name__)


class HistoryWorker(QObject):
    ready = Signal()
    changed = Signal()
    page_ready = Signal(object, int)
    item_ready = Signal(object, str)
    error = Signal(str)
    collections_ready = Signal(object)
    image_ready = Signal(object, object, str)
    image_stored = Signal(object)
    notice = Signal(str)

    def __init__(self, path: Path, history_limit: int, max_text_bytes: int, settings=None):
        super().__init__()
        self.path = path
        self.history_limit = history_limit
        self.max_text_bytes = max_text_bytes
        self.repository = None
        from clipo.config.settings import Settings
        from dataclasses import replace
        self.settings = replace(settings) if settings else Settings()

    @Slot()
    def initialize(self):
        try:
            self.repository = HistoryRepository(self.path, memory=not self.settings.persist_history)
            self.service = HistoryService(self.repository, self.history_limit, self.max_text_bytes)
            self.repository.set_limit(self.history_limit)
            self.ready.emit()
        except Exception:
            logger.error("History initialization failed (details omitted to protect clipboard data)")
            self.error.emit("History could not be opened. Check data directory permissions and free disk space.")

    @Slot(str, object)
    def execute(self, action, payload):
        if self.repository is None:
            self.error.emit("History is unavailable. Restart Clipo after fixing the data directory.")
            return
        try:
            if action == "capture":
                from clipo.security.policy import excluded_text
                if excluded_text(payload, self.settings.block_sensitive, self.settings.excluded_patterns):
                    self.error.emit("Sensitive or excluded text was not saved.")
                    return
                if self.service.capture(payload):
                    self.changed.emit()
            elif action == "page":
                query, generation = payload
                self.page_ready.emit(self.repository.page(query), generation)
            elif action in ("preview", "restore", "edit_item", "organize_item", "save_image", "view_image", "qr", "ocr", "snippet", "json_pretty", "json_minify", "open_url"):
                item = self.repository.get(payload)
                if item and action == "restore":
                    with self.repository.connection:
                        self.repository.connection.execute("UPDATE clipboard_items SET use_count=use_count+1 WHERE id=?", (item.id,))
                if item and item.content_type == "image" and action in ("preview", "restore", "view_image"):
                    from PySide6.QtGui import QImage
                    image = QImage(item.image_path)
                    if action == "preview":
                        image = image.scaled(800, 800, aspectMode=Qt.AspectRatioMode.KeepAspectRatio)
                    self.image_ready.emit(item, image, action)
                else:
                    self.item_ready.emit(item, action)
            elif action == "payload":
                from clipo.security.policy import excluded_text
                if "image" not in payload and excluded_text(payload.get("text", "") + payload.get("html", ""), self.settings.block_sensitive, self.settings.excluded_patterns):
                    self.error.emit("Sensitive or excluded content was not saved.")
                    return
                from clipo.services.images import store_image
                if "image" in payload:
                    image = payload["image"]
                    path, digest = store_image(image, self.repository.images)
                    import json
                    self.repository.add_payload(f"Image · {image.width()} × {image.height()}", "image", self.service.history_limit,
                        image_path=str(path), digest=digest, metadata=json.dumps({"width": image.width(), "height": image.height(), "bytes": path.stat().st_size}))
                    self.image_stored.emit(self.repository.get(self.repository.connection.execute("SELECT max(id) FROM clipboard_items").fetchone()[0]))
                else:
                    self.repository.add_payload(payload["text"], payload.get("kind", "text"), self.service.history_limit,
                        content_html=payload.get("html", ""), metadata=payload.get("metadata", ""))
                self.changed.emit()
            elif action == "flag":
                self.repository.flag(*payload)
                self.changed.emit()
            elif action == "edit":
                if len(payload[1].encode()) > self.service.max_text_bytes:
                    raise ValueError("Edited text exceeds the configured limit")
                self.repository.edit(*payload)
                self.changed.emit()
            elif action == "organize":
                self.repository.organize(*payload)
                self.changed.emit()
            elif action == "collections":
                self.collections_ready.emit(self.repository.collections_list())
            elif action == "collection":
                self.repository.manage_collection(*payload)
                self.collections_ready.emit(self.repository.collections_list())
                self.changed.emit()
            elif action == "collection_style":
                self.repository.style_collection(*payload)
                self.collections_ready.emit(self.repository.collections_list())
            elif action == "undo":
                self.repository.undo()
                self.changed.emit()
            elif action == "export_image":
                import shutil
                item_id, target = payload
                item = self.repository.get(item_id)
                if not item or not item.image_path:
                    raise ValueError("Select an image first")
                shutil.copyfile(item.image_path, target)
            elif action == "garbage_collect":
                self.repository.collect_images()
            elif action == "ocr_result":
                with self.repository.connection:
                    self.repository.connection.execute("UPDATE clipboard_items SET ocr_text=? WHERE id=?", (payload[1], payload[0]))
                self.changed.emit()
            elif action == "make_snippet":
                with self.repository.connection:
                    self.repository.connection.execute("UPDATE clipboard_items SET content_type='snippet' WHERE id=? AND content_type!='image'", (payload,))
                self.changed.emit()
            elif action == "qr_record":
                if not self.settings.persist_history:
                    return
                import hashlib
                from clipo.config.settings import private_directory
                item_id, data = payload
                path = private_directory(self.path.parent / "qr") / (hashlib.sha256(data).hexdigest() + ".png")
                if not path.exists():
                    import os
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(data)
                from datetime import datetime, timezone
                with self.repository.connection:
                    self.repository.connection.execute("INSERT INTO qr_history(clipboard_item_id,qr_image_path,created_at) VALUES(?,?,?)", (item_id, str(path), datetime.now(timezone.utc).isoformat()))
                self.changed.emit()
            elif action == "configure":
                from dataclasses import replace
                old = self.settings
                self.settings = replace(payload)
                if old.persist_history != self.settings.persist_history:
                    self.repository.close()
                    self.repository = HistoryRepository(self.path, memory=not self.settings.persist_history)
                    self.service = HistoryService(self.repository, self.settings.history_limit, self.settings.max_text_bytes)
                    self.changed.emit()
                self.service.max_text_bytes = self.settings.max_text_bytes
            elif action == "new_item":
                text, title, language, tags, collections, description = payload
                if len(text.encode()) > self.service.max_text_bytes:
                    raise ValueError("Text exceeds the configured size limit")
                if self.service.capture(text):
                    item_id = self.repository.connection.execute("SELECT max(id) FROM clipboard_items").fetchone()[0]
                    self.repository.edit(item_id, text, title, language, description)
                    self.repository.organize(item_id, tags, collections)
                    if language:
                        with self.repository.connection:
                            self.repository.connection.execute("UPDATE clipboard_items SET content_type='snippet' WHERE id=?", (item_id,))
                    self.changed.emit()
            elif action == "cleanup":
                if self.settings.retention_days:
                    from datetime import datetime, timedelta, timezone
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=self.settings.retention_days)).isoformat()
                    with self.repository.connection:
                        self.repository.connection.execute("DELETE FROM clipboard_items WHERE is_pinned=0 AND created_at<?", (cutoff,))
                    self.changed.emit()
                self.repository.collect_images()
            elif action == "delete":
                self.repository.delete(payload)
                self.changed.emit()
            elif action == "clear":
                self.repository.clear()
                with self.repository.connection:
                    self.repository.connection.execute("DELETE FROM qr_history")
                if self.settings.persist_history:
                    for path in (self.path.parent / "qr").glob("*.png"):
                        path.unlink(missing_ok=True)
                self.changed.emit()
            elif action == "export":
                from clipo.services.exchange import export_history
                path, format, query, selected = payload
                count = export_history(self.repository, path, format, query, selected)
                self.notice.emit(f"Exported {count:,} items.")
            elif action == "import":
                from clipo.services.exchange import import_history
                count = import_history(self.repository, payload, self.service.history_limit)
                self.changed.emit()
                self.notice.emit(f"Imported {count:,} items. The configured retention limit applies.")
            elif action == "scheduled_backup":
                if not self.settings.persist_history or not self.settings.backup_hours:
                    return
                import time
                from clipo.config.settings import private_directory
                directory = private_directory(Path(self.settings.backup_directory) / "clipo-backups")
                backups = sorted(directory.glob("clipo-auto-*.json"), key=lambda file: file.stat().st_mtime)
                if backups and time.time() - backups[-1].stat().st_mtime < self.settings.backup_hours * 3600:
                    return
                from clipo.services.exchange import export_history
                from datetime import datetime, timezone
                target = directory / ("clipo-auto-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json")
                export_history(self.repository, target)
                for expired in backups[:-6]:
                    expired.unlink()
                self.notice.emit("Automatic local backup saved.")
            elif action == "limit":
                self.service.history_limit = payload
                self.repository.set_limit(payload)
                self.changed.emit()
        except ValueError as error:
            self.error.emit(str(error))
        except Exception:
            logger.error("History operation failed: %s (content omitted)", action)
            self.error.emit("History operation failed. Check free disk space and data directory permissions.")

    @Slot()
    def close(self):
        if self.repository:
            self.repository.close()
            self.repository = None

