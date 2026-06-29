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
AI_THRESHOLD = 0.75         # raw >= this -> likely_ai   (narrow band on purpose)
HUMAN_THRESHOLD = 0.40      # raw <= this -> likely_human (wide band on purpose)

SHORT_TEXT_FLOOR = 50       # words; below this, stylometrics is unreliable

# --- Paths ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "audit.jsonl")
