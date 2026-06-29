"""Confidence scoring — combine the two signals into one calibrated verdict.

This implements the rule in planning.md verbatim. Two ideas drive it:

  ai_likelihood = how AI-ish the combined evidence is (0 human .. 1 AI)
  confidence    = how sure we are of the verdict we're about to show a reader,
                  high ONLY when the evidence is strong AND both signals agree.

The asymmetry is deliberate: the "likely_ai" band is narrow (raw >= 0.75) and the
"likely_human" band is wide (raw <= 0.40), and signal disagreement can only ever
push us toward "uncertain" — never toward an accusation. On a writing platform,
falsely calling a human's work AI is the worst outcome, so the math leans away
from it.
"""
from config import (
    AI_THRESHOLD,
    DISAGREEMENT_LIMIT,
    HUMAN_THRESHOLD,
    LIKELY_AI,
    LIKELY_HUMAN,
    SHORT_TEXT_FLOOR,
    UNCERTAIN,
    W_LLM,
    W_LLM_SHORT,
    W_STYLE,
    W_STYLE_SHORT,
)


def combine(p_llm, p_style, word_count=None, style_reliable=True):
    """Combine two P(AI) signals into a verdict + confidence.

    Args:
      p_llm:          P(AI) from the LLM judge, 0..1
      p_style:        P(AI) from stylometrics, 0..1
      word_count:     length of the text in words (enables short-text handling)
      style_reliable: False when stylometrics flagged the text as unreliable

    Returns dict: {verdict, confidence, ai_likelihood, raw, disagreement, weights}
    """
    short = (word_count is not None and word_count < SHORT_TEXT_FLOOR) or not style_reliable
    if short:
        w_llm, w_style = W_LLM_SHORT, W_STYLE_SHORT
    else:
        w_llm, w_style = W_LLM, W_STYLE

    raw = w_llm * p_llm + w_style * p_style          # weights sum to 1
    disagreement = abs(p_llm - p_style)

    if disagreement > DISAGREEMENT_LIMIT:
        verdict = UNCERTAIN
    elif raw >= AI_THRESHOLD:
        verdict = LIKELY_AI
    elif raw <= HUMAN_THRESHOLD:
        verdict = LIKELY_HUMAN
    else:
        verdict = UNCERTAIN

    strength = abs(raw - 0.5) * 2                     # 0 at the fence, 1 at extremes
    confidence = round(strength * (1 - disagreement), 2)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "ai_likelihood": round(raw, 4),
        "raw": round(raw, 4),
        "disagreement": round(disagreement, 4),
        "weights": {"llm": w_llm, "style": w_style},
    }


def confidence_band(confidence):
    """Map a numeric confidence to a plain word used in the transparency label."""
    if confidence >= 0.66:
        return "high"
    if confidence >= 0.40:
        return "medium"
    return "low"
