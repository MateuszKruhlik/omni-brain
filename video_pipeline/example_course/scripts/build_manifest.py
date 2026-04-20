#!/usr/bin/env python3
import csv
import json
import os
import re
import subprocess
from pathlib import Path

# Configure these via CLI arguments or edit defaults below
COURSE_ROOT = None  # Set via --course_root
WORK_ROOT = None    # Set via --work_root
MANIFEST_JSONL = None
MANIFEST_CSV = None
FFPROBE = "ffprobe"  # Assumes ffprobe is in PATH

COURSE_ID = None
COURSE_TITLE = None

PILOT_PATH = None  # Optional: set via --pilot to mark a specific lesson


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def get_duration_seconds(path: Path):
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        data = json.loads(out.decode("utf-8"))
        return float(data["format"]["duration"])
    except Exception:
        return None


def iter_videos(root: Path):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            low = fn.lower()
            if not low.endswith(".mp4"):
                continue
            if low.endswith(".mp4.tmp"):
                continue
            yield Path(dirpath) / fn


def build_manifest(course_root, work_root, course_id, pilot_path=None):
    course_title = course_root.name
    manifest_jsonl = work_root / "manifests" / "video_manifest.jsonl"
    manifest_csv = work_root / "manifests" / "video_manifest.csv"

    rows = []
    for path in iter_videos(course_root):
        rel = path.relative_to(course_root)
        parts = rel.parts
        module = parts[0] if len(parts) > 0 else ""
        submodule = parts[1] if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
        filename = parts[-1]
        lesson_title = filename.rsplit(".", 1)[0]
        lesson_id = slugify(lesson_title)
        module_id = slugify(module)
        submodule_id = slugify(submodule) if submodule else ""
        duration = get_duration_seconds(path)
        rows.append(
            {
                "course_id": course_id,
                "course_title": course_title,
                "module": module,
                "submodule": submodule,
                "lesson_title": lesson_title,
                "lesson_id": lesson_id,
                "module_id": module_id,
                "submodule_id": submodule_id,
                "file_name": filename,
                "path": str(path),
                "duration_sec": duration,
                "is_pilot": str(path) == str(pilot_path) if pilot_path else False,
            }
        )

    manifest_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with manifest_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with manifest_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "course_id",
                "course_title",
                "module",
                "submodule",
                "lesson_title",
                "lesson_id",
                "module_id",
                "submodule_id",
                "file_name",
                "duration_sec",
                "is_pilot",
                "path",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {manifest_jsonl}")
    print(f"Wrote {len(rows)} rows to {manifest_csv}")


if __name__ == "__main__":
    import argparse as _ap
    parser = _ap.ArgumentParser(description="Build video manifest from course folder")
    parser.add_argument("--course_root", required=True, help="Path to source video folder")
    parser.add_argument("--work_root", required=True, help="Path to course work directory")
    parser.add_argument("--course_id", required=True, help="Course slug (snake_case)")
    parser.add_argument("--pilot", default=None, help="Optional path to pilot lesson file")
    args = parser.parse_args()
    build_manifest(
        course_root=Path(args.course_root),
        work_root=Path(args.work_root),
        course_id=args.course_id,
        pilot_path=Path(args.pilot) if args.pilot else None,
    )
