#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

STOPWORDS = {
    "the","and","for","that","with","this","you","your","are","was","were","from","they","their","have","has","had",
    "what","when","where","which","who","whom","whose","why","how","a","an","to","of","in","on","at","by",
    "it","is","be","as","or","if","we","our","us","but","so","do","does","did","can","could","should",
    "would","will","just","not","no","yes","then","than","there","here","about","into","out","up","down",
    "over","under","again","all","any","both","each","few","more","most","other","some","such","only","own",
    "same","too","very","also","like","because","been","being","them","he","she","him","her","they","them",
    "i","me","my","mine","we","us","our","ours","your","yours","its","it's","im","ive","dont","didnt",
    "you're","we're","that's","there's","it's","let's","cant","can't"
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{2,}")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def tokenize(text: str):
    words = WORD_RE.findall(text.lower())
    return [w for w in words if w not in STOPWORDS]


def extract_summary(sentences, word_freq, top_n=6):
    scored = []
    for idx, sent in enumerate(sentences):
        words = tokenize(sent)
        if not words:
            continue
        score = sum(word_freq.get(w, 0) for w in words) / max(1, len(words))
        scored.append((score, idx, sent.strip()))
    scored.sort(reverse=True)
    top = sorted(scored[:top_n], key=lambda x: x[1])
    return [s for _, _, s in top]


def fmt_time(t):
    m, s = divmod(int(t), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", required=True, help="chunks.jsonl")
    parser.add_argument("--glossary_json", required=True)
    parser.add_argument("--glossary_md", required=True)
    parser.add_argument("--map_json", required=True)
    parser.add_argument("--map_md", required=True)
    args = parser.parse_args()

    chunks = []
    with open(args.chunks, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    if not chunks:
        raise SystemExit("No chunks loaded")

    lesson_id = chunks[0].get("lesson_id")
    lesson_title = chunks[0].get("lesson_title")

    term_freq = Counter()
    first_seen = {}
    example_chunk = {}

    full_text = " ".join(c.get("text", "") for c in chunks)
    sentences = SENT_SPLIT_RE.split(full_text)

    for c in chunks:
        words = tokenize(c.get("text", ""))
        term_freq.update(words)
        for w in words:
            if w not in first_seen:
                first_seen[w] = c.get("start_time", 0.0)
                example_chunk[w] = c.get("chunk_id")

    top_terms = [w for w, _ in term_freq.most_common(40)]
    glossary = []
    for term in top_terms:
        glossary.append({
            "term": term,
            "count": term_freq[term],
            "first_seen": float(first_seen.get(term, 0.0)),
            "first_seen_hms": fmt_time(first_seen.get(term, 0.0)),
            "example_chunk": example_chunk.get(term),
            "definition": "",
        })

    # Knowledge map via co-occurrence in chunks (heuristic)
    top_set = set(top_terms[:30])
    pair_counts = Counter()
    for c in chunks:
        words = set(w for w in tokenize(c.get("text", "")) if w in top_set)
        if len(words) < 2:
            continue
        for a, b in combinations(sorted(words), 2):
            pair_counts[(a, b)] += 1

    edges = []
    for (a, b), w in pair_counts.most_common(30):
        edges.append({"source": a, "target": b, "weight": int(w), "relation": "co_occurs"})

    # Write glossary
    Path(args.glossary_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.glossary_json, "w", encoding="utf-8") as f:
        json.dump({"items": glossary}, f, ensure_ascii=False, indent=2)

    with open(args.glossary_md, "w", encoding="utf-8") as f:
        f.write("# Glossary (auto, heuristic)\n\n")
        f.write("| Term | Count | First Seen | Example Chunk | Definition |\n")
        f.write("|---|---:|---|---|---|\n")
        for item in glossary:
            f.write(
                f"| {item['term']} | {item['count']} | {item['first_seen_hms']} | {item['example_chunk']} |  |\n"
            )

    # Write knowledge map
    Path(args.map_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.map_json, "w", encoding="utf-8") as f:
        json.dump({"edges": edges}, f, ensure_ascii=False, indent=2)

    with open(args.map_md, "w", encoding="utf-8") as f:
        f.write("# Knowledge Map (auto, heuristic)\n\n")
        f.write("Top co-occurring term pairs from this lesson transcript.\n\n")
        for e in edges:
            f.write(f"- {e['source']} ↔ {e['target']} (weight={e['weight']})\n")

    # Write summary
    summary_sents = extract_summary(sentences, term_freq, top_n=6)
    summary_path = Path(args.glossary_md).parents[1] / "summaries" / f"lesson_{lesson_id}.summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Summary (extractive, heuristic)\n\n")
        if lesson_title:
            f.write(f"**Lesson:** {lesson_title}\n\n")
        for s in summary_sents:
            f.write(f"- {s}\n")
        f.write("\n## Notes\n")
        f.write("Auto-generated; replace with LLM summary for higher quality.\n")

    print("Glossary, knowledge map, and summary written.")


if __name__ == "__main__":
    main()
