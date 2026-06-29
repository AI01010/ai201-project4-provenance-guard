"""Provenance Guard — Flask API (Milestone 4: two signals + confidence scoring).

POST /submit now runs BOTH detection signals and returns a real, calibrated
confidence score plus each signal's individual score. The transparency label and
the production layer (appeals, rate limiting) arrive in Milestone 5.
"""
import uuid

from flask import Flask, jsonify, request

import audit
from pipeline import analyze

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify({
        "service": "Provenance Guard (Milestone 4)",
        "endpoints": {"POST /submit": "{text, creator_id}", "GET /log": "recent entries"},
    })


@app.post("/submit")
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "Field 'text' is required and must be non-empty."}), 400
    if not creator_id:
        return jsonify({"error": "Field 'creator_id' is required."}), 400

    content_id = str(uuid.uuid4())
    analysis = analyze(text)
    result, signals = analysis["result"], analysis["signals"]

    audit.log_event({
        "event": "classification",
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": result["verdict"],
        "ai_likelihood": result["ai_likelihood"],
        "confidence": result["confidence"],
        "disagreement": result["disagreement"],
        "llm_score": signals["llm"]["p_llm"],
        "llm_reason": signals["llm"]["reason"],
        "style_score": signals["style"]["p_style"],
        "style_metrics": signals["style"]["metrics"],
        "signals_used": ["llm_judge", "stylometrics"],
        "status": "classified",
    })

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": result["verdict"],
        "confidence": result["confidence"],
        "ai_likelihood": result["ai_likelihood"],
        "signals": {
            "llm_score": signals["llm"]["p_llm"],
            "llm_reason": signals["llm"]["reason"],
            "style_score": signals["style"]["p_style"],
            "style_metrics": signals["style"]["metrics"],
        },
        "label": "(transparency label added in Milestone 5)",
        "status": "classified",
    })


@app.get("/log")
def get_log():
    limit = request.args.get("limit", 25, type=int)
    return jsonify({"entries": audit.read_log(limit=limit)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
