"""Validated configuration and XDG paths. No clipboard data belongs here."""
import json
import os
from dataclasses import asdict, dataclass
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

