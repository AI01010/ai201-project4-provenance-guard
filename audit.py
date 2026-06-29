"""Audit log — the accountability layer.

Append-only JSONL (one JSON object per line). I'm using JSONL over a database
because it's append-only by nature, a corrupted line doesn't kill the file, and
it's the format I already used in Lab 4. Every classification and every appeal
becomes one line. Original decisions are never rewritten — an appeal appends a
*new* line for the same content_id, so a reviewer sees both side by side.
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


def log_classification(content_id, creator_id, content_type, result, signals, label):
    """Write a classification entry from a /submit result."""
    return log_event({
        "event": "classification",
        "content_id": content_id,
        "creator_id": creator_id,
        "content_type": content_type,
        "attribution": result["verdict"],
        "ai_likelihood": result["ai_likelihood"],
        "confidence": result["confidence"],
        "disagreement": result["disagreement"],
        "llm_score": signals["llm"]["p_llm"],
        "llm_reason": signals["llm"]["reason"],
        "style_score": signals["style"]["p_style"],
        "style_metrics": signals["style"]["metrics"],
        "signals_used": ["llm_judge", "stylometrics"],
        "label_shown": label,
        "status": "classified",
        "appeal_reasoning": None,
    })


def log_appeal(content_id, creator_reasoning, original):
    """Write an appeal entry next to the original classification."""
    return log_event({
        "event": "appeal",
        "content_id": content_id,
        "creator_id": original.get("creator_id"),
        "attribution": original.get("attribution"),
        "confidence": original.get("confidence"),
        "original_label": original.get("label_shown"),
        "status": "under_review",
        "appeal_reasoning": creator_reasoning,
    })


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


def find_classification(content_id):
    """Return the original classification entry for a content_id, or None."""
    for entry in read_log():
        if entry.get("content_id") == content_id and entry.get("event") == "classification":
            return entry
    return None
