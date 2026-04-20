#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


def run(cmd, log_path: Path | None = None):
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as f:
            f.write("COMMAND: " + " ".join(cmd) + "\n\n")
            f.flush()
            subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT)
    else:
        subprocess.run(cmd, check=True)


def append_timing(report_csv: Path, report_jsonl: Path, row: dict):
    report_csv.parent.mkdir(parents=True, exist_ok=True)
    report_jsonl.parent.mkdir(parents=True, exist_ok=True)

    write_header = not report_csv.exists()
    with report_csv.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    with report_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path to video_manifest.jsonl")
    parser.add_argument("--work_root", required=True, help="Root of the course work directory")
    parser.add_argument("--whisperx_bin", default="whisperx", help="Path to whisperx binary (default: uses PATH)")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="Path to ffmpeg binary (default: uses PATH)")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="en")
    parser.add_argument("--compute_type", default="int8")
    parser.add_argument("--vad_method", default="silero")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--start_index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only_module", default=None, help="Optional substring to filter module name")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    work_root = Path(args.work_root)
    transcripts_dir = work_root / "transcripts"
    audio_dir = work_root / "audio"
    logs_dir = work_root / "logs"
    report_csv = work_root / "reports" / "transcription_timing.csv"
    report_jsonl = work_root / "reports" / "transcription_timing.jsonl"

    rows = []
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    if args.only_module:
        rows = [r for r in rows if args.only_module.lower() in r.get("module", "").lower()]

    # filter to unprocessed
    unprocessed = []
    for r in rows:
        lesson_id = r.get("lesson_id")
        base = f"lesson_{lesson_id}"
        transcript_json = transcripts_dir / f"{base}.json"
        if not transcript_json.exists():
            unprocessed.append(r)

    if args.limit is not None:
        rows = unprocessed[args.start_index : args.start_index + args.limit]
    else:
        rows = unprocessed[args.start_index :]

    if not rows:
        print("No rows to process.")
        return

    for idx, row in enumerate(rows, start=1):
        lesson_id = row.get("lesson_id")
        base = f"lesson_{lesson_id}"
        audio_path = audio_dir / f"{base}.wav"
        transcript_json = transcripts_dir / f"{base}.json"
        source_path = row.get("path")
        audio_duration_sec = row.get("duration_sec")

        print(f"[{idx}/{len(rows)}] {base}")

        start_ts = datetime.now()
        t0 = time.time()
        extract_sec = 0.0
        transcribe_sec = 0.0
        status = "ok"
        error = ""

        try:
            if not audio_path.exists():
                print(f"  - extracting audio -> {audio_path.name}")
                t_extract = time.time()
                run([
                    args.ffmpeg,
                    "-y",
                    "-i",
                    source_path,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-vn",
                    str(audio_path),
                ])
                extract_sec = time.time() - t_extract

            print("  - transcribing with WhisperX")
            t_trans = time.time()
            log_path = logs_dir / f"{base}.whisperx.log"
            run([
                args.whisperx_bin,
                str(audio_path),
                "--model",
                args.model,
                "--language",
                args.language,
                "--output_dir",
                str(transcripts_dir),
                "--output_format",
                "all",
                "--compute_type",
                args.compute_type,
                "--vad_method",
                args.vad_method,
                "--device",
                args.device,
            ], log_path=log_path)
            transcribe_sec = time.time() - t_trans

        except subprocess.CalledProcessError as e:
            status = "error"
            error = f"{e}"
        finally:
            t1 = time.time()
            end_ts = datetime.now()
            total_sec = t1 - t0
            rtf = None
            if audio_duration_sec:
                try:
                    rtf = total_sec / float(audio_duration_sec)
                except Exception:
                    rtf = None

            timing_row = {
                "lesson_id": lesson_id,
                "lesson_title": row.get("lesson_title"),
                "module": row.get("module"),
                "submodule": row.get("submodule"),
                "source_path": source_path,
                "audio_duration_sec": audio_duration_sec,
                "start_time": start_ts.isoformat(timespec="seconds"),
                "end_time": end_ts.isoformat(timespec="seconds"),
                "total_sec": round(total_sec, 2),
                "extract_sec": round(extract_sec, 2),
                "transcribe_sec": round(transcribe_sec, 2),
                "rtf": round(rtf, 3) if rtf is not None else "",
                "status": status,
                "error": error,
            }
            append_timing(report_csv, report_jsonl, timing_row)


if __name__ == "__main__":
    main()
