#!/usr/bin/env python3
"""
RAG Query Tool — Multi-stage fallback retrieval for unified_library.

Usage:
    # CLI mode (default) — short excerpts for human scanning
    python rag/ingest/query.py "How to validate assumptions?"
    python rag/ingest/query.py "marketplace listing tips" --domain marketplace

    # Expert mode — full text, diversified, multi-stage fallback
    python rag/ingest/query.py "listing optimization" --mode expert --domain marketplace

    # Debug mode — show fallback stages and confidence signals
    python rag/ingest/query.py "title + tags best practices" --mode expert --debug
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = ROOT_DIR / "rag" / "indexes" / "chroma"
COLLECTION_NAME = "unified_library"
EMBEDDING_MODELS = {
    "openai": "text-embedding-3-large",
    "voyage": "voyage-4-large",
}

# CLI mode defaults
DEFAULT_N_RESULTS = 5
MAX_EXCERPT_LENGTH = 200

# Expert mode defaults
EXPERT_TOPK_CONTEXT = 7       # final chunks delivered to expert
EXPERT_MAX_PER_BOOK = 2       # max chunks from same book
EXPERT_CHUNK_MAX_CHARS = 3000 # max chars per chunk in expert output
MIN_BOOKS_IN_TOPK = 3         # desired book diversity

# Fallback fetch sizes
FETCH_N_STAGE0 = 20
FETCH_N_STAGE1 = 30
FETCH_N_STAGE1_EMERGENCY = 40
FETCH_N_STAGE2_PER_SUBQUERY = 15

# Confidence thresholds (calibrated for Voyage voyage-4-large, 2026-02-02)
# Voyage cosine similarity scores are lower than OpenAI (~0.35-0.64 range)
THRESHOLD_TOP1_SCORE = 0.45
THRESHOLD_AVG5_SCORE = 0.42
THRESHOLD_FLATNESS = 0.015    # gap between top1 and top5
# These are starting values — recalibrate after collecting query logs.

MIN_RESULTS_BEFORE_TAG_FALLBACK = 3

# ---------------------------------------------------------------------------
# Intent Packs — deterministic multi-query for broad/multi-intent queries
# ---------------------------------------------------------------------------
# Add intent packs for your domains here (see docs/runbooks/NEW_EXPERT.md)
# Each pack = one query type. Keywords: mix of languages. Subquery: English phrases.
INTENT_PACKS = {
    # Example intent packs
    "example_intent_1": {
        "keywords": ["example1", "kw2", "kw3"],
        "subquery": "english phrases for example intent 1",
    },
    "example_intent_2": {
        "keywords": ["example2", "kw4", "kw5"],
        "subquery": "english phrases for example intent 2",
    },
}

QUERY_LOG_PATH = ROOT_DIR / "rag" / "logs" / "query_log.jsonl"


def log_query(entry: dict):
    """Append a query log entry as JSONL."""
    QUERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUERY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_collection():
    """Get the ChromaDB collection."""
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_query(text: str) -> list[float]:
    """Embed a query string using the configured provider."""
    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage")
    model = EMBEDDING_MODELS[provider]

    if provider == "voyage":
        import voyageai
        client = voyageai.Client()
        result = client.embed([text], model=model, input_type="query")
        return result.embeddings[0]

    from openai import OpenAI
    client = OpenAI()
    response = client.embeddings.create(model=model, input=[text])
    return response.data[0].embedding


def build_where_filter(domain: str | None, tags: list[str] | None) -> dict | None:
    """Build ChromaDB where filter."""
    conditions = []

    if domain:
        conditions.append({"domain": {"$eq": domain}})

    if tags:
        tag_conditions = [{"tags": {"$contains": tag}} for tag in tags]
        if len(tag_conditions) == 1:
            conditions.append(tag_conditions[0])
        else:
            conditions.append({"$or": tag_conditions})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


# ---------------------------------------------------------------------------
# Confidence assessment
# ---------------------------------------------------------------------------
def assess_confidence(
    scores: list[float],
    metas: list[dict],
    topk: int = EXPERT_TOPK_CONTEXT,
) -> dict:
    """Assess retrieval confidence from scores and metadata."""
    if not scores:
        return {"low_confidence": True, "reasons": ["no_results"], "top1": 0, "avg5": 0, "gap": 0, "unique_books": 0}

    top_scores = scores[:topk]
    top1 = top_scores[0]
    avg5 = sum(top_scores[:5]) / min(5, len(top_scores))
    gap = top_scores[0] - top_scores[min(4, len(top_scores) - 1)] if len(top_scores) >= 2 else 0
    unique_books = len(set(m.get("book_id", "?") for m in metas[:topk]))

    reasons = []
    if top1 < THRESHOLD_TOP1_SCORE:
        reasons.append(f"top1_low ({top1:.3f} < {THRESHOLD_TOP1_SCORE})")
    if avg5 < THRESHOLD_AVG5_SCORE:
        reasons.append(f"avg5_low ({avg5:.3f} < {THRESHOLD_AVG5_SCORE})")
    if gap < THRESHOLD_FLATNESS and top1 < 0.55:
        reasons.append(f"flat ({gap:.3f} < {THRESHOLD_FLATNESS})")
    if unique_books < MIN_BOOKS_IN_TOPK:
        reasons.append(f"low_diversity ({unique_books} books < {MIN_BOOKS_IN_TOPK})")

    return {
        "low_confidence": len(reasons) > 0,
        "reasons": reasons,
        "top1": top1,
        "avg5": avg5,
        "gap": gap,
        "unique_books": unique_books,
    }


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------
def detect_intents(query: str) -> list[str]:
    """Match query against intent packs. Returns list of matched pack names."""
    query_lower = query.lower()
    matched = []
    for pack_name, pack in INTENT_PACKS.items():
        for kw in pack["keywords"]:
            if kw.lower() in query_lower:
                matched.append(pack_name)
                break
    return matched


# ---------------------------------------------------------------------------
# Retrieval helpers
# ---------------------------------------------------------------------------
def _retrieve(
    collection,
    query_embedding: list[float],
    where_filter: dict | None,
    fetch_n: int,
) -> tuple[list[str], list[dict], list[float]]:
    """Run a single ChromaDB query, return (docs, metas, scores)."""
    count = collection.count()
    fetch_n = min(fetch_n, count)
    if fetch_n == 0:
        return [], [], []

    results = collection.query(
        query_embeddings=[query_embedding],
        where=where_filter,
        n_results=fetch_n,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    scores = [1 - d for d in (results["distances"][0] if results["distances"] else [])]

    return docs, metas, scores


def merge_results(
    *result_sets: tuple[list[str], list[dict], list[float]],
) -> tuple[list[str], list[dict], list[float]]:
    """Merge multiple result sets, deduplicate by chunk ID, sort by score desc."""
    seen_ids: dict[str, int] = {}
    all_docs = []
    all_metas = []
    all_scores = []

    for docs, metas, scores in result_sets:
        for doc, meta, score in zip(docs, metas, scores):
            chunk_id = f"{meta.get('book_id', '')}_{meta.get('page', '')}_{meta.get('location', '')}"
            if chunk_id in seen_ids:
                # Keep higher score
                idx = seen_ids[chunk_id]
                if score > all_scores[idx]:
                    all_docs[idx] = doc
                    all_metas[idx] = meta
                    all_scores[idx] = score
            else:
                seen_ids[chunk_id] = len(all_docs)
                all_docs.append(doc)
                all_metas.append(meta)
                all_scores.append(score)

    # Sort by score descending
    indices = sorted(range(len(all_scores)), key=lambda i: all_scores[i], reverse=True)
    return (
        [all_docs[i] for i in indices],
        [all_metas[i] for i in indices],
        [all_scores[i] for i in indices],
    )


def diversify_results(
    docs: list[str],
    metas: list[dict],
    scores: list[float],
    max_per_book: int = EXPERT_MAX_PER_BOOK,
    select_n: int = EXPERT_TOPK_CONTEXT,
) -> tuple[list[str], list[dict], list[float]]:
    """Select top results with diversity constraint: max N chunks per book."""
    book_counts: dict[str, int] = defaultdict(int)
    selected_docs = []
    selected_metas = []
    selected_scores = []

    for doc, meta, score in zip(docs, metas, scores):
        if len(selected_docs) >= select_n:
            break
        bid = meta.get("book_id", "unknown")
        if book_counts[bid] >= max_per_book:
            continue
        book_counts[bid] += 1
        selected_docs.append(doc)
        selected_metas.append(meta)
        selected_scores.append(score)

    return selected_docs, selected_metas, selected_scores


# ---------------------------------------------------------------------------
# Multi-stage expert retrieval
# ---------------------------------------------------------------------------
def run_expert_query(
    text: str,
    collection,
    where_filter: dict | None,
    debug: bool = False,
    topk: int = EXPERT_TOPK_CONTEXT,
) -> tuple[list[str], list[dict], list[float], list[str]]:
    """
    Multi-stage retrieval pipeline for expert mode.

    Stage 0: Baseline (fetchN=20)
    Stage 1: Embedding boost (fetchN=30, then 40 if still low)
    Stage 2: Intent pack sub-queries (deterministic)

    Returns (docs, metas, scores, stage_log).
    """
    stage_log = []

    # --- Stage 0: Baseline ---
    query_emb = embed_query(text)
    docs0, metas0, scores0 = _retrieve(collection, query_emb, where_filter, FETCH_N_STAGE0)
    docs_d, metas_d, scores_d = diversify_results(docs0, metas0, scores0, select_n=topk)
    conf = assess_confidence(scores_d, metas_d, topk=topk)

    stage_log.append(f"Stage 0: fetchN={FETCH_N_STAGE0}, top1={conf['top1']:.3f}, avg5={conf['avg5']:.3f}, "
                     f"gap={conf['gap']:.3f}, books={conf['unique_books']}")

    # Check multi-intent (independent trigger)
    matched_intents = detect_intents(text)
    multi_intent = len(matched_intents) >= 2

    if multi_intent:
        stage_log.append(f"Multi-intent detected: {matched_intents}")

    if not conf["low_confidence"] and not multi_intent:
        stage_log.append("Stage 0 sufficient — no fallback needed.")
        if debug:
            for line in stage_log:
                print(f"  [DEBUG] {line}")
        return docs_d, metas_d, scores_d, stage_log

    stage_log.append(f"Low confidence: {conf['reasons']}" if conf["low_confidence"] else "Triggered by multi-intent only")

    # --- Stage 1: Embedding Boost ---
    docs1, metas1, scores1 = _retrieve(collection, query_emb, where_filter, FETCH_N_STAGE1)
    merged = merge_results((docs0, metas0, scores0), (docs1, metas1, scores1))
    docs_d, metas_d, scores_d = diversify_results(*merged, select_n=topk)
    conf = assess_confidence(scores_d, metas_d, topk=topk)

    stage_log.append(f"Stage 1: fetchN={FETCH_N_STAGE1}, top1={conf['top1']:.3f}, "
                     f"books={conf['unique_books']}")

    if not conf["low_confidence"] and not multi_intent:
        stage_log.append("Stage 1 sufficient.")
        if debug:
            for line in stage_log:
                print(f"  [DEBUG] {line}")
        return docs_d, metas_d, scores_d, stage_log

    # Stage 1b: Emergency boost
    if conf["low_confidence"]:
        docs1b, metas1b, scores1b = _retrieve(collection, query_emb, where_filter, FETCH_N_STAGE1_EMERGENCY)
        merged = merge_results(
            (docs_d, metas_d, scores_d),
            (docs1b, metas1b, scores1b),
        )
        docs_d, metas_d, scores_d = diversify_results(*merged, select_n=topk)
        conf = assess_confidence(scores_d, metas_d, topk=topk)

        stage_log.append(f"Stage 1b: fetchN={FETCH_N_STAGE1_EMERGENCY}, top1={conf['top1']:.3f}, "
                         f"books={conf['unique_books']}")

        if not conf["low_confidence"] and not multi_intent:
            stage_log.append("Stage 1b sufficient.")
            if debug:
                for line in stage_log:
                    print(f"  [DEBUG] {line}")
            return docs_d, metas_d, scores_d, stage_log

    # --- Stage 2: Intent Pack Sub-queries ---
    if not matched_intents:
        # If no intents matched but still low confidence, skip to final output
        stage_log.append("Stage 2 skipped — no intent packs matched.")
        if debug:
            for line in stage_log:
                print(f"  [DEBUG] {line}")
        return docs_d, metas_d, scores_d, stage_log

    subquery_results = []
    for intent_name in matched_intents[:3]:  # max 3 packs
        subquery = INTENT_PACKS[intent_name]["subquery"]
        sub_emb = embed_query(subquery)
        sub_docs, sub_metas, sub_scores = _retrieve(
            collection, sub_emb, where_filter, FETCH_N_STAGE2_PER_SUBQUERY
        )
        subquery_results.append((sub_docs, sub_metas, sub_scores))
        stage_log.append(f"Stage 2: pack={intent_name}, subquery='{subquery[:50]}...', results={len(sub_docs)}")

    # Merge all: baseline + boost + subqueries
    all_result_sets = [(docs_d, metas_d, scores_d)] + subquery_results
    merged = merge_results(*all_result_sets)
    docs_d, metas_d, scores_d = diversify_results(*merged, select_n=topk)
    conf = assess_confidence(scores_d, metas_d, topk=topk)

    stage_log.append(f"Stage 2 final: top1={conf['top1']:.3f}, books={conf['unique_books']}")

    if debug:
        for line in stage_log:
            print(f"  [DEBUG] {line}")

    return docs_d, metas_d, scores_d, stage_log


# ---------------------------------------------------------------------------
# CLI mode formatting
# ---------------------------------------------------------------------------
def format_result_cli(doc: str, meta: dict, score: float) -> str:
    """Format a single search result for CLI display (short excerpt)."""
    excerpt = doc[:MAX_EXCERPT_LENGTH].replace("\n", " ")
    if len(doc) > MAX_EXCERPT_LENGTH:
        excerpt += "..."

    title = meta.get("title", "Unknown")
    page = meta.get("page", "?")
    book_id = meta.get("book_id", "?")
    source = meta.get("source_path", "")
    author = meta.get("author", "")
    author_str = f" by {author}" if author else ""

    location = meta.get("location", "")
    cite = f"({location})" if location else f"(p. {page})"

    lines = [
        f"[Score: {score:.2f}] {title}{author_str} {cite} [book_id: {book_id}]",
        f"  Source: {source}",
        f'  "{excerpt}"',
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Expert mode formatting
# ---------------------------------------------------------------------------
def format_result_expert(doc: str, meta: dict, score: float, index: int) -> str:
    """Format a single search result for expert/LLM consumption (full text)."""
    title = meta.get("title", "Unknown")
    author = meta.get("author", "")
    book_id = meta.get("book_id", "?")

    location = meta.get("location", "")
    page = meta.get("page", "?")
    cite = f"({location})" if location else f"(p. {page})"

    # Trim chunk text to limit
    text = doc[:EXPERT_CHUNK_MAX_CHARS]
    if len(doc) > EXPERT_CHUNK_MAX_CHARS:
        for sep in (". ", ".\n", ".\r"):
            last = text.rfind(sep)
            if last > EXPERT_CHUNK_MAX_CHARS - 300:
                text = text[: last + 1]
                break
        text += " [...]"

    author_str = f" by {author}" if author else ""
    header = f"--- [{index}] {title}{author_str} {cite} [score: {score:.2f}] [book_id: {book_id}] ---"
    return f"{header}\n{text}"


# ---------------------------------------------------------------------------
# Core query logic
# ---------------------------------------------------------------------------
def run_query(
    text: str,
    domain: str | None = None,
    tags: list[str] | None = None,
    n_results: int = DEFAULT_N_RESULTS,
    mode: str = "cli",
    debug: bool = False,
    topk: int = EXPERT_TOPK_CONTEXT,
):
    """Run a query against the collection."""
    collection = get_collection()

    count = collection.count()
    if count == 0:
        print("Collection is empty. Run ingest.py first.")
        return

    where_filter = build_where_filter(domain, tags)

    if mode == "expert":
        docs, metas, scores, stage_log = run_expert_query(
            text, collection, where_filter, debug=debug, topk=topk,
        )

        if not docs:
            print("No results found.")
            return

        # Check partial coverage
        unique_books = len(set(m.get("book_id", "?") for m in metas))
        partial_coverage = unique_books < MIN_BOOKS_IN_TOPK

        books_used = sorted(set(m.get("book_id", "?") for m in metas))
        stages_used = len([l for l in stage_log if l.startswith("Stage") and "sufficient" not in l and "skipped" not in l])

        print(f"=== RAG Evidence Pack: {len(docs)} chunks from {len(books_used)} books ===")
        print(f"Query: \"{text}\"")
        print(f"Books: {', '.join(books_used)}")
        print(f"Stages used: {stages_used}")
        if partial_coverage:
            print(f"[NOTICE] Evidence is concentrated in {unique_books} source(s) — treating as partial coverage.")
        print()

        for i, (doc, meta, score) in enumerate(zip(docs, metas, scores), start=1):
            print(format_result_expert(doc, meta, score, i))
            print()

        # Log query for calibration
        matched_intents = detect_intents(text)
        log_query({
            "ts": datetime.now(timezone.utc).isoformat(),
            "query": text,
            "domain": domain,
            "mode": "expert",
            "top1": round(scores[0], 4) if scores else 0,
            "avg5": round(sum(scores[:5]) / min(5, len(scores)), 4) if scores else 0,
            "gap_1_5": round(scores[0] - scores[min(4, len(scores) - 1)], 4) if len(scores) >= 2 else 0,
            "books_count": len(books_used),
            "books": books_used,
            "stages_used": stages_used,
            "intents_matched": matched_intents,
            "partial_coverage": partial_coverage,
            "stage_log": stage_log,
        })
    else:
        # CLI mode — simple single-stage retrieval
        query_embedding = embed_query(text)
        fetch_n = min(n_results, count)
        docs, metas, scores = _retrieve(collection, query_embedding, where_filter, fetch_n)

        # Tag fallback
        if len(docs) < MIN_RESULTS_BEFORE_TAG_FALLBACK and tags and domain:
            print(f"(Fallback: relaxing tag filter, querying domain={domain} only)\n")
            fallback_filter = build_where_filter(domain, None)
            docs, metas, scores = _retrieve(collection, query_embedding, fallback_filter, fetch_n)

        if not docs:
            print("No results found.")
            return

        print(f"=== {len(docs)} result(s) ===\n")
        for doc, meta, score in zip(docs, metas, scores):
            print(format_result_cli(doc, meta, score))
            print()


def main():
    parser = argparse.ArgumentParser(description="RAG Query Tool")
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--domain", default=None, help="Filter by domain (e.g., marketplace)")
    parser.add_argument("--tags", default=None, help="Comma-separated tags to filter by")
    parser.add_argument("-n", type=int, default=DEFAULT_N_RESULTS, help="Number of results (CLI mode)")
    parser.add_argument(
        "--mode",
        choices=["cli", "expert"],
        default="cli",
        help="Output mode: 'cli' for short excerpts, 'expert' for full text with diversification",
    )
    parser.add_argument("--debug", action="store_true", help="Show fallback stage debug info")
    parser.add_argument("--topk", type=int, default=EXPERT_TOPK_CONTEXT, help=f"Number of chunks to return in expert mode (default: {EXPERT_TOPK_CONTEXT})")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")

    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage")
    key_var = "VOYAGE_API_KEY" if provider == "voyage" else "OPENAI_API_KEY"
    if not os.environ.get(key_var):
        print(f"ERROR: {key_var} not set in .env")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
    run_query(args.query, domain=args.domain, tags=tags, n_results=args.n, mode=args.mode, debug=args.debug, topk=args.topk)


if __name__ == "__main__":
    main()
