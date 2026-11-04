"""All SQLite work runs serially on a dedicated Qt thread."""
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from clipo.core.history import HistoryService
from clipo.storage.repository import HistoryRepository

logger = logging.getLogger(__name__)


class HistoryWorker(QObject):
    ready = Signal()
    changed = Signal()
    page_ready = Signal(object, int)
    item_ready = Signal(object, str)
    error = Signal(str)

    def __init__(self, path: Path, history_limit: int, max_text_bytes: int):
        super().__init__()
        self.path = path
        self.history_limit = history_limit
        self.max_text_bytes = max_text_bytes
        self.repository = None

    @Slot()
    def initialize(self):
        try:
            self.repository = HistoryRepository(self.path)
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
                if self.service.capture(payload):
                    self.changed.emit()
            elif action == "page":
                query, generation = payload
                self.page_ready.emit(self.repository.page(query), generation)
            elif action in ("preview", "restore"):
                self.item_ready.emit(self.repository.get(payload), action)
            elif action == "delete":
                self.repository.delete(payload)
                self.changed.emit()
            elif action == "clear":
                self.repository.clear()
                self.changed.emit()
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

