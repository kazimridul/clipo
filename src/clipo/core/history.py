"""Business rules, independent of Qt widgets or clipboard ownership."""
from clipo.storage.repository import HistoryRepository


class HistoryService:
    def __init__(self, repository: HistoryRepository, history_limit: int, max_text_bytes: int):
        self.repository = repository
        self.history_limit = history_limit
        self.max_text_bytes = max_text_bytes

    def capture(self, text: str) -> bool:
        if not text or not text.strip():
            return False
        if len(text.encode("utf-8")) > self.max_text_bytes:
            raise ValueError("Clipboard text exceeds the configured size limit; it was not saved.")
        return self.repository.add(text, self.history_limit)

