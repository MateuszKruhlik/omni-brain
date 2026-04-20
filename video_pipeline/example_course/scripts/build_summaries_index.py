#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def read_summary_text(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    summary_lines = []
    for line in lines:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            summary_lines.append(line[2:].strip())
    return " ".join(summary_lines).strip()


def read_glossary_terms(path: Path, top_n=15):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])[:top_n]
    return [i.get("term") for i in items if i.get("term")]


def read_chunk_stats(path: Path):
    chunk_count = 0
    total_words = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            chunk_count += 1
            total_words += int(obj.get("word_count", 0))
    return chunk_count, total_words


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks_dir", default="chunks")
    parser.add_argument("--summaries_dir", default="summaries")
    parser.add_argument("--glossary_dir", default="glossary")
    parser.add_argument("--output", default="summaries/summaries_index.jsonl")
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    summaries_dir = Path(args.summaries_dir)
    glossary_dir = Path(args.glossary_dir)

    chunk_files = sorted(chunks_dir.glob("*.chunks.jsonl"))
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out:
        for chunk_path in chunk_files:
            with chunk_path.open("r", encoding="utf-8") as f:
                first_line = f.readline()
            if not first_line:
                continue
            first = json.loads(first_line)
            lesson_id = first.get("lesson_id")
            lesson_title = first.get("lesson_title")
            course_id = first.get("course_id")
            course_title = first.get("course_title")
            module = first.get("module")
            submodule = first.get("submodule")
            source_path = first.get("source_path")
            source_file = first.get("source_file")

            summary_path = summaries_dir / f"lesson_{lesson_id}.summary.md"
            summary_text = read_summary_text(summary_path) if summary_path.exists() else ""

            glossary_path = glossary_dir / f"lesson_{lesson_id}.glossary.json"
            top_terms = read_glossary_terms(glossary_path, top_n=15)

            chunk_count, total_words = read_chunk_stats(chunk_path)

            row = {
                "lesson_id": lesson_id,
                "lesson_title": lesson_title,
                "course_id": course_id,
                "course_title": course_title,
                "module": module,
                "submodule": submodule,
                "summary": summary_text,
                "top_terms": top_terms,
                "chunk_count": chunk_count,
                "total_words": total_words,
                "source_path": source_path,
                "source_file": source_file,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
