"""Conservative content hints; copied code is never executed."""
import ipaddress
import json
import re
import uuid
from urllib.parse import urlparse


def card_like(value):
    if not re.fullmatch(r"[0-9 -]{13,25}", value):
        return False
    digits = [int(character) for character in value if character.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) < 2:
        return False
    return sum((digit * 2 - 9 if digit > 4 else digit * 2) if index % 2 else digit for index, digit in enumerate(reversed(digits))) % 10 == 0


def recognize(text):
    value = text.strip()
    parsed = urlparse(value)
    if parsed.scheme in ("https", "http") and parsed.netloc and "\n" not in value:
        return "url", ""
    if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        return "email", ""
    if card_like(value):
        return "credit_card", ""
    if re.fullmatch(r"\+?[\d ()-]{7,25}", value) and 7 <= len(re.sub(r"\D", "", value)) <= 15:
        return "phone", ""
    if value.startswith("<?xml"):
        return "snippet", "XML"
    try:
        ipaddress.ip_address(value)
        return "ip", ""
    except ValueError:
        pass
    try:
        uuid.UUID(value)
        return "uuid", ""
    except ValueError:
        pass
    if value.startswith(("{", "[")):
        try:
            json.loads(value)
            return "snippet", "JSON"
        except ValueError:
            pass
    for pattern, language in ((r"^(def |class |from \w+ import |import \w+)", "Python"), (r"^(const |let |function |export )", "JavaScript"), (r"^(SELECT |INSERT |UPDATE |CREATE TABLE |WITH )", "SQL"), (r"^#!/.*(bash|sh)", "Bash"), (r"^<(!DOCTYPE|html|div|p[ >])", "HTML")):
        if re.search(pattern, value, re.I | re.M):
            return "snippet", language
    return "text", ""


def format_code(text, language):
    if language.casefold() == "json":
        return format_json(text)
    if language.casefold() == "python":
        import black
        try:
            return black.format_file_contents(text, fast=False, mode=black.Mode())
        except black.NothingChanged:
            return text
        except (black.InvalidInput, AssertionError):
            raise ValueError("This Python snippet could not be formatted safely") from None
    if language.casefold() == "sql":
        import sqlparse
        return sqlparse.format(text, reindent=True, keyword_case="upper")
    raise ValueError("Formatting is supported for Python, SQL and JSON")


def format_json(text, compact=False):
    try:
        value = json.loads(text)
    except ValueError:
        raise ValueError("This item is not valid JSON") from None
    return json.dumps(value, ensure_ascii=False, indent=None if compact else 2, separators=(",", ":") if compact else None)
