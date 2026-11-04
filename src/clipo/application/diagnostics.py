"""Exercise bundled optional engines without accessing the user's history/clipboard."""
import json
from pathlib import Path
import tempfile
from clipo import __version__


def self_test():
    from clipo.services.qr import generate_qr
    from clipo.services.recognition import format_code
    from clipo.security.vault import encrypt_backup, decrypt_backup
    from clipo.storage.repository import HistoryRepository
    from clipo.models.item import HistoryQuery
    from PySide6.QtGui import QImage, QColor
    from clipo.services.images import store_image
    import dbus_next  # Included portal transport; no connection is opened here.
    result = {"version": __version__}
    try:
        result["qr"] = generate_qr("Clipo self-test")[0].startswith(b"\x89PNG")
        result["python_formatter"] = "x = 1" in format_code("x=1\n", "Python")
        result["sql_formatter"] = "SELECT" in format_code("select 1", "SQL")
        password = "Clipo temporary self-test passphrase"
        result["backup_encryption"] = decrypt_backup(encrypt_backup(b"temporary data", password), password) == b"temporary data"
        with tempfile.TemporaryDirectory(prefix="clipo-diagnostics-") as folder:
            repository = HistoryRepository(Path(folder) / "history.sqlite3", password=password)
            repository.add("encrypted self-test", 100)
            image = QImage(32, 32, QImage.Format.Format_RGBA8888)
            image.fill(QColor("purple"))
            path, _ = store_image(image, repository.images, repository.vault)
            result["encrypted_image"] = not path.read_bytes().startswith(b"\x89PNG") and not QImage.fromData(repository.read_blob(path)).isNull()
            result["sqlcipher_fts"] = repository.page(HistoryQuery(text="self-test")).total == 1
            repository.close()
            result["encrypted_database"] = not (Path(folder) / "history.sqlite3").read_bytes().startswith(b"SQLite format 3")
        result["passed"] = all(value is True for key, value in result.items() if key != "version")
    except Exception:
        result["passed"] = False
        result["error"] = "A bundled engine self-test failed. Check the installed dependencies."
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1
