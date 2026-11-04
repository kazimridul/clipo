from PySide6.QtGui import QImage, QColor
from clipo.models.item import HistoryQuery
from clipo.storage.repository import HistoryRepository
from clipo.services.images import store_image


def test_flags_organization_edit_undo_and_retention(tmp_path):
    repo = HistoryRepository(tmp_path / "history.sqlite3")
    repo.add("original", 0)
    item = repo.page(HistoryQuery()).items[0]
    repo.flag(item.id, "is_pinned")
    repo.flag(item.id, "is_favorite")
    repo.organize(item.id, "ubuntu, python", "Work, Personal")
    repo.edit(item.id, "edited", "My clip", "Python")
    assert repo.page(HistoryQuery(text="python", view="favorites", collection="Work")).total == 1
    repo.add("newer", 1)
    assert repo.page(HistoryQuery()).total == 2  # Pins survive retention.
    repo.delete(item.id)
    assert repo.get(item.id) is None
    repo.undo()
    restored = repo.get(item.id)
    assert restored.content_text == "edited" and restored.is_favorite and restored.is_pinned
    assert restored.collections == "Work, Personal"
    repo.manage_collection("Work", "Office")
    assert repo.page(HistoryQuery(collection="Office")).total == 1
    repo.manage_collection("Office", "")
    assert repo.get(item.id) is not None
    repo.close()


def test_image_hash_storage_and_safe_cleanup(tmp_path):
    repo = HistoryRepository(tmp_path / "history.sqlite3")
    image = QImage(100, 80, QImage.Format.Format_RGBA8888)
    image.fill(QColor("red"))
    path, digest = store_image(image, repo.images)
    assert store_image(image, repo.images) == (path, digest)
    assert path.stat().st_mode & 0o777 == 0o600
    repo.add_payload("test image", "image", 100, image_path=str(path), digest=digest)
    assert not repo.add_payload("test image", "image", 100, image_path=str(path), digest=digest)
    item = repo.page(HistoryQuery(view="image")).items[0]
    assert QImage(repo.get(item.id).image_path).size() == image.size()
    repo.delete(item.id)
    repo.collect_images()
    assert path.exists()  # Undo can still restore it.
    repo.undo()
    repo.clear()
    assert not path.exists()
    repo.close()


def test_v1_migration_preserves_history(tmp_path):
    import sqlite3
    path = tmp_path / "history.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE clipboard_items(id INTEGER PRIMARY KEY AUTOINCREMENT,content_type TEXT NOT NULL DEFAULT 'text',content_text TEXT NOT NULL,content_hash TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        connection.execute("INSERT INTO clipboard_items VALUES(1,'text','kept','hash','2026-11-04T00:00:00+00:00','2026-11-04T00:00:00+00:00')")
        connection.execute("PRAGMA user_version=1")
    repo = HistoryRepository(path)
    assert repo.get(1).content_text == "kept"
    assert repo.connection.execute("PRAGMA user_version").fetchone()[0] == 4
    repo.close()


def test_collection_style_and_snippet_description_search(tmp_path):
    repo = HistoryRepository(tmp_path / "history.sqlite3")
    repo.add("def demo(): pass", 0)
    item = repo.page(HistoryQuery()).items[0]
    repo.edit(item.id, item.content_text, "Example", "Python", "Reusable helper")
    repo.organize(item.id, "dev", "Work, Personal")
    repo.style_collection("Work", "#336699")
    repo.style_collection("Work")
    first = repo.collections_list()[0]
    assert first == {"name": "Work", "color": "#336699", "is_pinned": 1}
    assert repo.page(HistoryQuery(text="Reusable helper")).total == 1
    repo.close()
