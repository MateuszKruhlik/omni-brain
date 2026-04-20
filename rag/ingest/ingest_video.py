#!/usr/bin/env python3
"""
RAG Video Ingestion — Embed video chunks to ChromaDB.

Reads JSONL chunk files from video_pipeline and embeds them
into the unified_library collection alongside PDF/EPUB content.

Usage:
    python rag/ingest/ingest_video.py --course example_course
    python rag/ingest/ingest_video.py --course example_course --dry-run
    python rag/ingest/ingest_video.py --course example_course --force
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]  # <repo_root>
VIDEO_PIPELINE_DIR = ROOT_DIR / "video_pipeline"
CHROMA_DIR = ROOT_DIR / "rag" / "indexes" / "chroma"

COLLECTION_NAME = "unified_library"

# Embedding config
EMBEDDING_MODELS = {
    "openai": "text-embedding-3-large",
    "voyage": "voyage-4-large",
}

MAX_EMBED_CHARS = 28000  # ~7000 tokens

# Video-specific settings
VIDEO_DOMAIN = "video"  # Default domain for video content
VIDEO_ID_PREFIX = "vid"  # Prefix for video book_ids

INDEX_VERSION = 1
PARSER_VERSION = "whisperx_v1"
CLEANING_VERSION = "safe_sentence_v1"


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
def _truncate_for_embedding(text: str) -> str:
    """Truncate text to stay within embedding model token limit."""
    if len(text) <= MAX_EMBED_CHARS:
        return text
    truncated = text[:MAX_EMBED_CHARS]
    last_space = truncated.rfind(" ")
    if last_space > MAX_EMBED_CHARS - 200:
        truncated = truncated[:last_space]
    return truncated


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings from configured provider in batches."""
    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage")
    model = EMBEDDING_MODELS[provider]
    safe_texts = [_truncate_for_embedding(t) for t in texts]

    if provider == "voyage":
        return _embed_voyage(safe_texts, model)
    return _embed_openai(safe_texts, model)


def _embed_openai(texts: list[str], model: str) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI()
    all_embeddings = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([d.embedding for d in response.data])

    return all_embeddings


def _embed_voyage(texts: list[str], model: str) -> list[list[float]]:
    import voyageai

    client = voyageai.Client()
    all_embeddings = []
    batch_size = 32

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.embed(batch, model=model, input_type="document")
        all_embeddings.extend(result.embeddings)

    return all_embeddings


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
def get_collection():
    """Get or create the ChromaDB collection."""
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def get_existing_video_ids(collection, course_id: str) -> set[str]:
    """Get IDs of already indexed chunks for a course."""
    # Query by metadata to find existing video chunks
    try:
        results = collection.get(
            where={"course_id": {"$eq": course_id}},
            include=["metadatas"],
        )
        return set(results["ids"]) if results["ids"] else set()
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Chunk Loading
# ---------------------------------------------------------------------------
def load_chunks(course_dir: Path) -> list[dict]:
    """Load all chunks from a course's chunks directory."""
    chunks_dir = course_dir / "chunks"
    if not chunks_dir.exists():
        return []

    all_chunks = []
    for chunk_file in sorted(chunks_dir.glob("*.chunks.jsonl")):
        with open(chunk_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line)
                    all_chunks.append(chunk)

    return all_chunks


def generate_video_book_id(course_id: str, lesson_id: str) -> str:
    """Generate a book_id for a video lesson."""
    # Use course slug + lesson number as book_id
    # e.g., vid_exa_01 for example_course lesson 01
    course_short = course_id[:3] if len(course_id) > 3 else course_id
    lesson_num = lesson_id.split("_")[0] if "_" in lesson_id else lesson_id[:2]
    return f"{VIDEO_ID_PREFIX}_{course_short}_{lesson_num}"


# ---------------------------------------------------------------------------
# Ingestion Logic
# ---------------------------------------------------------------------------
def ingest_video_chunks(
    course_id: str,
    chunks: list[dict],
    collection,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Ingest video chunks into ChromaDB. Returns number of chunks indexed."""

    if not chunks:
        print(f"  [SKIP] No chunks found for {course_id}")
        return 0

    # Check existing chunks
    existing_ids = set() if force else get_existing_video_ids(collection, course_id)

    # Filter out already indexed chunks
    new_chunks = []
    for chunk in chunks:
        chunk_id = f"{course_id}_{chunk['lesson_id']}_{chunk['chunk_id']}"
        if chunk_id not in existing_ids:
            new_chunks.append((chunk_id, chunk))

    if not new_chunks:
        print(f"  [SKIP] All {len(chunks)} chunks already indexed for {course_id}")
        return 0

    print(f"  [PROCESS] {len(new_chunks)} new chunks to index (of {len(chunks)} total)")

    if dry_run:
        print(f"  [DRY-RUN] Would index {len(new_chunks)} chunks")
        return len(new_chunks)

    # Prepare data for ChromaDB
    ids = []
    documents = []
    metadatas = []

    for chunk_id, chunk in new_chunks:
        text = chunk.get("text_clean") or chunk.get("text", "")
        if not text.strip():
            continue

        lesson_id = chunk.get("lesson_id", "unknown")
        book_id = generate_video_book_id(course_id, lesson_id)

        # Build tags string
        tags = chunk.get("tags", [])
        if VIDEO_DOMAIN not in tags:
            tags = [VIDEO_DOMAIN] + tags
        tags_str = ",".join(tags)

        metadata = {
            "book_id": book_id,
            "title": chunk.get("lesson_title", lesson_id),
            "author": chunk.get("course_title", course_id),  # Derive from course metadata
            "year": datetime.now(timezone.utc).year,
            "edition": "",
            "domain": VIDEO_DOMAIN,
            "tags": tags_str,
            "page": 0,  # Videos don't have pages
            "location": chunk.get("start_time_hms", "00:00:00"),  # Use timestamp as location
            "source_path": chunk.get("source_path", ""),
            "source_type": "video",
            "course_id": course_id,
            "lesson_id": lesson_id,
            "module": chunk.get("module", ""),
            "submodule": chunk.get("submodule", ""),
            "start_time": chunk.get("start_time", 0),
            "end_time": chunk.get("end_time", 0),
            "duration_sec": chunk.get("duration_sec", 0),
            "index_version": INDEX_VERSION,
            "parser_version": PARSER_VERSION,
            "cleaning_version": CLEANING_VERSION,
            "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        }

        ids.append(chunk_id)
        documents.append(text)
        metadatas.append(metadata)

    if not documents:
        print(f"  [WARN] No valid text in chunks")
        return 0

    # Get embeddings
    print(f"  Generating embeddings for {len(documents)} chunks...")
    embeddings = get_embeddings(documents)

    # Upsert to ChromaDB
    print(f"  Upserting {len(ids)} records to ChromaDB...")
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(ids)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="RAG Video Ingestion")
    parser.add_argument("--course", required=True, help="Course slug (folder name in video_pipeline/)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    parser.add_argument("--force", action="store_true", help="Re-index all chunks regardless of existing")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")

    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage")
    if provider not in EMBEDDING_MODELS:
        print(f"ERROR: Unknown EMBEDDING_PROVIDER={provider}. Use 'openai' or 'voyage'.")
        sys.exit(1)

    key_var = "VOYAGE_API_KEY" if provider == "voyage" else "OPENAI_API_KEY"
    if not args.dry_run and not os.environ.get(key_var):
        print(f"ERROR: {key_var} not set in .env. Use --dry-run to preview.")
        sys.exit(1)

    course_dir = VIDEO_PIPELINE_DIR / args.course
    if not course_dir.exists():
        print(f"ERROR: Course directory not found: {course_dir}")
        sys.exit(1)

    print("=== RAG Video Ingestion ===")
    print(f"  Course: {args.course}")
    print(f"  Course dir: {course_dir}")
    print(f"  ChromaDB: {CHROMA_DIR}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Force: {args.force}")
    print()

    # Load chunks
    chunks = load_chunks(course_dir)
    print(f"Found {len(chunks)} chunk(s) in {args.course}\n")

    if not chunks:
        print("No chunks found. Run chunking pipeline first.")
        return

    # Get collection
    collection = None if args.dry_run else get_collection()

    # Ingest
    indexed = ingest_video_chunks(
        course_id=args.course,
        chunks=chunks,
        collection=collection,
        dry_run=args.dry_run,
        force=args.force,
    )

    print(f"\n{'Would index' if args.dry_run else 'Indexed'}: {indexed} chunk(s)")

    if not args.dry_run and indexed > 0:
        # Show collection stats
        count = collection.count()
        print(f"Total chunks in collection: {count}")


if __name__ == "__main__":
    main()
