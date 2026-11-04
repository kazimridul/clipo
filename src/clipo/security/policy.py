"""Local sensitive-pattern detection and user-defined literal/glob exclusions."""
from fnmatch import fnmatchcase
import ast
import re
import textwrap

SENSITIVE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\bAKIA[A-Z0-9]{16}\b|\b(?:ghp_|github_pat_|sk-live-|sk-proj-)[A-Za-z0-9_-]{16,}|"
    r"(?i:authorization\s*:\s*(?:bearer|basic)\s+\S+)"
)

CREDENTIAL_ASSIGNMENT = re.compile(
    r"\b(?:api[_-]?key|access[_-]?token|password|secret)[ \t]*[=:][ \t]*"
    r"['\"]?(?P<value>[^\s'\"]{8,})", re.IGNORECASE
)


def _python_reference_spans(text):
    """Locate code references and annotations without executing copied code."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    lines = text.splitlines(keepends=True)
    offsets = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    def position(line, column):
        # Python AST columns count UTF-8 bytes, while regex offsets count characters.
        return offsets[line - 1] + len(lines[line - 1].encode()[:column].decode())

    spans = []

    def add(node):
        spans.append((position(node.lineno, node.col_offset), position(node.end_lineno, node.end_col_offset)))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            add(node)
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and any(isinstance(target, ast.Attribute) and target.attr == node.value.id for target in node.targets):
            add(node.value)
        elif isinstance(node, ast.keyword) and isinstance(node.value, ast.Name):
            add(node.value)
        elif isinstance(node, ast.Constant) and (node.value is None or isinstance(node.value, bool)):
            add(node)
        elif isinstance(node, (ast.arg, ast.AnnAssign)) and node.annotation:
            add(node.annotation)
    return spans


def sensitive_text(text):
    if SENSITIVE.search(text):
        return True
    code = textwrap.dedent(text)
    matches = list(CREDENTIAL_ASSIGNMENT.finditer(code))
    if not matches:
        return False
    references = sorted(_python_reference_spans(code))
    index, end = 0, 0
    for match in matches:
        position = match.start("value")
        while index < len(references) and references[index][0] <= position:
            end = max(end, references[index][1])
            index += 1
        if position >= end:
            return True
    return False


def excluded_text(text, block_sensitive=True, patterns=""):
    from clipo.services.recognition import card_like
    if block_sensitive and (sensitive_text(text) or card_like(text.strip())):
        return True
    # One literal per line. No user-supplied regular expression can freeze capture.
    return any(pattern.casefold() in text.casefold() for pattern in patterns.splitlines() if pattern.strip())


def excluded_application(source, patterns):
    return any(fnmatchcase(source.casefold(), pattern.strip().casefold()) for pattern in patterns.split(",") if pattern.strip())


def excluded_payload(text, html, block_sensitive=False, patterns=""):
    """Apply the same text/HTML policy at capture and persistence boundaries."""
    return bool(excluded_text(text, block_sensitive, patterns)
                or excluded_text(html, False, patterns)
                or (block_sensitive and SENSITIVE.search(html)))
