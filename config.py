"""Central config for Provenance Guard.

Everything that's a knob lives here so the spec (planning.md) and the code can't
silently drift apart. If you change a threshold, change it here and nowhere else.
"""
import os
from dotenv import load_dotenv

# Loads GROQ_API_KEY (and anything else) from .env if it exists.
# We *use* .env at runtime; we never print it and never commit it.
load_dotenv()

# --- Groq ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Verdict constants ---
LIKELY_AI = "likely_ai"
LIKELY_HUMAN = "likely_human"
UNCERTAIN = "uncertain"
VALID_VERDICTS = {LIKELY_AI, LIKELY_HUMAN, UNCERTAIN}

# --- Scoring weights & thresholds (mirror planning.md) ---
W_LLM = 0.65            # the LLM judge gets the larger vote (it reads meaning)
W_STYLE = 0.35          # stylometrics is noisier on short / formal text
W_LLM_SHORT = 0.85      # on short text, lean almost entirely on the LLM
W_STYLE_SHORT = 0.15

DISAGREEMENT_LIMIT = 0.40   # signals farther apart than this -> force "uncertain"
# planning.md specced AI_THRESHOLD at 0.75. At 0.75 the system never confidently
# caught AI on naturalistic text (see data/evaluation_results.json), so I lowered
# it to 0.70 — which recovered real true positives with 0 false positives on my
# 24-sample human eval set. The honest cost: formal / ESL human writing overlaps
# with AI in score-space, so 0.70 DOES misfire on harder cases (the monetary-
# policy example in the README is one). That's an unavoidable trade with these two
# signals, and it's why appeals are a first-class feature. Documented as a spec
# divergence in the README. Small-sample calibration; re-tune before prod.
AI_THRESHOLD = 0.70         # raw >= this -> likely_ai   (narrow band on purpose)
HUMAN_THRESHOLD = 0.40      # raw <= this -> likely_human (wide band on purpose)

SHORT_TEXT_FLOOR = 50       # words; below this, stylometrics is unreliable

# --- Paths ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "audit.jsonl")

# --- Appeal re-evaluation (diminishing-returns reweighting) ---
# An appeal re-runs detection with the creator's reasoning as context. We grant
# the re-evaluation a "trust" weight that grows with each appeal but on a log
# curve, saturating at APPEAL_MAX_TRUST by APPEAL_CAP appeals. It never reaches
# 1.0, so an appeal can never single-handedly flip a verdict. A human still owns
# the final call. This is the anti-gaming knob: appealing 50 times can't brute
# force a flip, and a bogus "trust me" barely moves the score because the
# re-evaluation LLM stays skeptical.
APPEAL_MAX_TRUST = 0.70     # most the re-evaluation can ever weigh vs. the original
APPEAL_CAP = 4              # appeals past this add no further trust (log saturates)

# --- Rate limiting ---
SUBMIT_RATE_LIMIT = "10 per minute;100 per day"

# --- Content types (text is required; art_description is the multi-modal stretch) ---
CONTENT_TEXT = "text"
CONTENT_ART = "art_description"
VALID_CONTENT_TYPES = {CONTENT_TEXT, CONTENT_ART}
