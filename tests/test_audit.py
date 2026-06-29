"""Tests for the append-only audit log (uses a temp log dir)."""
import audit

RESULT = {"verdict": "likely_ai", "confidence": 0.78, "ai_likelihood": 0.91,
          "disagreement": 0.05}
SIGNALS = {
    "llm": {"p_llm": 0.92, "reason": "generic phrasing", "reliable": True},
    "style": {"p_style": 0.88, "reliable": True,
              "metrics": {"burstiness_cv": 0.3, "type_token_ratio": 0.7,
                          "ai_tell_hits": 5, "ai_tell_density": 1.2}},
}


def test_classification_is_written_and_readable(temp_log):
    audit.log_classification("cid-1", "creator-1", "text", RESULT, SIGNALS, "label text")
    entries = audit.read_log()
    assert len(entries) == 1
    e = entries[0]
    assert e["content_id"] == "cid-1"
    assert e["event"] == "classification"
    assert e["attribution"] == "likely_ai"
    assert e["status"] == "classified"
    assert e["llm_score"] == 0.92
    assert e["style_score"] == 0.88
    assert "timestamp" in e


def test_find_classification(temp_log):
    audit.log_classification("cid-2", "creator-2", "text", RESULT, SIGNALS, "lbl")
    found = audit.find_classification("cid-2")
    assert found is not None and found["content_id"] == "cid-2"
    assert audit.find_classification("nope") is None


def test_appeal_appends_next_to_original(temp_log):
    audit.log_classification("cid-3", "creator-3", "text", RESULT, SIGNALS, "lbl")
    original = audit.find_classification("cid-3")
    audit.log_appeal("cid-3", "I wrote this myself, I'm just formal.", original)
    entries = audit.read_log()
    assert len(entries) == 2
    appeal = entries[-1]
    assert appeal["event"] == "appeal"
    assert appeal["status"] == "under_review"
    assert appeal["appeal_reasoning"].startswith("I wrote this")
    # original entry untouched
    assert entries[0]["status"] == "classified"


def test_read_log_limit(temp_log):
    for i in range(5):
        audit.log_classification(f"c{i}", "u", "text", RESULT, SIGNALS, "lbl")
    assert len(audit.read_log(limit=2)) == 2


def test_corrupted_line_is_skipped(temp_log):
    audit.log_classification("cid-ok", "u", "text", RESULT, SIGNALS, "lbl")
    with open(audit.LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write("this is not json\n")
    entries = audit.read_log()  # must not raise
    assert len(entries) == 1
