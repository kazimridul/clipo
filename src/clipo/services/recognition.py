"""Conservative content hints; copied code is never executed."""
import ipaddress
import json
import re
import uuid
from urllib.parse import urlparse


def recognize(text):
    value = text.strip()
    parsed = urlparse(value)
    if parsed.scheme in ("https", "http") and parsed.netloc and "\n" not in value:
        return "url", ""
    if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        return "email", ""
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


def format_json(text, compact=False):
    try:
        value = json.loads(text)
    except ValueError:
        raise ValueError("This item is not valid JSON") from None
    return json.dumps(value, ensure_ascii=False, indent=None if compact else 2, separators=(",", ":") if compact else None)
