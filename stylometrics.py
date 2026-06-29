"""Signal 2 — Stylometric heuristics (pure Python, no external libraries).

This signal never reads *meaning*. It measures structure: how bursty the
sentences are, how diverse the vocabulary is, and how heavily the text leans on
the connective/hedge phrases AI loves. AI prose tends to be uniform; human
writing is irregular. That structural difference is what we exploit here.

Everything returns a P(AI) in [0, 1] so it lines up with the LLM signal.

Known blind spots (documented in planning.md):
  * short text -> the stats are meaningless (we flag `reliable=False`)
  * formal / ESL human writing scores AI-like (uniform + transition-heavy)
  * repetitive poetry tanks the type-token ratio and looks "AI"
"""
import math
import re

from config import SHORT_TEXT_FLOOR

# Sub-weights within the stylometric score. Burstiness and transition density are
# the trustworthy ones; type-token ratio is the weakest, so it gets the least say.
W_BURST = 0.45
W_TRANS = 0.35
W_TTR = 0.20

# Phrases AI models lean on far more than people do. Counted case-insensitively.
AI_TELL_PHRASES = [
    "furthermore", "moreover", "in addition", "additionally", "however",
    "it is important to note", "it is worth noting", "it's important to note",
    "in conclusion", "in summary", "overall", "ultimately",
    "in today's world", "in the realm of", "in the world of",
    "delve", "delving", "tapestry", "navigate the", "navigating the",
    "landscape of", "testament to", "plays a crucial role",
    "plays a vital role", "plays a significant role", "it is essential",
    "a wide range of", "wide array of", "numerous", "various",
    "stakeholders", "leverage", "robust", "comprehensive", "seamless",
    "foster", "underscore", "underscores", "paradigm", "holistic",
    "ever-evolving", "ever-changing", "multifaceted", "myriad",
    "on the other hand", "as a result", "consequently",
]


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _ramp(x, low, high):
    """0 when x <= low, 1 when x >= high, linear in between."""
    if high == low:
        return 0.0
    return _clamp((x - low) / (high - low))


def _split_sentences(text):
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def _words(text):
    return re.findall(r"[a-zA-Z']+", text.lower())


def _burstiness_ai(sentences):
    """Coefficient of variation of sentence length. Low CV -> uniform -> AI-like."""
    lengths = [len(_words(s)) for s in sentences]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return 0.5, 0.0  # not enough sentences to judge -> neutral
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.5, 0.0
    var = sum((n - mean) ** 2 for n in lengths) / len(lengths)
    cv = math.sqrt(var) / mean
    # Human prose typically CV ~0.5-0.8; AI clusters ~0.2-0.4.
    ai = 1.0 - _ramp(cv, 0.25, 0.75)
    return ai, round(cv, 3)


def _ttr_ai(words):
    """Moving-average type-token ratio. Low diversity -> AI-like (weak signal)."""
    if len(words) < 10:
        return 0.5, 0.0
    window = 50
    if len(words) <= window:
        ttr = len(set(words)) / len(words)
    else:
        ratios = []
        for i in range(len(words) - window + 1):
            chunk = words[i:i + window]
            ratios.append(len(set(chunk)) / window)
        ttr = sum(ratios) / len(ratios)
    ai = 1.0 - _ramp(ttr, 0.55, 0.80)
    return ai, round(ttr, 3)


def _transition_ai(text, sentences):
    """Density of AI-tell phrases per sentence. High density -> AI-like."""
    low = text.lower()
    hits = sum(low.count(p) for p in AI_TELL_PHRASES)
    n = max(len(sentences), 1)
    density = hits / n
    ai = _ramp(density, 0.10, 0.60)
    return ai, hits, round(density, 3)


def stylometric_score(text):
    """Return P(AI) plus the raw metrics that produced it.

    Returns a dict:
      {
        "p_style": float 0..1,
        "reliable": bool,          # False on very short text
        "word_count": int,
        "metrics": {burstiness_cv, type_token_ratio, ai_tell_hits, ai_tell_density},
      }
    """
    text = (text or "").strip()
    words = _words(text)
    sentences = _split_sentences(text)
    word_count = len(words)

    if word_count == 0:
        return {
            "p_style": 0.5,
            "reliable": False,
            "word_count": 0,
            "metrics": {"burstiness_cv": 0.0, "type_token_ratio": 0.0,
                        "ai_tell_hits": 0, "ai_tell_density": 0.0},
        }

    burst_ai, cv = _burstiness_ai(sentences)
    ttr_ai, ttr = _ttr_ai(words)
    trans_ai, hits, density = _transition_ai(text, sentences)

    p_style = W_BURST * burst_ai + W_TRANS * trans_ai + W_TTR * ttr_ai

    return {
        "p_style": round(_clamp(p_style), 4),
        "reliable": word_count >= SHORT_TEXT_FLOOR,
        "word_count": word_count,
        "metrics": {
            "burstiness_cv": cv,
            "type_token_ratio": ttr,
            "ai_tell_hits": hits,
            "ai_tell_density": density,
        },
    }


if __name__ == "__main__":
    import json
    import sys
    sample = sys.argv[1] if len(sys.argv) > 1 else (
        "Artificial intelligence represents a transformative paradigm shift. "
        "It is important to note that stakeholders must collaborate. Furthermore, "
        "a comprehensive approach is essential."
    )
    print(json.dumps(stylometric_score(sample), indent=2))
