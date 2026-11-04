import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from PySide6.QtGui import QImage, QColor
from clipo.models.item import HistoryQuery
from clipo.storage.repository import HistoryRepository
from clipo.services.images import store_image
from clipo.services.exchange import export_history, import_history
from clipo.security.policy import excluded_text, excluded_application


def test_sensitive_detection_and_literal_exclusions():
    assert excluded_text("Authorization: Bearer example-token")
    assert excluded_text("-----BEGIN PRIVATE KEY-----")
    assert excluded_text("api_key=abcdefghijklmnopqrstuvwxyz")
    assert not excluded_text("ordinary text")
    assert not excluded_text("api_key=abcdefghijklmnopqrstuvwxyz", False)
    assert excluded_text("Internal Acme document", False, "\nacme\n")
    assert excluded_application("org.keepassxc.KeePassXC", "*keepass*")


def test_json_roundtrip_including_images_flags_tags_and_html(tmp_path):
    source = HistoryRepository(tmp_path / "source/history.sqlite3")
    source.add_payload("hello বাংলা", "text", 0, content_html="<b>hello বাংলা</b>")
    first = source.page(HistoryQuery()).items[0]
    source.flag(first.id, "is_pinned")
    source.organize(first.id, "important", "Work")
    source.style_collection("Work", "#336699")
    source.style_collection("Work")
    image = QImage(80, 40, QImage.Format.Format_RGBA8888)
    image.fill(QColor("green"))
    path, digest = store_image(image, source.images)
    source.add_payload("test image", "image", 0, image_path=str(path), digest=digest)
    target = tmp_path / "backup.json"
    assert export_history(source, target) == 2
    assert target.stat().st_mode & 0o777 == 0o600
    destination = HistoryRepository(tmp_path / "restored/history.sqlite3")
    assert import_history(destination, target) == 2
    restored = destination.get(destination.page(HistoryQuery(text="important")).items[0].id)
    assert restored.is_pinned and restored.collections == "Work" and restored.content_html == "<b>hello বাংলা</b>"
    assert destination.collections_list() == [{"name": "Work", "color": "#336699", "is_pinned": 1}]
    img = destination.page(HistoryQuery(view="image")).items[0]
    assert QImage(img.image_path).pixelColor(0, 0) == QColor("green")
    assert str(destination.images) in img.image_path
    source.close()
    destination.close()


def test_invalid_import_is_rejected_before_any_mutation(tmp_path):
    repo = HistoryRepository(tmp_path / "history.sqlite3")
    repo.add("keep", 0)
    target = tmp_path / "backup.json"
    export_history(repo, target)
    data = json.loads(target.read_text())
    data["items"].append({"content_text": "bad", "content_type": "executable"})
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        import_history(repo, target)
    assert repo.page(HistoryQuery()).total == 1
    repo.close()


def test_exports_escape_html_and_spreadsheet_formulas(tmp_path):
    repo = HistoryRepository(tmp_path / "history.sqlite3")
    repo.add("=HYPERLINK(\"bad\")", 0)
    repo.add("<script>alert('x')</script>", 0)
    export_history(repo, tmp_path / "data.html", "html")
    export_history(repo, tmp_path / "data.csv", "csv")
    assert "<script>" not in (tmp_path / "data.html").read_text()
    assert "'=HYPERLINK" in (tmp_path / "data.csv").read_text()
    repo.close()


def test_session_history_is_not_persisted_and_temp_images_are_removed(tmp_path):
    path = tmp_path / "history.sqlite3"
    repo = HistoryRepository(path, memory=True)
    directory = repo.images
    repo.add("session only", 0)
    assert not path.exists()
    repo.close()
    assert not directory.exists()
    reopened = HistoryRepository(path)
    assert reopened.page(HistoryQuery()).total == 0
    reopened.close()


def test_search_index_tracks_edits_ocr_tags_undo_and_clear(tmp_path):
    repo = HistoryRepository(tmp_path / "history.sqlite3")
    repo.add("original", 0)
    item = repo.page(HistoryQuery()).items[0]
    repo.edit(item.id, "replacement")
    assert repo.page(HistoryQuery(text="original")).total == 0
    assert repo.page(HistoryQuery(text="placement")).total == 1
    repo.organize(item.id, "searchable-tag", "")
    assert repo.page(HistoryQuery(text="searchable-tag")).total == 1
    with repo.connection:
        repo.connection.execute("UPDATE clipboard_items SET ocr_text='Recognized screenshot' WHERE id=?", (item.id,))
    assert repo.page(HistoryQuery(text="screenshot")).total == 1
    repo.delete(item.id)
    assert repo.page(HistoryQuery(text="screenshot")).total == 0
    repo.undo()
    assert repo.page(HistoryQuery(text="screenshot")).total == 1
    repo.clear()
    assert repo.page(HistoryQuery(text="screenshot")).total == 0
    repo.close()


def test_autostart_is_user_scoped_and_reversible(tmp_path, monkeypatch):
    from clipo.system.startup import configure_autostart
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    configure_autostart(True)
    path = tmp_path / "autostart/clipo.desktop"
    assert "--background" in path.read_text()
    configure_autostart(False)
    assert not path.exists()


def test_worker_session_switch_expiration_and_scheduled_backup(tmp_path):
    from dataclasses import replace
    from clipo.config.settings import Settings
    from clipo.core.worker import HistoryWorker
    settings = Settings(backup_hours=1, backup_directory=str(tmp_path / "backups"), retention_days=7)
    worker = HistoryWorker(tmp_path / "data/history.sqlite3", 100, 1024, settings)
    errors = []
    worker.error.connect(errors.append)
    worker.initialize()
    worker.execute("capture", "persistent clip")
    worker.execute("scheduled_backup", None)
    worker.execute("scheduled_backup", None)
    backups = list((tmp_path / "backups/clipo-backups").glob("*.json"))
    assert len(backups) == 1
    worker.execute("configure", replace(settings, persist_history=False))
    assert worker.repository.page(HistoryQuery()).total == 0
    worker.execute("capture", "session only")
    worker.execute("configure", settings)
    page = worker.repository.page(HistoryQuery())
    assert [item.content_text for item in page.items] == ["persistent clip"]
    with worker.repository.connection:
        worker.repository.connection.execute("UPDATE clipboard_items SET created_at='2000-01-01T00:00:00+00:00'")
    worker.execute("cleanup", None)
    assert worker.repository.page(HistoryQuery()).total == 0
    assert not errors
    worker.close()
