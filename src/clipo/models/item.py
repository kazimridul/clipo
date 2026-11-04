"""Immutable values passed between the GUI and storage worker."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ClipboardItem:
    id: int
    content_text: str
    content_hash: str
    created_at: str
    content_type: str = "text"


@dataclass(frozen=True)
class HistoryQuery:
    text: str = ""
    today: bool = False
    offset: int = 0
    limit: int = 100


@dataclass(frozen=True)
class HistoryPage:
    query: HistoryQuery
    items: tuple[ClipboardItem, ...]
    total: int

