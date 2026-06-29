"""Run the four calibration inputs from the spec through the pipeline.

This is how I check the scores are *meaningful*: clearly-AI and clearly-human
should land in opposite confident bands, and the two borderline cases should land
in 'uncertain' with visibly lower confidence. Output is captured into the README.

Run from the project root:  python scripts/calibrate.py
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import analyze  # noqa: E402

CASES = [
    ("Clearly AI-generated", "expect: likely_ai, high conf",
     "Artificial intelligence represents a transformative paradigm shift in modern "
     "society. It is important to note that while the benefits of AI are numerous, it "
     "is equally essential to consider the ethical implications. Furthermore, "
     "stakeholders across various sectors must collaborate to ensure responsible "
     "deployment."),
    ("Clearly human-written", "expect: likely_human, decent conf",
     "ok so i finally tried that new ramen place downtown and honestly? "
     "underwhelming. the broth was fine but they put WAY too much sodium in it and i "
     "was thirsty for like three hours after. my friend got the spicy version and "
     "said it was better. probably won't go back unless someone drags me there"),
    ("Borderline: formal human", "expect: uncertain, lower conf",
     "The relationship between monetary policy and asset price inflation has been "
     "extensively studied in the literature. Central banks face a fundamental tension "
     "between their mandate for price stability and the unintended consequences of "
     "prolonged low interest rates on equity and real estate valuations."),
    ("Borderline: lightly edited AI", "expect: uncertain / mid",
     "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
     "flexibility and no commute on one side, isolation and blurred work-life "
     "boundaries on the other. Studies show productivity varies widely by individual "
     "and role type."),
]


def main():
    for name, expectation, text in CASES:
        out = analyze(text)
        r = out["result"]
        s = out["signals"]
        print("=" * 78)
        print(f"{name}  ({expectation})")
        print(f"  p_llm   = {s['llm']['p_llm']:.3f}   reason: {s['llm']['reason']}")
        print(f"  p_style = {s['style']['p_style']:.3f}   metrics: {json.dumps(s['style']['metrics'])}")
        print(f"  raw/ai_likelihood = {r['ai_likelihood']:.3f}   disagreement = {r['disagreement']:.3f}")
        print(f"  VERDICT = {r['verdict']}   CONFIDENCE = {r['confidence']}")
        print(f"  LABEL: {out['label']}")
    print("=" * 78)


if __name__ == "__main__":
    main()
