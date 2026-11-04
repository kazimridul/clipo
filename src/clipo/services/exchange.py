"""Portable, validated local backups and escaped readable exports."""
import base64
import csv
import hashlib
import html
import json
import os
import tempfile
import re
from dataclasses import asdict, replace
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from PIL import Image
from clipo.models.item import HistoryQuery

MAX_BACKUP = 128 * 1024 * 1024


def items(repository, query=None, selected=None):
    if selected is not None:
        for item_id in selected:
            item = repository.get(item_id)
            if item:
                yield item
        return
    query, offset = query or HistoryQuery(), 0
    while True:
        page = repository.page(replace(query, offset=offset, limit=200))
        for item in page.items:
            yield repository.get(item.id)
        offset += len(page.items)
        if not page.items or offset >= page.total:
            break


def export_history(repository, target, format="json", query=None, selected=None):
    target = Path(target)
    fd, temporary_name = tempfile.mkstemp(prefix=".clipo-export-", dir=target.parent)
    temporary = Path(temporary_name)
    count = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            if format == "json":
                stream.write('{"clipo_backup":1,"collections":')
                json.dump(repository.collections_list(), stream, ensure_ascii=False)
                stream.write(',"items":[')
            elif format == "html":
                stream.write('<!doctype html><meta charset="utf-8"><title>Clipo export</title>')
            elif format == "csv":
                writer = csv.writer(stream)
                writer.writerow(["type", "text", "created_at", "title", "tags", "collections"])
            elif format != "txt":
                raise ValueError("Supported formats: JSON, TXT, CSV, HTML")
            for item in items(repository, query, selected):
                if format == "json":
                    data = asdict(item)
                    data.pop("id")
                    data.pop("image_path")
                    if item.image_path:
                        path = Path(item.image_path)
                        if not path.is_relative_to(repository.images):
                            raise ValueError("Image reference is outside managed storage")
                        data["image_base64"] = base64.b64encode(path.read_bytes()).decode()
                    if count:
                        stream.write(",")
                    json.dump(data, stream, ensure_ascii=False)
                elif format == "html":
                    stream.write("<article><h2>" + html.escape(item.title or item.content_type) + "</h2><pre>" + html.escape(item.content_text or item.ocr_text) + "</pre></article>\n")
                elif format == "csv":
                    cells = [item.content_type, item.content_text, item.created_at, item.title, item.tags, item.collections]
                    writer.writerow(["'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value for value in cells])
                else:
                    stream.write(item.content_text + "\n\n")
                count += 1
                if stream.tell() > MAX_BACKUP:
                    raise ValueError("Export exceeds 128 MiB. Export a smaller collection or selection.")
            if format == "json":
                stream.write("]}")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return count


def validate_backup(path):
    path = Path(path)
    if path.stat().st_size > MAX_BACKUP:
        raise ValueError("Backup exceeds 128 MiB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("This is not a valid Clipo JSON backup") from None
    if not isinstance(data, dict) or data.get("clipo_backup") != 1 or not isinstance(data.get("items"), list) or len(data["items"]) > 100000:
        raise ValueError("Unsupported backup structure or version")
    categories = data.get("collections", [])
    if not isinstance(categories, list) or len(categories) > 10000:
        raise ValueError("Invalid collection definitions")
    for category in categories:
        if not isinstance(category, dict) or not isinstance(category.get("name"), str) or not 1 <= len(category["name"]) <= 100 or "," in category["name"]:
            raise ValueError("Invalid collection name")
        if not isinstance(category.get("color"), str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", category["color"]) or type(category.get("is_pinned")) not in (int, bool) or category["is_pinned"] not in (0, 1):
            raise ValueError("Invalid collection appearance")
    validated = []
    for record in data["items"]:
        if not isinstance(record, dict):
            raise ValueError("Invalid item in backup")
        clean = {}
        for key in ("content_text", "content_type", "created_at", "content_html", "file_metadata", "title", "language", "tags", "collections", "ocr_text", "description"):
            value = record.get(key, "")
            if not isinstance(value, str) or len(value.encode()) > 16 * 1024 * 1024:
                raise ValueError("Invalid item text in backup")
            clean[key] = value
        if clean["content_type"] not in ("text", "image", "url", "email", "ip", "uuid", "files", "snippet"):
            raise ValueError("Unsupported clipboard type in backup")
        if len(clean["title"]) > 300 or len(clean["description"]) > 4000 or len(clean["language"]) > 100:
            raise ValueError("Oversized item title, description, or language")
        try:
            timestamp = datetime.fromisoformat(clean["created_at"])
            if timestamp.tzinfo is None:
                raise ValueError()
            clean["created_at"] = timestamp.astimezone(timezone.utc).isoformat()
            if clean["content_type"] == "files":
                urls = json.loads(clean["file_metadata"])
                if not isinstance(urls, list) or any(not isinstance(url, str) or not url.startswith("file://") for url in urls):
                    raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Invalid timestamp or file metadata") from None
        for key in ("is_favorite", "is_pinned"):
            value = record.get(key, False)
            if type(value) not in (bool, int) or value not in (0, 1):
                raise ValueError("Invalid item flags")
            clean[key] = bool(value)
        for names in (clean["tags"], clean["collections"]):
            if len(names) > 10000 or any(len(name.strip()) > 100 for name in names.split(",")):
                raise ValueError("Invalid tag or collection name")
        if clean["content_type"] == "image":
            try:
                raw = base64.b64decode(record.get("image_base64", ""), validate=True)
                with Image.open(BytesIO(raw)) as image:
                    if image.format != "PNG" or image.width * image.height > 32_000_000:
                        raise ValueError()
                    image.verify()
                clean["image_bytes"] = raw
            except Exception:
                raise ValueError("Invalid or oversized PNG in backup") from None
        validated.append(clean)
    return validated, categories


def import_history(repository, path, history_limit=0):
    records, categories = validate_backup(path)
    created_files = []
    try:
        with repository.connection:
            for category in categories:
                repository.connection.execute("INSERT INTO categories(name,color,is_pinned) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET color=excluded.color,is_pinned=excluded.is_pinned", (category["name"], category["color"], category["is_pinned"]))
            for record in records:
                data = dict(record)
                raw = data.pop("image_bytes", None)
                tags, collections = data.pop("tags"), data.pop("collections")
                if raw is not None:
                    image_path = repository.images / (hashlib.sha256(raw).hexdigest() + ".png")
                    if not image_path.exists():
                        fd = os.open(image_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                        created_files.append(image_path)
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(raw)
                    data["image_path"] = str(image_path)
                data["content_hash"] = hashlib.sha256((data["content_type"] + data["content_text"]).encode() + (raw or b"")).hexdigest()
                data["updated_at"] = data["created_at"]
                data["search_tags"] = tags
                cursor = repository.connection.execute("INSERT INTO clipboard_items(" + ",".join(data) + ") VALUES(" + ",".join("?" for _ in data) + ")", list(data.values()))
                for names, table, relation, key in ((tags, "tags", "item_tags", "tag_id"), (collections, "categories", "item_categories", "category_id")):
                    for name in dict.fromkeys(name.strip() for name in names.split(",") if name.strip()):
                        repository.connection.execute(f"INSERT OR IGNORE INTO {table}(name) VALUES(?)", (name,))
                        repository.connection.execute(f"INSERT INTO {relation}(item_id,{key}) SELECT ?,id FROM {table} WHERE name=?", (cursor.lastrowid, name))
            repository.prune(history_limit)
    except Exception:
        for file in created_files:
            file.unlink(missing_ok=True)
        raise
    return len(records)
