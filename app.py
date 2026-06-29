"""Provenance Guard — Flask API.

Endpoints:
  POST /submit   classify a piece of content, return verdict + confidence + label
  POST /appeal   contest a classification (status -> under_review, logged)
  GET  /log      recent audit-log entries (for documentation / grading visibility)
  GET  /stats    analytics view (stretch): verdict mix, appeal rate, avg confidence
  GET  /         tiny index describing the API

Rate limiting is applied to /submit only. .env is loaded in config (we use the
key, never print or commit it).
"""
import uuid

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import audit
from config import (
    CONTENT_TEXT,
    SUBMIT_RATE_LIMIT,
    VALID_CONTENT_TYPES,
)
from labels import HEADLINE
from pipeline import analyze

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.get("/")
def index():
    return jsonify({
        "service": "Provenance Guard",
        "description": "AI-vs-human content attribution with confidence, "
                       "transparency labels, appeals, and an audit log.",
        "endpoints": {
            "POST /submit": "{text, creator_id, content_type?}",
            "POST /appeal": "{content_id, creator_reasoning}",
            "GET /log": "recent audit entries",
            "GET /stats": "analytics summary",
        },
    })


@app.post("/submit")
@limiter.limit(SUBMIT_RATE_LIMIT)
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()
    content_type = (data.get("content_type") or CONTENT_TEXT).strip()

    if not text:
        return jsonify({"error": "Field 'text' is required and must be non-empty."}), 400
    if not creator_id:
        return jsonify({"error": "Field 'creator_id' is required."}), 400
    if content_type not in VALID_CONTENT_TYPES:
        return jsonify({
            "error": f"content_type must be one of {sorted(VALID_CONTENT_TYPES)}."
        }), 400

    content_id = str(uuid.uuid4())
    analysis = analyze(text, content_type=content_type)
    result, signals, label = analysis["result"], analysis["signals"], analysis["label"]

    audit.log_classification(content_id, creator_id, content_type, result, signals, label)

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "content_type": content_type,
        "attribution": result["verdict"],
        "headline": HEADLINE[result["verdict"]],
        "confidence": result["confidence"],
        "ai_likelihood": result["ai_likelihood"],
        "signals": {
            "llm_score": signals["llm"]["p_llm"],
            "llm_reason": signals["llm"]["reason"],
            "style_score": signals["style"]["p_style"],
            "style_metrics": signals["style"]["metrics"],
        },
        "label": label,
        "status": "classified",
    })


@app.post("/appeal")
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = (data.get("content_id") or "").strip()
    reasoning = (data.get("creator_reasoning") or "").strip()

    if not content_id:
        return jsonify({"error": "Field 'content_id' is required."}), 400
    if not reasoning:
        return jsonify({"error": "Field 'creator_reasoning' is required."}), 400

    original = audit.find_classification(content_id)
    if original is None:
        return jsonify({"error": f"No classification found for content_id {content_id}."}), 404

    audit.log_appeal(content_id, reasoning, original)

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal was received. This content is now under review by a "
                   "human moderator. The original decision remains logged alongside "
                   "your appeal.",
        "original_attribution": original.get("attribution"),
        "original_confidence": original.get("confidence"),
    })


@app.get("/log")
def get_log():
    try:
        limit = int(request.args.get("limit", 25))
    except (TypeError, ValueError):
        limit = 25
    return jsonify({"entries": audit.read_log(limit=limit)})


@app.get("/stats")
def stats():
    """Analytics view (stretch): verdict distribution, appeal rate, avg confidence."""
    entries = audit.read_log()
    classifications = [e for e in entries if e.get("event") == "classification"]
    appeals = [e for e in entries if e.get("event") == "appeal"]

    total = len(classifications)
    mix = {"likely_ai": 0, "likely_human": 0, "uncertain": 0}
    conf_sum = 0.0
    for c in classifications:
        mix[c.get("attribution", "uncertain")] = mix.get(c.get("attribution", "uncertain"), 0) + 1
        conf_sum += c.get("confidence", 0.0)

    return jsonify({
        "total_classifications": total,
        "verdict_distribution": mix,
        "verdict_ratio": {k: (round(v / total, 3) if total else 0.0) for k, v in mix.items()},
        "appeals": len(appeals),
        "appeal_rate": round(len(appeals) / total, 3) if total else 0.0,
        "avg_confidence": round(conf_sum / total, 3) if total else 0.0,
    })


@app.errorhandler(429)
def ratelimit_handler(err):
    return jsonify({
        "error": "Rate limit exceeded.",
        "detail": str(err.description),
        "limit": SUBMIT_RATE_LIMIT,
        "message": "Slow down — you've hit the submission rate limit. "
                   "Try again shortly.",
    }), 429


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
