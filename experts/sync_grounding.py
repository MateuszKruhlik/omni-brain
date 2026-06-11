#!/usr/bin/env python3
"""Sync the shared GROUNDING RULES block into expert prompts.

Source of truth: experts/prompts/_shared/grounding_rules.md (template with
{{PLACEHOLDERS}}). Per-expert citation examples live in EXPERTS below.

Why this exists: the grounding block is duplicated across every RAG-backed
expert prompt (prompts must stay standalone — IDEs load them as-is). Copies
drift over time, and a single drifted example with a fictional book_id teaches
the model to fabricate citations. One template + this script keeps all copies
identical while preserving per-expert examples.

Usage:
    python3 experts/sync_grounding.py --check   # report drift (exit 1 if any)
    python3 experts/sync_grounding.py --write   # rewrite blocks in prompts

The synced block in each prompt is wrapped in markers:
    <!-- SHARED:GROUNDING:BEGIN ... -->  /  <!-- SHARED:GROUNDING:END -->
On first run (no markers yet), the script finds a legacy
"GROUNDING RULES (MANDATORY)" heading and replaces that section.
Stdlib only — runs with system python3, no venv needed.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # experts/
PROMPTS = ROOT / "prompts"
TEMPLATE = PROMPTS / "_shared" / "grounding_rules.md"

MARKER_BEGIN = ("<!-- SHARED:GROUNDING:BEGIN — auto-synced; edit "
                "experts/prompts/_shared/grounding_rules.md, then run: "
                "python3 experts/sync_grounding.py --write -->")
MARKER_END = "<!-- SHARED:GROUNDING:END -->"

# Register every RAG-backed expert here when you create it
# (see docs/runbooks/NEW_EXPERT.md, Phase 4.2).
#
# RAG examples MUST use real book_ids from rag/manifests/library_manifest.md
# (or real video lesson ids from your Chroma index) — a fictional example
# anchors the model toward fabricating citations.
EXPERTS: dict[str, dict] = {
    # "my_expert.md": {
    #     "rag": ["[dom_01] Some Real Book — p.45 (score 0.59)",
    #             "[dom_02] Another Real Book — ch.3, seg.2 (score 0.52)"],
    #     "gk": ["Some framework (Author)", "Another concept (Author)"],
    # },
}

# Legacy section: heading until the next top-column horizontal rule.
LEGACY_RE = re.compile(
    r"^(?P<level>#{2,3}) GROUNDING RULES \(MANDATORY\)\n(?P<body>.*?)(?=^---$)",
    re.DOTALL | re.MULTILINE,
)
MARKED_RE = re.compile(
    re.escape(MARKER_BEGIN) + r"\n(?P<inner>.*?)" + re.escape(MARKER_END) + r"\n?",
    re.DOTALL,
)


def render(cfg: dict, level: str) -> str:
    """Render the canonical block for one expert at the given heading level."""
    body = TEMPLATE.read_text(encoding="utf-8")
    body = re.sub(r"<!--.*?-->\n", "", body, count=1, flags=re.DOTALL)  # strip template header comment
    body = (body
            .replace("{{RAG_EXAMPLE_1}}", cfg["rag"][0])
            .replace("{{RAG_EXAMPLE_2}}", cfg["rag"][1])
            .replace("{{GK_EXAMPLE_1}}", cfg["gk"][0])
            .replace("{{GK_EXAMPLE_2}}", cfg["gk"][1]))
    return (f"{MARKER_BEGIN}\n"
            f"{level} GROUNDING RULES (MANDATORY)\n"
            f"{body.strip()}\n"
            f"{MARKER_END}\n")


def sync_file(path: Path, cfg: dict, write: bool) -> str | None:
    """Returns drift description or None if in sync. Writes when asked."""
    text = path.read_text(encoding="utf-8")

    m = MARKED_RE.search(text)
    if m:
        level_m = re.search(r"^(#{2,3}) GROUNDING RULES", m.group("inner"), re.MULTILINE)
        level = level_m.group(1) if level_m else "###"
        expected = render(cfg, level)
        current = text[m.start():m.end()]
        if current == expected:
            return None
        if write:
            path.write_text(text[:m.start()] + expected + text[m.end():], encoding="utf-8")
        return "drift in marked block"

    lm = LEGACY_RE.search(text)
    if lm:
        expected = render(cfg, lm.group("level"))
        if write:
            path.write_text(text[:lm.start()] + expected + text[lm.end():], encoding="utf-8")
        return "legacy block (no markers yet)"

    return "GROUNDING RULES section not found!"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift, exit 1 if any")
    mode.add_argument("--write", action="store_true", help="rewrite blocks from the template")
    args = ap.parse_args()

    if not EXPERTS:
        print("No experts registered yet — add entries to EXPERTS in this script "
              "when you create RAG-backed experts (docs/runbooks/NEW_EXPERT.md).")
        return 0

    drift = 0
    for name, cfg in EXPERTS.items():
        path = PROMPTS / name
        if not path.exists():
            print(f"  MISSING  {name}")
            drift += 1
            continue
        result = sync_file(path, cfg, write=args.write)
        if result is None:
            print(f"  OK       {name}")
        else:
            status = "SYNCED" if args.write else "DRIFT"
            print(f"  {status:<8} {name} — {result}")
            drift += 1

    if args.check and drift:
        print(f"\n{drift} file(s) out of sync. Run: python3 experts/sync_grounding.py --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
