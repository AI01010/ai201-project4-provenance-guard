"""The detection pipeline (Milestone 4: two signals + confidence).

analyze(text) runs both signals and combines them into one calibrated result.
Keeping this in a single place is what stops the running system and the offline
evaluation from ever disagreeing. The reader-facing transparency label is added
on top of this in Milestone 5.
"""
from llm_signal import llm_score
from scoring import combine
from stylometrics import stylometric_score


def analyze(text):
    """Run both detection signals and combine them.

    Returns:
      {
        "result": {verdict, confidence, ai_likelihood, raw, disagreement, weights},
        "signals": {"llm": {...}, "style": {...}},
      }
    """
    llm = llm_score(text)
    style = stylometric_score(text)

    result = combine(
        p_llm=llm["p_llm"],
        p_style=style["p_style"],
        word_count=style["word_count"],
        style_reliable=style["reliable"],
    )

    return {"result": result, "signals": {"llm": llm, "style": style}}
