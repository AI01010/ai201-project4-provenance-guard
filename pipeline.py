"""The detection pipeline — one function the API and the eval harness both call.

analyze(text) runs both signals, combines them, builds the reader-facing label,
and returns one structured result. Keeping this in a single place is what stops
the running system and the offline evaluation from ever disagreeing.
"""
from config import CONTENT_TEXT
from labels import make_label
from llm_signal import llm_score
from scoring import combine
from stylometrics import stylometric_score


def analyze(text, content_type=CONTENT_TEXT, appeal_context=None):
    """Run the full attribution pipeline on a piece of text.

    When appeal_context is given (a creator's appeal reasoning), the LLM judge
    re-scores the text in light of it. Stylometrics is unchanged: the structure of
    the text is the same, only the semantic read gets the new context.

    Returns:
      {
        "content_type": str,
        "result": {verdict, confidence, ai_likelihood, raw, disagreement, weights},
        "signals": {"llm": {...}, "style": {...}},
        "label": str,
      }
    """
    llm = llm_score(text, appeal_context=appeal_context)
    style = stylometric_score(text)

    result = combine(
        p_llm=llm["p_llm"],
        p_style=style["p_style"],
        word_count=style["word_count"],
        style_reliable=style["reliable"],
    )
    label = make_label(result["verdict"], result["confidence"])

    return {
        "content_type": content_type,
        "result": result,
        "signals": {"llm": llm, "style": style},
        "label": label,
    }
