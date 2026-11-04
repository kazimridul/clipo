"""Validated configuration and XDG paths. No clipboard data belongs here."""
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def xdg_path(variable: str, fallback: str) -> Path:
    candidate = Path(os.environ.get(variable, ""))
    return (candidate if candidate.is_absolute() else Path.home() / fallback) / "clipo"


def private_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


@dataclass
class Settings:
    history_limit: int = 1000  # Zero means unlimited.
    max_text_bytes: int = 1024 * 1024
    theme: str = "system"
    paused: bool = False
    private: bool = False
    quick_shortcut: str = "Ctrl+Shift+V"
    auto_ocr: bool = False
    ocr_language: str = "eng"
    block_sensitive: bool = True
    excluded_patterns: str = ""
    excluded_apps: str = ""
    retention_days: int = 0
    persist_history: bool = True
    autostart: bool = False
    backup_hours: int = 0
    backup_directory: str = ""
    encrypted: bool = False
    portal_shortcut: bool = False
    key_bindings: dict[str, str] = field(default_factory=lambda: {"search": "Ctrl+F", "quit": "Ctrl+Q", "pin": "Ctrl+P", "delete": "Delete", "private": "Ctrl+Shift+P", "pause": "Ctrl+Shift+Space", "qr": "Ctrl+Shift+Q"})

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Settings must be a JSON object")
        result = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if type(result.history_limit) is not int or not 0 <= result.history_limit <= 1_000_000:
            raise ValueError("Invalid history limit")
        if type(result.max_text_bytes) is not int or not 1024 <= result.max_text_bytes <= 16 * 1024 * 1024:
            raise ValueError("Invalid text size limit")
        if result.theme not in ("system", "light", "dark") or type(result.paused) is not bool or type(result.private) is not bool:
            raise ValueError("Invalid appearance or monitoring setting")
        from clipo.system.shortcuts import parse_shortcut
        if not isinstance(result.quick_shortcut, str):
            raise ValueError("Invalid quick clipboard shortcut")
        parse_shortcut(result.quick_shortcut)
        import re
        if type(result.auto_ocr) is not bool or not isinstance(result.ocr_language, str) or not re.fullmatch(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*", result.ocr_language):
            raise ValueError("Invalid OCR settings")
        if any(type(getattr(result, key)) is not bool for key in ("block_sensitive", "persist_history", "autostart", "encrypted", "portal_shortcut")):
            raise ValueError("Invalid privacy or integration setting")
        if any(not isinstance(getattr(result, key), str) or len(getattr(result, key)) > 10000 for key in ("excluded_patterns", "excluded_apps")):
            raise ValueError("Invalid exclusion patterns")
        if type(result.retention_days) is not int or not 0 <= result.retention_days <= 36500:
            raise ValueError("Invalid history expiration")
        if type(result.backup_hours) is not int or not 0 <= result.backup_hours <= 8760 or not isinstance(result.backup_directory, str):
            raise ValueError("Invalid backup settings")
        if result.backup_hours and not Path(result.backup_directory).is_absolute():
            raise ValueError("Scheduled backups require an absolute local directory")
        if not isinstance(result.key_bindings, dict) or set(result.key_bindings) != set(cls().key_bindings) or any(not isinstance(value, str) or len(value) > 100 for value in result.key_bindings.values()):
            raise ValueError("Invalid keyboard bindings")
        return result

    def save(self, path: Path) -> None:
        private_directory(path.parent)
        temporary = path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(asdict(self), stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)

