#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def read_lesson_id(chunks_path: Path) -> str:
    with chunks_path.open("r", encoding="utf-8") as f:
        line = f.readline()
    if not line:
        raise SystemExit(f"Empty chunks file: {chunks_path}")
    obj = json.loads(line)
    lesson_id = obj.get("lesson_id")
    if not lesson_id:
        raise SystemExit(f"Missing lesson_id in: {chunks_path}")
    return lesson_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chunks_dir",
        default="chunks",
        help="Directory with *.chunks.jsonl files (default: chunks)",
    )
    parser.add_argument(
        "--build_script",
        default="scripts/build_glossary_and_map.py",
        help="Path to build_glossary_and_map.py",
    )
    parser.add_argument("--limit", type=int, default=0, help="Process only N files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing outputs")
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    build_script = Path(args.build_script)
    base_dir = chunks_dir.parent

    if not chunks_dir.exists():
        raise SystemExit(f"Missing chunks_dir: {chunks_dir}")
    if not build_script.exists():
        raise SystemExit(f"Missing build_script: {build_script}")

    chunk_files = sorted(chunks_dir.glob("*.chunks.jsonl"))
    if args.limit and args.limit > 0:
        chunk_files = chunk_files[: args.limit]

    total = len(chunk_files)
    if total == 0:
        raise SystemExit("No chunk files found.")

    for idx, chunks_path in enumerate(chunk_files, 1):
        lesson_id = read_lesson_id(chunks_path)
        glossary_json = base_dir / "glossary" / f"lesson_{lesson_id}.glossary.json"
        glossary_md = base_dir / "glossary" / f"lesson_{lesson_id}.glossary.md"
        map_json = base_dir / "knowledge_map" / f"lesson_{lesson_id}.map.json"
        map_md = base_dir / "knowledge_map" / f"lesson_{lesson_id}.map.md"

        outputs = [glossary_json, glossary_md, map_json, map_md]
        if not args.force and all(p.exists() for p in outputs):
            print(f"[{idx}/{total}] skip {chunks_path.stem} (outputs exist)")
            continue

        cmd = [
            sys.executable,
            str(build_script),
            "--chunks",
            str(chunks_path),
            "--glossary_json",
            str(glossary_json),
            "--glossary_md",
            str(glossary_md),
            "--map_json",
            str(map_json),
            "--map_md",
            str(map_md),
        ]
        print(f"[{idx}/{total}] build {chunks_path.stem}")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
