"""Local sensitive-pattern detection and user-defined literal/glob exclusions."""
from fnmatch import fnmatchcase
import re

SENSITIVE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\bAKIA[A-Z0-9]{16}\b|\b(?:ghp_|github_pat_|sk-live-|sk-proj-)[A-Za-z0-9_-]{16,}|"
    r"(?i:authorization\s*:\s*(?:bearer|basic)\s+\S+)|"
    r"(?i:(?:api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*['\"]?[^\s'\"]{8,})"
)


def excluded_text(text, block_sensitive=True, patterns=""):
    if block_sensitive and SENSITIVE.search(text):
        return True
    # One literal per line. No user-supplied regular expression can freeze capture.
    return any(pattern.casefold() in text.casefold() for pattern in patterns.splitlines() if pattern.strip())


def excluded_application(source, patterns):
    return any(fnmatchcase(source.casefold(), pattern.strip().casefold()) for pattern in patterns.split(",") if pattern.strip())
