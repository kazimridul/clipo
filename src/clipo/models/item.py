"""Immutable values passed between the GUI and storage worker."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClipboardItem:
    id: int
    content_text: str
    content_hash: str
    created_at: str
    content_type: str = "text"
    image_path: str = ""
    is_favorite: bool = False
    is_pinned: bool = False
    title: str = ""
    language: str = ""
    ocr_text: str = ""
    tags: str = ""
    collections: str = ""
    content_html: str = ""
    file_metadata: str = ""
    use_count: int = 0
    description: str = ""


@dataclass(frozen=True)
class HistoryQuery:
    text: str = ""
    today: bool = False
    offset: int = 0
    limit: int = 100
    view: str = "all"
    collection: str = ""
    sort: str = "newest"
    since: str = ""
    until: str = ""


@dataclass(frozen=True)
class HistoryPage:
    query: HistoryQuery
    items: tuple[ClipboardItem, ...]
    total: int
    thumbnails: dict[int, bytes] = field(default_factory=dict)

