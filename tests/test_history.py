import sqlite3

import pytest

from clipo.core.history import HistoryService
from clipo.models.item import HistoryQuery
from clipo.storage.repository import HistoryRepository


@pytest.fixture
def repository(tmp_path):
    repo = HistoryRepository(tmp_path / "data" / "history.sqlite3")
    yield repo
    repo.close()


def test_text_is_exact_and_survives_restart(tmp_path):
    path = tmp_path / "history.sqlite3"
    text = "  Hello বাংলা 👋\n\tquotes ' \" % _  "
    repo = HistoryRepository(path)
    assert repo.add(text, 1000)
    item = repo.page(HistoryQuery()).items[0]
    repo.close()
    reopened = HistoryRepository(path)
    assert reopened.get(item.id).content_text == text
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    reopened.close()


def test_only_consecutive_duplicates_are_removed(repository):
    assert repository.add("a", 0)
    assert not repository.add("a", 0)
    assert repository.add("b", 0)
    assert repository.add("a", 0)
    assert repository.page(HistoryQuery()).total == 3


def test_limit_keeps_newest_and_zero_is_unlimited(repository):
    for i in range(250):
        repository.add(str(i), 0)
    assert repository.page(HistoryQuery()).total == 250
    repository.set_limit(3)
    page = repository.page(HistoryQuery())
    assert [item.content_text for item in page.items] == ["249", "248", "247"]


def test_literal_search_pagination_delete_clear(repository):
    for text in ["100%", "under_score", "HELLO", "world", "x' OR 1=1 --"]:
        repository.add(text, 0)
    assert repository.page(HistoryQuery(text="% ")).total == 0
    assert repository.page(HistoryQuery(text="%")).total == 1
    assert repository.page(HistoryQuery(text="_")).total == 1
    assert repository.page(HistoryQuery(text="hello")).total == 1
    assert repository.page(HistoryQuery(text="' OR 1=1 --")).total == 1
    page = repository.page(HistoryQuery(limit=2, offset=2))
    assert len(page.items) == 2 and page.total == 5
    repository.delete(page.items[0].id)
    assert repository.get(page.items[0].id) is None
    repository.clear()
    assert repository.page(HistoryQuery()).total == 0


def test_preview_is_bounded_restore_uses_full_content(repository):
    text = "a" * 100000
    repository.add(text, 0)
    item = repository.page(HistoryQuery()).items[0]
    assert len(item.content_text) == 240
    assert repository.get(item.id).content_text == text


def test_today_filter_uses_local_midnight(repository):
    repository.add("old", 0)
    repository.add("today", 0)
    with repository.connection:
        repository.connection.execute("UPDATE clipboard_items SET created_at='2000-01-01T00:00:00+00:00' WHERE content_text='old'")
    assert [item.content_text for item in repository.page(HistoryQuery(today=True)).items] == ["today"]


def test_service_rejects_empty_and_oversize_without_truncation(repository):
    service = HistoryService(repository, 10, 8)
    assert not service.capture(" \n\t")
    with pytest.raises(ValueError, match="size limit"):
        service.capture("🙂🙂🙂")
    assert repository.page(HistoryQuery()).total == 0
    assert service.capture("🙂🙂")


def test_reject_future_schema(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError, match="newer"):
        HistoryRepository(path)
