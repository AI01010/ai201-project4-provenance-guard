"""Capture real runtime evidence for the README.

Exercises the actual app (real Groq calls, real rate limiter, real audit log):
  Phase A: 3 classifications + 1 appeal -> snapshot a clean audit sample
  Phase B: a 12-request burst -> capture the 429 rate-limit responses

Outputs:
  data/sample_audit_log.jsonl   (clean 4-entry audit sample for the repo)
  data/evidence.json            (submission responses + rate-limit status codes)

Run from project root:  python scripts/capture_evidence.py
"""
import json
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from config import LOG_FILE  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

CLEARLY_AI = (
    "Artificial intelligence represents a transformative paradigm shift in modern "
    "society. It is important to note that while the benefits of AI are numerous, it "
    "is equally essential to consider the ethical implications. Furthermore, "
    "stakeholders across various sectors must collaborate to ensure responsible "
    "deployment of these comprehensive and robust systems."
)
CLEARLY_HUMAN = (
    "ok so i finally tried that new ramen place downtown and honestly? underwhelming. "
    "the broth was fine but they put WAY too much sodium in it and i was thirsty for "
    "like three hours after. my friend got the spicy version and said it was better. "
    "probably won't go back unless someone drags me there"
)
FORMAL_HUMAN = (
    "The relationship between monetary policy and asset price inflation has been "
    "extensively studied in the literature. Central banks face a fundamental tension "
    "between their mandate for price stability and the unintended consequences of "
    "prolonged low interest rates on equity and real estate valuations."
)


def main():
    # Start clean so the evidence is reproducible.
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    client = app_module.app.test_client()
    evidence = {"submissions": [], "appeal": None, "rate_limit_burst": []}

    # --- Phase A: real classifications ---
    print("== Phase A: classifications ==")
    cases = [("clearly AI", CLEARLY_AI, "ai-writer-01"),
             ("clearly human", CLEARLY_HUMAN, "human-writer-02"),
             ("formal human (borderline)", FORMAL_HUMAN, "human-writer-03")]
    responses = []
    for name, text, creator in cases:
        r = client.post("/submit", json={"text": text, "creator_id": creator})
        body = r.get_json()
        responses.append((name, body))
        evidence["submissions"].append({"case": name, "response": body})
        print(f"  {name}: {body['attribution']} (conf {body['confidence']}, "
              f"ai_likelihood {body['ai_likelihood']})")

    # --- Appeal the formal-human case (the false-positive-risk one) ---
    print("== Appeal ==")
    appeal_target = responses[2][1]["content_id"]
    ar = client.post("/appeal", json={
        "content_id": appeal_target,
        "creator_reasoning": "I wrote this myself for an economics class. English is "
                             "my second language, so my writing tends to read formal — "
                             "please have a human review this.",
    })
    evidence["appeal"] = ar.get_json()
    print(f"  appeal status: {ar.get_json()['status']}")

    # Snapshot the clean audit sample (3 classifications + 1 appeal).
    shutil.copyfile(LOG_FILE, os.path.join(DATA, "sample_audit_log.jsonl"))
    print(f"  snapshotted clean audit sample ({len(open(LOG_FILE, encoding='utf-8').readlines())} lines)")

    # --- Phase B: trip the rate limiter (10/min) ---
    print("== Phase B: rate-limit burst (12 requests) ==")
    for i in range(12):
        r = client.post("/submit", json={"text": "Rate limit test submission for evidence.",
                                          "creator_id": "ratelimit-test"})
        evidence["rate_limit_burst"].append(r.status_code)
        print(f"  request {i+1:>2}: {r.status_code}")

    with open(os.path.join(DATA, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, ensure_ascii=False)

    codes = evidence["rate_limit_burst"]
    print(f"\nrate-limit burst status codes: {codes}")
    print(f"  200s: {codes.count(200)}   429s: {codes.count(429)}")
    print("wrote data/sample_audit_log.jsonl and data/evidence.json")


if __name__ == "__main__":
    main()
