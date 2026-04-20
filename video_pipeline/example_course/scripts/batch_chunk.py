#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work_root", required=True, help="Root of the course work directory")
    parser.add_argument("--manifest", required=True, help="Path to video_manifest.jsonl")
    parser.add_argument("--chunker", default="scripts/chunk_transcript.py", help="Path to chunk_transcript.py")
    parser.add_argument("--start_index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Rebuild chunks even if output exists")
    args = parser.parse_args()

    work_root = Path(args.work_root)
    transcripts_dir = work_root / "transcripts"
    chunks_dir = work_root / "chunks"

    transcripts = sorted(transcripts_dir.glob("lesson_*.json"))
    if args.limit is not None:
        transcripts = transcripts[args.start_index : args.start_index + args.limit]
    else:
        transcripts = transcripts[args.start_index :]

    if not transcripts:
        print("No transcripts found.")
        return

    for idx, transcript_path in enumerate(transcripts, start=1):
        base = transcript_path.stem
        output_path = chunks_dir / f"{base}.chunks.jsonl"
        if output_path.exists() and not args.force:
            print(f"[{idx}/{len(transcripts)}] skip {output_path.name}")
            continue
        print(f"[{idx}/{len(transcripts)}] chunk {base}")
        run([
            "python3",
            args.chunker,
            "--input",
            str(transcript_path),
            "--manifest",
            args.manifest,
            "--output",
            str(output_path),
        ])


if __name__ == "__main__":
    main()
