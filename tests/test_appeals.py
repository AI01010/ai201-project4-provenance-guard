"""Tests for appeal re-evaluation (diminishing-returns reweighting)."""
from appeals import appeal_trust, reweigh
from config import APPEAL_CAP, APPEAL_MAX_TRUST

AI_TEXT = (
    "Artificial intelligence represents a transformative paradigm shift. "
    "Furthermore, stakeholders must collaborate. Moreover, a comprehensive and "
    "robust framework is essential. It is important to note the multifaceted nature."
)


def test_trust_increases_with_diminishing_increments():
    t = [appeal_trust(k) for k in (1, 2, 3, 4)]
    assert t[0] < t[1] < t[2] < t[3]
    increments = [t[i + 1] - t[i] for i in range(3)]
    assert increments[0] > increments[1] > increments[2]  # log-shaped: diminishing


def test_trust_caps_at_max():
    assert appeal_trust(1) < APPEAL_MAX_TRUST
    assert appeal_trust(APPEAL_CAP) == APPEAL_MAX_TRUST
    assert appeal_trust(APPEAL_CAP + 10) == APPEAL_MAX_TRUST  # saturates


def test_reweigh_moves_toward_reeval_more_with_more_appeals():
    reeval = {"ai_likelihood": 0.30, "disagreement": 0.10}  # explanation lowered it
    r1 = reweigh(0.80, reeval, 1)
    r4 = reweigh(0.80, reeval, 4)
    assert 0.30 < r1["revised_ai_likelihood"] < 0.80
    assert r4["revised_ai_likelihood"] < r1["revised_ai_likelihood"]
    assert r4["revised_ai_likelihood"] >= 0.30  # never overshoots the re-evaluation


def test_single_appeal_cannot_flip_a_strong_verdict_alone():
    reeval = {"ai_likelihood": 0.20, "disagreement": 0.10}
    r1 = reweigh(0.85, reeval, 1)
    assert r1["revised_ai_likelihood"] > 0.5  # one appeal isn't enough to flip


def test_bogus_appeal_with_no_new_info_does_not_help():
    # If the re-evaluation matches the original (unconvincing explanation),
    # the revised score equals the original no matter the appeal number.
    reeval = {"ai_likelihood": 0.80, "disagreement": 0.05}
    assert abs(reweigh(0.80, reeval, 3)["revised_ai_likelihood"] - 0.80) < 1e-9


def test_appeal_endpoint_returns_revised_assessment(client):
    sub = client.post("/submit", json={"text": AI_TEXT, "creator_id": "u"}).get_json()
    r = client.post("/appeal", json={
        "content_id": sub["content_id"],
        "creator_reasoning": "I wrote this myself; I'm a non-native speaker so it reads formal.",
    }).get_json()
    assert r["status"] == "under_review"
    assert r["appeal_number"] == 1
    assert "revised_attribution" in r
    assert "appeal_trust" in r
