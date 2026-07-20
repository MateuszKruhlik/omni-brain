#!/usr/bin/env python3
"""Brain HTML builder — bakes the knowledge corpus into a single brain.html.

Stdlib-only. Scope: docs/, domains/, experts/, inbox/, README.md, AGENTS.md.
Markdown stays verbatim in the payload (so "copy as markdown" returns the
original); the client rewrites relative .md links to hash routes at render
time. This script collects content + metadata, computes the backlink graph,
warns about dead links, and injects everything into template.html.

Usage: python3 tools/brain/build.py [--out PATH]
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

SCOPE_DIRS = ["docs", "domains", "experts", "inbox"]
SCOPE_FILES = ["README.md", "AGENTS.md"]
VENDOR = ["marked.min.js", "highlight.min.js", "highlight-dart.min.js", "minisearch.min.js"]

TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.M)
UPDATED_RE = re.compile(r"^\*\*Last updated:\*\*\s*(.+?)\s*$", re.M)
# any relative link: [text](target) or [text](target#anchor)
LINK_RE = re.compile(r"\]\(((?!https?://|mailto:|#|/)[^)\s]+?)(#[^)\s]*)?\)")


def resolve_rel(src_rel, target):
    """Resolve a relative link against the source file's directory (posix, no fs)."""
    parts = []
    for part in (Path(src_rel).parent / target).as_posix().split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part not in ("", "."):
            parts.append(part)
    return "/".join(parts)


def collect_paths():
    paths = []
    for d in SCOPE_DIRS:
        base = ROOT / d
        if base.is_dir():
            paths.extend(p for p in base.rglob("*.md") if not any(part.startswith(".") for part in p.parts))
    for f in SCOPE_FILES:
        p = ROOT / f
        if p.is_file():
            paths.append(p)
    return sorted(set(paths))


def git_dates():
    """Bulk last-modified dates: first occurrence of a path in git log = newest commit touching it."""
    dates = {}
    try:
        out = subprocess.run(
            ["git", "log", "--name-only", "--format=%cI", "--", "*.md"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return dates
    current = None
    for line in out.splitlines():
        if not line:
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}T", line):
            current = line[:10]
        elif current and line.endswith(".md") and line not in dates:
            dates[line] = current
    return dates


def git_hash():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "?"


def main():
    out_path = ROOT / "brain.html"
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])

    paths = collect_paths()
    corpus = {p.relative_to(ROOT).as_posix() for p in paths}
    dates = git_dates()
    warnings = []

    docs, backlinks, on_disk = [], {}, set()
    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        md = p.read_text(encoding="utf-8", errors="replace")
        title_m = TITLE_RE.search(md)
        status_m = STATUS_RE.search(md)
        updated_m = UPDATED_RE.search(md)
        for m in LINK_RE.finditer(md):
            resolved = resolve_rel(rel, m.group(1))
            if resolved in corpus:
                if resolved != rel:
                    backlinks.setdefault(resolved, [])
                    if rel not in backlinks[resolved]:
                        backlinks[resolved].append(rel)
            elif (ROOT / resolved).exists():
                on_disk.add(resolved)  # exists in repo but outside brain scope
            else:
                warnings.append(f"{rel}: dead link -> {m.group(1)}{m.group(2) or ''}")
        docs.append({
            "path": rel,
            "title": (title_m.group(1) if title_m else Path(rel).stem),
            "status": status_m.group(1).replace("**", "").replace("`", "") if status_m else None,
            "updatedHeader": updated_m.group(1) if updated_m else None,
            "modified": dates.get(rel) or datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d"),
            "md": md,
        })

    payload = {
        "built": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        "hash": git_hash(),
        "root": str(ROOT),
        "docCount": len(docs),
        "docs": docs,
        "backlinks": backlinks,
        "onDisk": sorted(on_disk),
    }

    template = (HERE / "template.html").read_text(encoding="utf-8")
    vendor_js = "\n;\n".join((HERE / "vendor" / v).read_text(encoding="utf-8") for v in VENDOR)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    html = (template
            .replace("/*__VENDOR__*/", vendor_js)
            .replace("__PAYLOAD__", payload_json))
    out_path.write_text(html, encoding="utf-8")

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"brain.html: {len(docs)} docs, {size_mb:.1f} MB -> {out_path}")
    if warnings:
        print(f"\n{len(warnings)} dead link(s):")
        for w in warnings:
            print(f"  ! {w}")


if __name__ == "__main__":
    main()
