"""Tests for the transparency labels — must be plain, varied, and fair."""
from config import LIKELY_AI, LIKELY_HUMAN, UNCERTAIN
from labels import make_label

BANNED_JARGON = ["classifier", "logit", "raw score", "ai_likelihood", "probability",
                 "stylometric", "p_llm", "p_style"]


def test_all_three_variants_distinct():
    ai = make_label(LIKELY_AI, 0.8)
    human = make_label(LIKELY_HUMAN, 0.8)
    uncertain = make_label(UNCERTAIN, 0.3)
    assert ai != human != uncertain != ai


def test_ai_label_offers_appeal():
    assert "appeal" in make_label(LIKELY_AI, 0.8).lower()


def test_confidence_changes_the_text():
    # Same verdict, different confidence -> different wording (not just a number).
    high = make_label(LIKELY_AI, 0.9)
    low = make_label(LIKELY_AI, 0.3)
    assert high != low
    assert "confident" in high.lower()


def test_no_jargon_anywhere():
    for verdict, conf in [(LIKELY_AI, 0.9), (LIKELY_HUMAN, 0.9), (UNCERTAIN, 0.2)]:
        label = make_label(verdict, conf).lower()
        for word in BANNED_JARGON:
            assert word not in label, f"jargon '{word}' leaked into label"


def test_confidence_percent_shown():
    assert "90%" in make_label(LIKELY_HUMAN, 0.9)


def test_uncertain_says_inconclusive():
    assert "inconclusive" in make_label(UNCERTAIN, 0.3).lower()
