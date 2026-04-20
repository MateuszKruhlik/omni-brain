#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

DEFAULT_MIN_WORDS = 300
DEFAULT_TARGET_WORDS = 500
DEFAULT_MAX_WORDS = 800
DEFAULT_OVERLAP_RATIO = 0.15
DEFAULT_PAUSE_THRESHOLD = 0.8

FILLER_RE = re.compile(r"\b(um+|uh+|erm+|hmm+|mm+|ah+|eh+)\b", re.IGNORECASE)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def fmt_time(t: float) -> str:
    t = int(t)
    m, s = divmod(t, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_sentence_fix(text: str) -> str:
    # Safe: only capitalization after clear sentence-ending punctuation.
    # No new words are added; no punctuation is inserted.
    if not text:
        return text
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    def repl(match):
        return match.group(1) + match.group(2).upper()

    text = re.sub(r"([.!?…]\s+)([a-z])", repl, text)
    return text


def ends_with_boundary(text: str) -> bool:
    text = text.strip()
    return bool(re.search(r"[.!?…]\"?$", text))


def is_boundary(seg, next_seg, pause_threshold):
    boundary_punct = ends_with_boundary(seg.get("text", ""))
    if next_seg is None:
        return True
    gap = max(0.0, float(next_seg.get("start", 0)) - float(seg.get("end", 0)))
    long_pause = gap >= pause_threshold
    return boundary_punct or long_pause


def load_manifest_row(manifest_path: Path, lesson_id: str):
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("lesson_id") == lesson_id:
                return row
    return None


def build_chunk_entry(segments, meta, chunk_index, segment_start_idx, segment_end_idx):
    words = [w for s in segments for w in s.get("words", [])]
    text_raw = " ".join(s.get("text", "").strip() for s in segments).strip()
    text_clean = safe_sentence_fix(clean_text(text_raw))
    start_time = segments[0].get("start", 0.0) if segments else 0.0
    end_time = segments[-1].get("end", 0.0) if segments else 0.0

    word_count_raw = len(words)
    word_count = len(text_clean.split()) if text_clean else 0
    char_count = len(text_clean)

    tags = [
        meta.get("course_id"),
        meta.get("module_id"),
        meta.get("submodule_id"),
        meta.get("lesson_id"),
    ]
    tags = [t for t in tags if t]

    return {
        "chunk_id": f"chunk_{chunk_index:04d}",
        "course_id": meta.get("course_id"),
        "course_title": meta.get("course_title"),
        "module": meta.get("module"),
        "submodule": meta.get("submodule"),
        "lesson_title": meta.get("lesson_title"),
        "lesson_id": meta.get("lesson_id"),
        "module_id": meta.get("module_id"),
        "submodule_id": meta.get("submodule_id"),
        "source_id": f"{meta.get('course_id')}:{meta.get('lesson_id')}",
        "source_type": "video",
        "source_path": meta.get("path"),
        "source_file": meta.get("file_name"),
        "start_time": float(start_time),
        "end_time": float(end_time),
        "start_time_hms": fmt_time(start_time),
        "end_time_hms": fmt_time(end_time),
        "duration_sec": float(end_time) - float(start_time),
        "word_count": word_count,
        "word_count_raw": word_count_raw,
        "char_count": char_count,
        "text": text_clean,
        "text_raw": text_raw,
        "text_clean": text_clean,
        "segment_start_index": segment_start_idx,
        "segment_end_index": segment_end_idx,
        "language": meta.get("language"),
        "source_model": meta.get("source_model"),
        "speaker": "unknown",
        "tags": tags,
    }


def chunk_segments(segments, meta, min_words, target_words, max_words, overlap_ratio, pause_threshold):
    chunks = []
    current = []
    current_words = 0
    segment_start_idx = 0
    chunk_index = 1

    for idx, seg in enumerate(segments):
        current.append(seg)
        current_words += len(seg.get("words", []))
        next_seg = segments[idx + 1] if idx + 1 < len(segments) else None
        boundary = is_boundary(seg, next_seg, pause_threshold)

        should_cut = False
        if current_words >= max_words:
            should_cut = True
        elif current_words >= target_words and boundary:
            should_cut = True
        elif idx == len(segments) - 1:
            should_cut = True

        if should_cut and current:
            chunk = build_chunk_entry(current, meta, chunk_index, segment_start_idx, idx)
            chunks.append(chunk)
            chunk_index += 1

            # Prepare overlap for next chunk
            overlap_words = int(current_words * overlap_ratio)
            if overlap_words > 0 and idx < len(segments) - 1:
                carry = []
                carry_words = 0
                for s in reversed(current):
                    carry.insert(0, s)
                    carry_words += len(s.get("words", []))
                    if carry_words >= overlap_words:
                        break
                current = carry
                current_words = sum(len(s.get("words", [])) for s in current)
                segment_start_idx = idx - len(current) + 1
            else:
                current = []
                current_words = 0
                segment_start_idx = idx + 1

    return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="WhisperX JSON transcript")
    parser.add_argument("--manifest", required=True, help="video_manifest.jsonl")
    parser.add_argument("--output", required=True, help="Output chunks.jsonl")
    parser.add_argument("--min_words", type=int, default=DEFAULT_MIN_WORDS)
    parser.add_argument("--target_words", type=int, default=DEFAULT_TARGET_WORDS)
    parser.add_argument("--max_words", type=int, default=DEFAULT_MAX_WORDS)
    parser.add_argument("--overlap_ratio", type=float, default=DEFAULT_OVERLAP_RATIO)
    parser.add_argument("--pause_threshold", type=float, default=DEFAULT_PAUSE_THRESHOLD)
    args = parser.parse_args()

    input_path = Path(args.input)
    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    lesson_id_raw = input_path.stem
    if lesson_id_raw.startswith("lesson_"):
        lesson_id_raw = lesson_id_raw[len("lesson_"):]
    lesson_id = slugify(lesson_id_raw)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    meta = load_manifest_row(manifest_path, lesson_id)
    if meta is None:
        raise SystemExit(f"Could not find lesson_id={lesson_id} in manifest")

    meta = {**meta}
    meta["language"] = data.get("language")
    meta["source_model"] = "whisperx-large-v3"

    segments = data.get("segments", [])
    chunks = chunk_segments(
        segments,
        meta,
        min_words=args.min_words,
        target_words=args.target_words,
        max_words=args.max_words,
        overlap_ratio=args.overlap_ratio,
        pause_threshold=args.pause_threshold,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Wrote {len(chunks)} chunks to {output_path}")


if __name__ == "__main__":
    main()
