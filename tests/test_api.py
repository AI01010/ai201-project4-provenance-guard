"""End-to-end API tests (LLM signal stubbed, audit log in a temp dir)."""

AI_TEXT = (
    "Artificial intelligence represents a transformative paradigm shift. "
    "Furthermore, stakeholders must collaborate. Moreover, a comprehensive and "
    "robust framework is essential. It is important to note the multifaceted nature."
)
HUMAN_TEXT = (
    "ok so honestly that movie was a mess lol. gonna be real, i almost walked out "
    "halfway through. u know that feeling when the plot just gives up? yeah."
)


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Provenance Guard" in r.get_json()["service"]


def test_submit_returns_required_fields(client):
    r = client.post("/submit", json={"text": HUMAN_TEXT, "creator_id": "u1"})
    assert r.status_code == 200
    body = r.get_json()
    for field in ("content_id", "attribution", "confidence", "label", "signals", "status"):
        assert field in body
    assert "llm_score" in body["signals"]
    assert "style_score" in body["signals"]
    assert body["status"] == "classified"


def test_submit_requires_text_and_creator(client):
    assert client.post("/submit", json={"creator_id": "u1"}).status_code == 400
    assert client.post("/submit", json={"text": "hello world"}).status_code == 400


def test_submit_rejects_bad_content_type(client):
    r = client.post("/submit", json={"text": HUMAN_TEXT, "creator_id": "u1",
                                     "content_type": "video"})
    assert r.status_code == 400


def test_appeal_flow_updates_status(client):
    sub = client.post("/submit", json={"text": AI_TEXT, "creator_id": "u2"}).get_json()
    cid = sub["content_id"]
    r = client.post("/appeal", json={"content_id": cid,
                                     "creator_reasoning": "I wrote this myself."})
    assert r.status_code == 200
    assert r.get_json()["status"] == "under_review"
    # appeal shows up in the log next to the original
    entries = client.get("/log").get_json()["entries"]
    appeals = [e for e in entries if e.get("event") == "appeal" and e["content_id"] == cid]
    assert len(appeals) == 1
    assert appeals[0]["status"] == "under_review"


def test_appeal_unknown_id_404(client):
    r = client.post("/appeal", json={"content_id": "does-not-exist",
                                     "creator_reasoning": "huh"})
    assert r.status_code == 404


def test_log_and_stats(client):
    client.post("/submit", json={"text": HUMAN_TEXT, "creator_id": "u3"})
    client.post("/submit", json={"text": AI_TEXT, "creator_id": "u4"})
    log = client.get("/log").get_json()
    assert len(log["entries"]) >= 2
    stats = client.get("/stats").get_json()
    assert stats["total_classifications"] >= 2
    assert "verdict_distribution" in stats
