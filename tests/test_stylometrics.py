"""Tests for Signal 2 (stylometrics) — pure Python, no network."""
from stylometrics import stylometric_score

AI_LIKE = (
    "Artificial intelligence represents a transformative paradigm shift in modern "
    "society. It is important to note that stakeholders must collaborate across "
    "various sectors. Furthermore, a comprehensive and robust approach is essential "
    "to navigate the landscape. Moreover, the multifaceted framework underscores a "
    "holistic methodology. Additionally, organizations must leverage numerous "
    "resources to foster sustainable outcomes. In conclusion, the ever-evolving "
    "environment demands a seamless and comprehensive strategy going forward."
)
HUMAN_LIKE = (
    "ok so i finally tried that ramen place downtown and honestly? underwhelming. "
    "broth was fine but WAY too salty. thirsty for hours. my friend liked the spicy "
    "one. probably won't go back unless someone drags me there lol"
)


def test_ai_like_scores_higher_than_human_like():
    ai = stylometric_score(AI_LIKE)["p_style"]
    human = stylometric_score(HUMAN_LIKE)["p_style"]
    assert ai > human
    assert ai > 0.5
    assert human < 0.5


def test_score_is_bounded():
    for text in (AI_LIKE, HUMAN_LIKE, "x"):
        p = stylometric_score(text)["p_style"]
        assert 0.0 <= p <= 1.0


def test_short_text_flagged_unreliable():
    out = stylometric_score("Hello there. Nice day.")
    assert out["reliable"] is False
    assert out["word_count"] < 50


def test_long_text_reliable():
    assert stylometric_score(AI_LIKE)["reliable"] is True


def test_empty_text_is_neutral():
    out = stylometric_score("")
    assert out["p_style"] == 0.5
    assert out["reliable"] is False


def test_metrics_present():
    m = stylometric_score(AI_LIKE)["metrics"]
    assert set(m) == {"burstiness_cv", "type_token_ratio", "ai_tell_hits", "ai_tell_density"}
    assert m["ai_tell_hits"] >= 3  # this text is packed with AI-tells
