#!/usr/bin/env python3
"""Reproducible indexed search/pagination measurement on 50,000 synthetic records."""
from pathlib import Path
import json
import tempfile
import time
from clipo.storage.repository import HistoryRepository
from clipo.models.item import HistoryQuery


def main():
    with tempfile.TemporaryDirectory(prefix="clipo-benchmark-") as folder:
        repo = HistoryRepository(Path(folder) / "history.sqlite3")
        started = time.perf_counter()
        with repo.connection:
            repo.connection.executemany(
                "INSERT INTO clipboard_items(content_text,content_hash,created_at,updated_at,content_type) VALUES(?,?,'2026-11-04T10:00:00+00:00','2026-11-04T10:00:00+00:00','text')",
                ((f"Project notes {i}: Ubuntu clipboard workflow, task ticket-{i:06d} with developer context and an example URL https://example.com/{i}.", str(i)) for i in range(50000)),
            )
        insertion = time.perf_counter() - started
        timings = {}
        for title, query in (("recent_page", HistoryQuery()), ("deep_page", HistoryQuery(offset=49000)), ("specific_substring", HistoryQuery(text="ticket-024681")), ("common_word", HistoryQuery(text="Ubuntu"))):
            samples = []
            for _ in range(5):
                before = time.perf_counter()
                result = repo.page(query)
                samples.append((time.perf_counter() - before) * 1000)
            timings[title] = {"median_ms": round(sorted(samples)[2], 2), "matches": result.total, "returned": len(result.items)}
        print(json.dumps({"records": 50000, "insert_seconds": round(insertion, 2), "queries": timings}, indent=2))
        repo.close()


if __name__ == "__main__":
    main()
