"""Evaluate the pipeline against the gathered dataset.

The system has THREE verdicts but ground truth is binary (human/ai), and that's on
purpose — "uncertain" is an abstention, not a wrong answer. So I report a few views
instead of one misleading accuracy number:

  * decisive accuracy  : when the system DID make a call, how often was it right?
  * coverage           : what fraction got a confident call (vs. abstaining)?
  * false-positive rate: human work labeled AI -- the error I care about most.
  * false-negative rate: AI work labeled human -- the "less bad" error.

Plus a 3x2 confusion matrix. Output -> data/evaluation_results.json.

Run from project root:  python scripts/evaluate.py
"""
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LIKELY_AI, LIKELY_HUMAN, UNCERTAIN  # noqa: E402
from pipeline import analyze  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SAMPLES = os.path.join(DATA, "samples.jsonl")
RESULTS = os.path.join(DATA, "evaluation_results.json")


def load_samples():
    rows = []
    with open(SAMPLES, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def evaluate(rows, sleep=1.5):
    per_sample = []
    # confusion[true_label][verdict]
    confusion = {"human": {LIKELY_HUMAN: 0, UNCERTAIN: 0, LIKELY_AI: 0},
                 "ai": {LIKELY_HUMAN: 0, UNCERTAIN: 0, LIKELY_AI: 0}}
    for i, row in enumerate(rows, 1):
        out = analyze(row["text"], content_type=row.get("content_type", "text"))
        verdict = out["result"]["verdict"]
        true = row["true_label"]
        confusion[true][verdict] += 1
        decisive = verdict in (LIKELY_AI, LIKELY_HUMAN)
        correct = (verdict == LIKELY_AI and true == "ai") or \
                  (verdict == LIKELY_HUMAN and true == "human")
        per_sample.append({
            "id": row["id"], "true_label": true, "kind": row.get("kind"),
            "content_type": row.get("content_type"), "source": row.get("source"),
            "verdict": verdict, "confidence": out["result"]["confidence"],
            "ai_likelihood": out["result"]["ai_likelihood"],
            "p_llm": out["signals"]["llm"]["p_llm"],
            "p_style": out["signals"]["style"]["p_style"],
            "decisive": decisive, "correct": correct,
        })
        print(f"  {i:>2}/{len(rows)} {row['id']} {true:>5} {row.get('kind',''):<14} "
              f"-> {verdict:<13} conf={out['result']['confidence']}")
        time.sleep(sleep)
    return per_sample, confusion


def summarize(per_sample, confusion):
    total = len(per_sample)
    human_total = sum(1 for p in per_sample if p["true_label"] == "human")
    ai_total = sum(1 for p in per_sample if p["true_label"] == "ai")
    decisive = [p for p in per_sample if p["decisive"]]
    correct = [p for p in decisive if p["correct"]]
    fp = sum(1 for p in per_sample if p["true_label"] == "human" and p["verdict"] == LIKELY_AI)
    fn = sum(1 for p in per_sample if p["true_label"] == "ai" and p["verdict"] == LIKELY_HUMAN)

    def rate(a, b):
        return round(a / b, 3) if b else 0.0

    return {
        "total": total, "human_total": human_total, "ai_total": ai_total,
        "decisive_count": len(decisive),
        "coverage": rate(len(decisive), total),
        "decisive_accuracy": rate(len(correct), len(decisive)),
        "strict_accuracy_uncertain_as_miss": rate(len(correct), total),
        "false_positives_human_called_ai": fp,
        "false_positive_rate": rate(fp, human_total),
        "false_negatives_ai_called_human": fn,
        "false_negative_rate": rate(fn, ai_total),
        "confusion_matrix": confusion,
    }


def print_report(summary):
    s = summary
    print("\n" + "=" * 64)
    print("PROVENANCE GUARD — EVALUATION REPORT")
    print("=" * 64)
    print(f"samples: {s['total']}  (human={s['human_total']}, ai={s['ai_total']})")
    print(f"coverage (made a confident call):     {s['coverage']*100:.1f}%")
    print(f"decisive accuracy (when it called):   {s['decisive_accuracy']*100:.1f}%")
    print(f"strict accuracy (uncertain=miss):     {s['strict_accuracy_uncertain_as_miss']*100:.1f}%")
    print(f"FALSE POSITIVES (human -> AI):        {s['false_positives_human_called_ai']} "
          f"({s['false_positive_rate']*100:.1f}% of human)")
    print(f"false negatives (AI -> human):        {s['false_negatives_ai_called_human']} "
          f"({s['false_negative_rate']*100:.1f}% of AI)")
    print("\nconfusion matrix (rows=truth, cols=verdict):")
    cm = s["confusion_matrix"]
    print(f"          {'likely_human':>14}{'uncertain':>12}{'likely_ai':>12}")
    for truth in ("human", "ai"):
        print(f"  {truth:<6}  {cm[truth][LIKELY_HUMAN]:>14}{cm[truth][UNCERTAIN]:>12}{cm[truth][LIKELY_AI]:>12}")
    print("=" * 64)


def main():
    rows = load_samples()
    print(f"loaded {len(rows)} samples; running pipeline (live Groq calls)...")
    per_sample, confusion = evaluate(rows)
    summary = summarize(per_sample, confusion)
    with open(RESULTS, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "per_sample": per_sample}, fh, indent=2, ensure_ascii=False)
    print_report(summary)
    print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    main()
