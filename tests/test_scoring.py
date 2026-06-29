"""Tests for the confidence scorer — the heart of the system."""
from config import AI_THRESHOLD, LIKELY_AI, LIKELY_HUMAN, UNCERTAIN
from scoring import combine, confidence_band


def test_strong_agreement_ai():
    out = combine(0.95, 0.90)
    assert out["verdict"] == LIKELY_AI
    assert out["ai_likelihood"] >= AI_THRESHOLD


def test_strong_agreement_human():
    out = combine(0.05, 0.10)
    assert out["verdict"] == LIKELY_HUMAN


def test_disagreement_forces_uncertain():
    # signals far apart -> never a confident verdict, even with a high raw score
    out = combine(0.95, 0.10)
    assert out["verdict"] == UNCERTAIN
    assert out["disagreement"] > 0.40


def test_middle_band_is_uncertain():
    out = combine(0.55, 0.55)
    assert out["verdict"] == UNCERTAIN


def test_disagreement_only_pushes_toward_uncertain_never_ai():
    # A human-leaning style signal disagreeing with an AI-leaning LLM must NOT
    # produce an AI accusation. This is the false-positive guard.
    out = combine(0.85, 0.20)
    assert out["verdict"] != LIKELY_AI


def test_confidence_higher_for_stronger_evidence():
    strong = combine(0.97, 0.95)["confidence"]
    weak = combine(0.72, 0.70)["confidence"]
    assert strong > weak


def test_confidence_bounded():
    for p_llm in (0.0, 0.3, 0.5, 0.7, 1.0):
        for p_style in (0.0, 0.5, 1.0):
            assert 0.0 <= combine(p_llm, p_style)["confidence"] <= 1.0


def test_short_text_downweights_stylometrics():
    out = combine(0.9, 0.2, word_count=10)
    assert out["weights"]["llm"] == 0.85
    assert out["weights"]["style"] == 0.15


def test_unreliable_style_downweighted():
    out = combine(0.9, 0.2, word_count=200, style_reliable=False)
    assert out["weights"]["llm"] == 0.85


def test_confidence_band_mapping():
    assert confidence_band(0.9) == "high"
    assert confidence_band(0.5) == "medium"
    assert confidence_band(0.1) == "low"
