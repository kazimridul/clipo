import sqlite3
import pytest
from PySide6.QtGui import QImage, QColor
from clipo.storage.repository import HistoryRepository
from clipo.models.item import HistoryQuery
from clipo.security.vault import migrate_repository, verify_password, encrypt_backup, decrypt_backup
from clipo.services.images import store_image
from clipo.services.exchange import export_encrypted, import_history

PASSWORD = "a long test passphrase 🔐"


def test_encrypted_migration_preserves_text_images_metadata_and_search(tmp_path):
    source = HistoryRepository(tmp_path / "history.sqlite3")
    source.add("Secret project text বাংলা", 100)
    item = source.page(HistoryQuery()).items[0]
    source.flag(item.id, "is_pinned")
    source.organize(item.id, "private", "Work")
    image = QImage(64, 48, QImage.Format.Format_RGBA8888)
    image.fill(QColor("red"))
    path, digest = store_image(image, source.images)
    source.add_payload("Secret image", "image", 100, image_path=str(path), digest=digest)
    migrate_repository(source, tmp_path / "vault", PASSWORD)
    encrypted_path = tmp_path / "vault/history.sqlite3"
    assert b"Secret project" not in encrypted_path.read_bytes()
    with sqlite3.connect(encrypted_path) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("SELECT * FROM clipboard_items")
    assert verify_password(encrypted_path, PASSWORD)
    with pytest.raises(ValueError):
        verify_password(encrypted_path, "wrong password")
    encrypted = HistoryRepository(encrypted_path, password=PASSWORD)
    assert encrypted.page(HistoryQuery(text="project")).total == 1
    assert encrypted.get(item.id).is_pinned
    assert encrypted.get(item.id).collections == "Work"
    stored = encrypted.page(HistoryQuery(view="image")).items[0]
    assert not open(stored.image_path, "rb").read().startswith(b"\x89PNG")
    assert QImage.fromData(encrypted.read_blob(stored.image_path)).pixelColor(0, 0) == QColor("red")
    source.close()
    encrypted.close()


def test_authenticated_blobs_and_backups_detect_tampering(tmp_path):
    repository = HistoryRepository(tmp_path / "vault/history.sqlite3", password=PASSWORD)
    path = repository.images / "image.png"
    repository.write_blob(path, b"sensitive image")
    assert repository.read_blob(path) == b"sensitive image"
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 1
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="integrity"):
        repository.read_blob(path)
    data = encrypt_backup(b"secret backup", PASSWORD)
    assert b"secret backup" not in data
    assert decrypt_backup(data, PASSWORD) == b"secret backup"
    with pytest.raises(ValueError):
        decrypt_backup(data, "wrong passphrase")
    with pytest.raises(ValueError):
        decrypt_backup(data[:-1] + bytes([data[-1] ^ 1]), PASSWORD)
    repository.close()


def test_encrypted_backup_roundtrip_without_plaintext_files(tmp_path):
    source = HistoryRepository(tmp_path / "vault/history.sqlite3", password=PASSWORD)
    source.add("secret backup payload", 100)
    target = tmp_path / "backup.clipo"
    assert export_encrypted(source, target, PASSWORD) == 1
    assert b"secret backup payload" not in target.read_bytes()
    restored = HistoryRepository(tmp_path / "restored/history.sqlite3")
    assert import_history(restored, target, password=PASSWORD) == 1
    assert restored.page(HistoryQuery()).items[0].content_text == "secret backup payload"
    assert not list(tmp_path.glob(".clipo-export-*"))
    source.close()
    restored.close()


def test_missing_encryption_metadata_is_not_silently_replaced(tmp_path):
    path = tmp_path / "vault/history.sqlite3"
    repository = HistoryRepository(path, password=PASSWORD)
    repository.add("keep this vault", 100)
    repository.close()
    (path.parent / "blob-salt").unlink()
    with pytest.raises(ValueError, match="metadata is missing"):
        HistoryRepository(path, password=PASSWORD)
    assert not (path.parent / "blob-salt").exists()
