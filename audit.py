"""Audit log — the accountability layer (Milestone 3: basics).

Append-only JSONL (one JSON object per line). A corrupted line never kills the
file. M3 logs each submission's first-signal result; M4 extends entries with both
signal scores, and M5 adds appeal entries.
"""
import json
import os
from datetime import datetime, timezone

from config import LOG_DIR, LOG_FILE


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_event(record):
    """Append one record (dict) as a single JSON line. Stamps a timestamp if absent."""
    _ensure_dir()
    record = dict(record)
    record.setdefault("timestamp", _now_iso())
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(
        f"[audit] {record['timestamp']} "
        f"{record.get('content_id', '?')[:8]} "
        f"{record.get('event', 'event')} -> {record.get('attribution', record.get('status', '-'))}"
    )
    return record


def read_log(limit=None):
    """Return log records (most recent last). limit keeps only the last N."""
    if not os.path.exists(LOG_FILE):
        return []
    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # one bad line never breaks the rest
    if limit is not None:
        entries = entries[-limit:]
    return entries
