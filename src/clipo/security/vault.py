"""SQLCipher databases and authenticated private blob/backup storage."""
import hashlib
import os
from pathlib import Path
import tempfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BLOB_MAGIC = b"CLIPOBL1"
BACKUP_MAGIC = b"CLIPOBK1"


def private_write(path: Path, data: bytes):
    fd, name = tempfile.mkstemp(prefix=".clipo-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def derive_key(password: str, salt: bytes):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=32768, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def encrypt_backup(data: bytes, password: str):
    salt, nonce = os.urandom(16), os.urandom(12)
    header = BACKUP_MAGIC + salt + nonce
    return header + AESGCM(derive_key(password, salt)).encrypt(nonce, data, header)


def decrypt_backup(data: bytes, password: str):
    if not data.startswith(BACKUP_MAGIC) or len(data) < 52:
        raise ValueError("Invalid encrypted backup")
    try:
        return AESGCM(derive_key(password, data[8:24])).decrypt(data[24:36], data[36:], data[:36])
    except Exception:
        raise ValueError("Backup password is incorrect or the backup was modified") from None


class BlobVault:
    def __init__(self, root: Path, password: str, create=False):
        self.root = root
        salt_path = root / "blob-salt"
        if not salt_path.exists():
            if not create:
                raise ValueError("Encrypted vault blob metadata is missing. Restore the complete vault or a portable backup.")
            private_write(salt_path, os.urandom(16))
        salt = salt_path.read_bytes()
        if len(salt) != 16:
            raise ValueError("Invalid encrypted vault metadata")
        self.cipher = AESGCM(derive_key(password, salt))

    def write(self, path: Path, data: bytes):
        nonce = os.urandom(12)
        aad = str(path.relative_to(self.root)).encode()
        private_write(path, BLOB_MAGIC + nonce + self.cipher.encrypt(nonce, data, aad))

    def read(self, path: Path):
        data = path.read_bytes()
        if not data.startswith(BLOB_MAGIC):
            raise ValueError("Encrypted image/QR file has an invalid header")
        try:
            return self.cipher.decrypt(data[8:20], data[20:], str(path.relative_to(self.root)).encode())
        except Exception:
            raise ValueError("Encrypted image/QR file failed integrity verification") from None


def open_database(path: Path, password: str):
    from sqlcipher3 import dbapi2
    connection = dbapi2.connect(str(path), timeout=5)
    try:
        if not connection.execute("PRAGMA cipher_version").fetchone():
            raise ValueError("SQLCipher engine is unavailable")
        connection.execute("PRAGMA key='" + password.replace("'", "''") + "'")
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA cipher_memory_security=ON")
        return connection, dbapi2.Row
    except Exception:
        connection.close()
        raise ValueError("Vault password is incorrect or the database is damaged") from None


def verify_password(path: Path, password: str):
    if not path.is_file():
        raise ValueError("Encrypted vault database is missing")
    connection, _ = open_database(path, password)
    connection.close()
    return True


def migrate_repository(source, final_root: Path, password: str):
    """Copy into a new encrypted store; the original stays until explicitly removed."""
    from clipo.storage.repository import HistoryRepository
    if len(password) < 12:
        raise ValueError("Use a vault passphrase of at least 12 characters")
    if final_root.exists():
        raise ValueError("An encrypted vault already exists. Unlock it instead of overwriting it.")
    with tempfile.TemporaryDirectory(prefix=".vault-migration-", dir=final_root.parent) as folder:
        staging = Path(folder) / "vault"
        target = HistoryRepository(staging / "history.sqlite3", password=password)
        try:
            with target.connection:
                for table in ("categories", "tags", "clipboard_items", "item_categories", "item_tags", "qr_history"):
                    cursor = source.connection.execute(f"SELECT * FROM {table}")
                    columns = [column[0] for column in cursor.description]
                    for row in cursor:
                        values = dict(zip(columns, row))
                        if table == "clipboard_items" and values["image_path"]:
                            original = Path(values["image_path"])
                            relative = original.relative_to(source.images)
                            destination = target.images / relative
                            target.write_blob(destination, source.read_blob(original))
                            thumb = source.images / "thumbnails" / original.name
                            if thumb.exists():
                                from clipo.config.settings import private_directory
                                private_directory(target.images / "thumbnails")
                                target.write_blob(target.images / "thumbnails" / original.name, source.read_blob(thumb))
                            values["image_path"] = str(final_root / "images" / relative)
                        if table == "qr_history":
                            original = Path(values["qr_image_path"])
                            from clipo.config.settings import private_directory
                            directory = private_directory(staging / "qr")
                            if original.exists():
                                target.write_blob(directory / original.name, source.read_blob(original))
                            values["qr_image_path"] = str(final_root / "qr" / original.name)
                        target.connection.execute(f"INSERT INTO {table}(" + ",".join(columns) + ") VALUES(" + ",".join("?" for _ in columns) + ")", list(values.values()))
            # Verify row counts before publishing the vault directory atomically.
            for table in ("clipboard_items", "categories", "item_tags"):
                if source.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] != target.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                    raise ValueError("Encrypted migration verification failed")
        finally:
            target.close()
        staging.rename(final_root)
