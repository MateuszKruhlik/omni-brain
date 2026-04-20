#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--map_dir",
        default="knowledge_map",
        help="Directory with per-lesson *.map.json files",
    )
    parser.add_argument(
        "--output_json",
        default="knowledge_map/global.map.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--output_md",
        default="knowledge_map/global.map.md",
        help="Output MD path",
    )
    parser.add_argument(
        "--top_edges",
        type=int,
        default=120,
        help="Number of top edges to include",
    )
    args = parser.parse_args()

    map_dir = Path(args.map_dir)
    if not map_dir.exists():
        raise SystemExit(f"Missing map_dir: {map_dir}")

    edge_counts = Counter()
    node_lessons = defaultdict(set)
    total_files = 0

    for path in sorted(map_dir.glob("lesson_*.map.json")):
        total_files += 1
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        edges = data.get("edges", [])
        lesson_id = path.stem.replace(".map", "").replace("lesson_", "")
        for e in edges:
            a = e.get("source")
            b = e.get("target")
            if not a or not b:
                continue
            key = tuple(sorted([a, b]))
            edge_counts[key] += int(e.get("weight", 1))
            node_lessons[a].add(lesson_id)
            node_lessons[b].add(lesson_id)

    top_edges = edge_counts.most_common(args.top_edges)
    nodes = []
    for node, lessons in node_lessons.items():
        nodes.append(
            {
                "id": node,
                "lesson_count": len(lessons),
                "lessons": sorted(lessons),
            }
        )
    nodes = sorted(nodes, key=lambda x: (-x["lesson_count"], x["id"]))

    edges_out = [
        {"source": a, "target": b, "weight": int(w), "relation": "co_occurs"}
        for (a, b), w in top_edges
    ]

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "total_lesson_maps": total_files,
                "nodes": nodes,
                "edges": edges_out,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Global Knowledge Map (auto, heuristic)\n\n")
        f.write(f"Lesson maps merged: {total_files}\n\n")
        f.write("Top edges:\n")
        for e in edges_out:
            f.write(f"- {e['source']} ↔ {e['target']} (weight={e['weight']})\n")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
