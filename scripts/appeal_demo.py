"""Demonstrate appeal re-evaluation against live Groq.

Submits the formal-human paragraph that the detector false-positives as AI, then
appeals it repeatedly with the same (genuine) explanation. Because the trust
granted to the re-evaluation grows on a log curve, each appeal nudges the verdict
further toward human with diminishing steps, saturating at the cap.

Output -> data/appeal_demo.json. Run from project root: python scripts/appeal_demo.py
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from config import LOG_FILE  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

FORMAL_HUMAN = (
    "The relationship between monetary policy and asset price inflation has been "
    "extensively studied in the literature. Central banks face a fundamental tension "
    "between their mandate for price stability and the unintended consequences of "
    "prolonged low interest rates on equity and real estate valuations."
)
REASONING = ("I wrote this myself for an economics class. English is my second "
             "language, so my academic writing reads formal and uniform. The "
             "specific framing of the policy tension is my own argument.")


def main():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    client = app_module.app.test_client()

    sub = client.post("/submit", json={"text": FORMAL_HUMAN, "creator_id": "esl-writer"}).get_json()
    cid = sub["content_id"]
    print(f"original: {sub['attribution']}  confidence={sub['confidence']}  "
          f"ai_likelihood={sub['ai_likelihood']}")

    rows = [{"stage": "original", "verdict": sub["attribution"],
             "confidence": sub["confidence"], "ai_likelihood": sub["ai_likelihood"]}]

    for i in range(4):
        r = client.post("/appeal", json={"content_id": cid, "creator_reasoning": REASONING}).get_json()
        print(f"appeal #{r['appeal_number']}: trust={r['appeal_trust']}  "
              f"revised_ai_likelihood={r['revised_ai_likelihood']}  "
              f"-> {r['revised_attribution']}  conf={r['revised_confidence']}")
        rows.append({"stage": f"appeal_{r['appeal_number']}", "trust": r["appeal_trust"],
                     "revised_ai_likelihood": r["revised_ai_likelihood"],
                     "verdict": r["revised_attribution"], "confidence": r["revised_confidence"]})

    with open(os.path.join(DATA, "appeal_demo.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)
    print("\nwrote data/appeal_demo.json")


if __name__ == "__main__":
    main()
