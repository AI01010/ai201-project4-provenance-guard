"""Provenance Guard — Flask API (Milestone 3: submission endpoint + first signal).

This is the M3 slice. POST /submit mints a content_id, runs the FIRST detection
signal (the Groq LLM judge), and returns a result with a placeholder confidence
and label. Real confidence scoring is Milestone 4; the production layer — the
three transparency labels, appeals, and rate limiting — is Milestone 5.
"""
import uuid

from flask import Flask, jsonify, request

import audit
from config import AI_THRESHOLD, HUMAN_THRESHOLD, LIKELY_AI, LIKELY_HUMAN, UNCERTAIN
from llm_signal import llm_score

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify({
        "service": "Provenance Guard (Milestone 3)",
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
    llm = llm_score(text)
    p = llm["p_llm"]

    # Placeholder verdict from signal 1 ALONE. The real, calibrated combination of
    # two signals lands in Milestone 4 — this is just enough to prove the route.
    if p >= AI_THRESHOLD:
        attribution = LIKELY_AI
    elif p <= HUMAN_THRESHOLD:
        attribution = LIKELY_HUMAN
    else:
        attribution = UNCERTAIN

    audit.log_event({
        "event": "classification",
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "llm_score": p,
        "llm_reason": llm["reason"],
        "confidence": None,
        "status": "classified",
    })

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": None,                       # placeholder until M4
        "signals": {"llm_score": p, "llm_reason": llm["reason"]},
        "label": "(transparency label added in Milestone 5)",
        "status": "classified",
    })


@app.get("/log")
def get_log():
    limit = request.args.get("limit", 25, type=int)
    return jsonify({"entries": audit.read_log(limit=limit)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
