"""Appeal re-evaluation — diminishing-returns reweighting.

When a creator appeals, we don't just flip a status flag. We re-run detection with
their reasoning as context (see pipeline.analyze(appeal_context=...)) and blend the
re-evaluation into the original score. How much we trust the re-evaluation grows
with each appeal, but on a log curve that saturates, and it never reaches 1.0.

Why a log curve, capped, and below 1.0:
  * The first appeal earns the biggest benefit-of-the-doubt; later ones earn less.
  * Appeals are self-interested. A real explanation lowers the re-scored p_ai (the
    LLM is told to stay skeptical); a bogus one barely moves it. So repeated empty
    appeals do nothing even though trust technically rises.
  * Trust caps below 1.0, so an appeal can never single-handedly flip a verdict.
    A human reviewer still owns the final decision (status -> under_review).
"""
import math

from config import APPEAL_CAP, APPEAL_MAX_TRUST
from scoring import decide


def appeal_trust(k):
    """Trust granted to the re-evaluation at appeal #k (1-based).

    Log curve scaled to APPEAL_MAX_TRUST, saturating at APPEAL_CAP appeals:
      trust(k) = APPEAL_MAX_TRUST * ln(1+k) / ln(1+APPEAL_CAP),  k clamped to CAP
    """
    k = max(1, min(int(k), APPEAL_CAP))
    return round(APPEAL_MAX_TRUST * math.log(1 + k) / math.log(1 + APPEAL_CAP), 4)


def reweigh(original_ai_likelihood, reeval_result, k):
    """Blend the original AI-likelihood with the appeal re-evaluation.

    Args:
      original_ai_likelihood: ai_likelihood from the original classification
      reeval_result:          scoring result from re-running with appeal context
                              (must have "ai_likelihood" and "disagreement")
      k:                      this appeal's number (1-based)

    Returns a dict describing the revised provisional decision.
    """
    trust = appeal_trust(k)
    reeval_ai = reeval_result["ai_likelihood"]
    revised_ai = round(original_ai_likelihood * (1 - trust) + reeval_ai * trust, 4)
    verdict, confidence = decide(revised_ai, reeval_result["disagreement"])
    return {
        "appeal_number": int(k),
        "trust": trust,
        "saturated": int(k) >= APPEAL_CAP,
        "original_ai_likelihood": round(original_ai_likelihood, 4),
        "reeval_ai_likelihood": round(reeval_ai, 4),
        "revised_ai_likelihood": revised_ai,
        "revised_verdict": verdict,
        "revised_confidence": confidence,
    }
