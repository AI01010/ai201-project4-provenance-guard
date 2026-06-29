"""Build a real, labeled evaluation dataset.

HUMAN samples are scraped from public / public-domain sources:
  * PoetryDB        (public-domain poetry)            -> content_type=text
  * Wikipedia REST  (CC BY-SA encyclopedic prose)     -> content_type=text
  * Art Institute of Chicago API (open-access)         -> content_type=art_description

AI samples are generated with Groq (llama-3.3-70b-versatile) on matched topics:
  poems, blog posts, marketing copy, encyclopedic summaries, and art descriptions.

We never tell the model "write like an AI" — we just ask it to write, so the
samples are genuine model output. Each record is one line of data/samples.jsonl:

  {"id","content_type","true_label","source","kind","topic","text"}

Run from project root:  python data/gather_data.py
"""
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GROQ_API_KEY, GROQ_MODEL  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples.jsonl")
UA = {"User-Agent": "ProvenanceGuard/1.0 (ai201 project; educational use)"}
SLEEP = 2.0  # be polite to Groq free-tier rate limits

WIKI_TITLES = [
    "Photosynthesis", "Jazz", "Mount Everest", "Black hole", "Origami",
    "Espresso", "Great Barrier Reef", "Bicycle",
]
AI_POEM_TOPICS = ["the sea at night", "an empty train station", "autumn leaves",
                  "a grandmother's kitchen", "city rain"]
AI_BLOG_TOPICS = ["why i switched to a standing desk", "a weekend trip to the coast",
                  "learning to bake sourdough", "my first marathon"]
AI_MARKETING_TOPICS = ["a new productivity app", "an eco-friendly water bottle",
                       "a meal-kit subscription"]
AI_ENCYC_TOPICS = ["the water cycle", "the history of jazz", "how volcanoes form",
                   "the invention of the printing press"]
AI_ART_SUBJECTS = ["an abstract painting of a thunderstorm",
                   "a bronze sculpture of a running horse",
                   "a watercolor of a quiet harbor at dawn"]


def _strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


# ----------------------------- HUMAN sources -----------------------------------

def human_poems(n=8):
    out = []
    try:
        r = requests.get(f"https://poetrydb.org/random/{n}", headers=UA, timeout=30)
        r.raise_for_status()
        for poem in r.json():
            text = "\n".join(poem.get("lines", [])).strip()
            if len(text.split()) < 20:
                continue
            out.append({
                "content_type": "text", "true_label": "human", "source": "poetrydb",
                "kind": "poem", "topic": poem.get("title", ""), "text": text,
            })
        print(f"[human] poetrydb: {len(out)} poems")
    except Exception as exc:
        print(f"[human] poetrydb FAILED: {exc}")
    return out


def human_wiki(titles=WIKI_TITLES):
    out = []
    for title in titles:
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            extract = r.json().get("extract", "").strip()
            if len(extract.split()) >= 25:
                out.append({
                    "content_type": "text", "true_label": "human", "source": "wikipedia",
                    "kind": "encyclopedic", "topic": title, "text": extract,
                })
        except Exception as exc:
            print(f"[human] wiki '{title}' FAILED: {exc}")
        time.sleep(0.3)
    print(f"[human] wikipedia: {len(out)} intros")
    return out


def human_art(n=8):
    out = []
    try:
        url = ("https://api.artic.edu/api/v1/artworks?limit=60"
               "&fields=id,title,artist_display,medium_display,description")
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        for art in r.json().get("data", []):
            desc = _strip_html(art.get("description"))
            if desc and len(desc.split()) >= 30:
                out.append({
                    "content_type": "art_description", "true_label": "human",
                    "source": "artic", "kind": "art_description",
                    "topic": art.get("title", ""), "text": desc,
                })
            if len(out) >= n:
                break
        print(f"[human] art institute: {len(out)} descriptions")
    except Exception as exc:
        print(f"[human] art institute FAILED: {exc}")
    return out


# ----------------------------- AI generation -----------------------------------

_client = None


def _groq():
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _generate(prompt):
    resp = _groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()


def ai_samples():
    out = []
    jobs = []
    for t in AI_POEM_TOPICS:
        jobs.append(("text", "poem", t,
                     f"Write a short free-verse poem about {t}. 8-14 lines. "
                     f"Output only the poem, no title, no commentary."))
    for t in AI_BLOG_TOPICS:
        jobs.append(("text", "blog", t,
                     f"Write a short personal blog post (120-180 words) titled '{t}'. "
                     f"Output only the post."))
    for t in AI_MARKETING_TOPICS:
        jobs.append(("text", "marketing", t,
                     f"Write a short marketing blurb (80-130 words) for {t}. "
                     f"Output only the blurb."))
    for t in AI_ENCYC_TOPICS:
        jobs.append(("text", "encyclopedic", t,
                     f"Write a neutral encyclopedic summary (100-160 words) of {t}. "
                     f"Output only the summary."))
    for s in AI_ART_SUBJECTS:
        jobs.append(("art_description", "art_description", s,
                     f"Write a 60-110 word gallery wall-label description for {s}. "
                     f"Output only the description."))

    for i, (ctype, kind, topic, prompt) in enumerate(jobs, 1):
        try:
            text = _generate(prompt)
            out.append({
                "content_type": ctype, "true_label": "ai", "source": "groq",
                "kind": kind, "topic": topic, "text": text,
            })
            print(f"[ai] {i}/{len(jobs)} {kind}: {topic[:40]}")
        except Exception as exc:
            print(f"[ai] {kind} '{topic}' FAILED: {exc}")
        time.sleep(SLEEP)
    return out


def main():
    samples = []
    samples += human_poems()
    samples += human_wiki()
    samples += human_art()
    samples += ai_samples()

    for i, s in enumerate(samples, 1):
        s["id"] = f"s{i:03d}"

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        for s in samples:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    human = sum(1 for s in samples if s["true_label"] == "human")
    ai = sum(1 for s in samples if s["true_label"] == "ai")
    art = sum(1 for s in samples if s["content_type"] == "art_description")
    print("-" * 60)
    print(f"wrote {len(samples)} samples -> {OUT_PATH}")
    print(f"  human={human}  ai={ai}  art_descriptions={art}")


if __name__ == "__main__":
    main()
