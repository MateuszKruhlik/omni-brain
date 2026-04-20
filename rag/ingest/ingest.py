#!/usr/bin/env python3
"""
RAG Ingestion Engine — PDF (page-level) & EPUB (chapter+segment) indexing to ChromaDB.

Usage:
    python rag/ingest/ingest.py                # Normal run
    python rag/ingest/ingest.py --dry-run      # Preview without writing
    python rag/ingest/ingest.py --force         # Re-index everything
"""

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]  # <repo_root>
MANIFEST_PATH = ROOT_DIR / "rag" / "manifests" / "library_manifest.md"
LIBRARY_DIR = ROOT_DIR / "rag" / "library"
CHROMA_DIR = ROOT_DIR / "rag" / "indexes" / "chroma"

COLLECTION_NAME = "unified_library"
MIN_CHUNK_LENGTH = 400

# EPUB segmentation: target chars per segment (~1000-1400 tokens)
EPUB_SEGMENT_MIN_CHARS = 4000
EPUB_SEGMENT_MAX_CHARS = 5600
EPUB_OVERLAP_CHARS = 800  # ~200 tokens overlap between segments

# Embedding provider config (read from .env at runtime)
EMBEDDING_MODELS = {
    "openai": "text-embedding-3-large",
    "voyage": "voyage-4-large",
}

INDEX_VERSION = 1
PARSER_VERSION_PDF = "pypdf_v1"
PARSER_VERSION_EPUB = "ebooklib_v1"
CLEANING_VERSION = "v1"

# Domain mapping — folder name → domain string
# Add your domains here when creating new experts (see docs/runbooks/NEW_EXPERT.md)
DOMAIN_MAP = {
    "marketplace": "marketplace",
    "example_domain": "example_domain",
}


# ---------------------------------------------------------------------------
# Manifest Parser
# ---------------------------------------------------------------------------
def parse_manifest(path: Path) -> dict:
    """Parse library_manifest.md and return dict keyed by book_id."""
    text = path.read_text(encoding="utf-8")
    books = {}
    current_domain = None

    for line in text.splitlines():
        header_match = re.match(r"^###\s+(.+)", line)
        if header_match:
            header_text = header_match.group(1).strip().lower()
            # Add explicit branches for your domains here (see docs/runbooks/NEW_EXPERT.md)
            if "marketplace" in header_text or "listing" in header_text:
                current_domain = "marketplace"
            elif "example" in header_text:
                current_domain = "example_domain"
            else:
                current_domain = header_text.replace(" ", "_")
            continue

        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) < 5:
            continue
        if cells[0] in ("ID", "---") or cells[0].startswith("-"):
            continue

        book_id = cells[0].strip()
        title = cells[1].strip()
        file_name = cells[2].strip()
        raw_tags = cells[3].strip()
        status = cells[4].strip() if len(cells) > 4 else "[PENDING]"
        checksum = cells[5].strip() if len(cells) > 5 else ""
        pages_count = cells[6].strip() if len(cells) > 6 else ""
        indexed_at = cells[7].strip() if len(cells) > 7 else ""
        author = cells[8].strip() if len(cells) > 8 else ""
        year = cells[9].strip() if len(cells) > 9 else ""
        edition = cells[10].strip() if len(cells) > 10 else ""

        tags = [t.strip().strip("`") for t in raw_tags.split(",")]

        books[book_id] = {
            "book_id": book_id,
            "title": title,
            "file_name": file_name,
            "tags": tags,
            "status": status,
            "domain": current_domain or "unknown",
            "checksum": checksum,
            "pages_count": pages_count,
            "indexed_at": indexed_at,
            "author": author,
            "year": int(year) if year.isdigit() else None,
            "edition": edition or None,
        }

    return books


def write_manifest(path: Path, books: dict):
    """Re-write the manifest file with updated book data."""
    sections: dict[str, list] = {}
    # Add your domain display titles here (see docs/runbooks/NEW_EXPERT.md)
    domain_titles = {
        "marketplace": "Marketplace & Listings",
        "example_domain": "Example Domain",
    }

    for book in books.values():
        domain = book["domain"]
        if domain not in sections:
            sections[domain] = []
        sections[domain].append(book)

    lines = [
        "# RAG LIBRARY MANIFEST",
        "",
        "**Index Location:** `rag/indexes/chroma`",
        f"**Ingest Tool:** {os.environ.get('EMBEDDING_PROVIDER', 'voyage').title()} Embeddings ({EMBEDDING_MODELS.get(os.environ.get('EMBEDDING_PROVIDER', 'voyage'), 'unknown')})",
        "",
        "## Status Types",
        "- `[INDEXED]`: Processed and available in RAG.",
        "- `[PENDING]`: File exists but not yet indexed.",
        "- `[ARCHIVED]`: Removed from active index.",
        "",
        "## Library Inventory",
        "",
    ]

    for domain, domain_books in sections.items():
        section_title = domain_titles.get(domain, domain.replace("_", " ").title())
        lines.append(f"### {section_title}")
        lines.append(
            "| ID | Title | File Name | Tags | Status | Checksum | Pages/Segments | Indexed At | Author | Year | Edition |"
        )
        lines.append(
            "|---|---|---|---|---|---|---|---|---|---|---|"
        )
        for b in domain_books:
            tags_str = ", ".join(f"`{t}`" for t in b["tags"])
            year_str = str(b["year"]) if b.get("year") else ""
            edition_str = b.get("edition") or ""
            author_str = b.get("author") or ""
            pages_str = str(b.get("pages_count", ""))
            checksum_short = b.get("checksum", "")
            if checksum_short and len(checksum_short) > 12:
                checksum_short = checksum_short[:12] + "…"
            indexed_str = b.get("indexed_at") or ""
            lines.append(
                f"| {b['book_id']} | {b['title']} | {b['file_name']} | {tags_str} | {b['status']} "
                f"| {checksum_short} | {pages_str} | {indexed_str} | {author_str} | {year_str} | {edition_str} |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Shared Utilities
# ---------------------------------------------------------------------------
def compute_checksum(filepath: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(raw: str) -> str:
    """Normalize whitespace in extracted text."""
    text = raw.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_format(file_name: str) -> str:
    """Detect file format from extension."""
    ext = Path(file_name).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".epub":
        return "epub"
    return "unknown"


# ---------------------------------------------------------------------------
# PDF Processing
# ---------------------------------------------------------------------------
def extract_pdf_chunks(pdf_path: Path) -> list[dict]:
    """Extract text from each page of a PDF. Returns list of chunk dicts."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    chunks = []
    for i, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        text = clean_text(raw)
        chunks.append({
            "id_suffix": f"p{i + 1}",
            "text": text,
            "page": i + 1,
            "location": "",
            "parser_version": PARSER_VERSION_PDF,
        })
    return chunks


# ---------------------------------------------------------------------------
# EPUB Processing — chapter + segment
# ---------------------------------------------------------------------------
def extract_epub_chunks(epub_path: Path) -> list[dict]:
    """
    Extract text from EPUB by chapter, then split into segments of
    ~900-1200 words each.

    ID format: {book_id}_ch{chapter}_s{segment}
    Location:  ch.{chapter}, seg.{segment}

    Uses ebooklib as primary parser, falls back to direct zipfile extraction
    for EPUBs with non-standard structure.
    """
    try:
        html_contents = _epub_via_ebooklib(epub_path)
    except Exception as e:
        print(f"    [WARN] ebooklib failed ({e}), using zipfile fallback...")
        html_contents = _epub_via_zipfile(epub_path)

    from bs4 import BeautifulSoup

    chunks = []
    chapter_num = 0

    for html in html_contents:
        soup = BeautifulSoup(html, "html.parser")
        text = clean_text(soup.get_text(separator="\n"))

        if len(text.strip()) < MIN_CHUNK_LENGTH:
            continue

        chapter_num += 1
        segments = _split_into_segments(text)

        for seg_num, seg_text in enumerate(segments, start=1):
            location = f"ch.{chapter_num}, seg.{seg_num}"
            chunks.append({
                "id_suffix": f"ch{chapter_num}_s{seg_num}",
                "text": seg_text,
                "page": 0,
                "location": location,
                "parser_version": PARSER_VERSION_EPUB,
            })

    return chunks


def _epub_via_ebooklib(epub_path: Path) -> list[str]:
    """Extract HTML contents using ebooklib."""
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(str(epub_path), options={"ignore_ncx": True})
    contents = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html = item.get_content().decode("utf-8", errors="replace")
        contents.append(html)
    return contents


def _epub_via_zipfile(epub_path: Path) -> list[str]:
    """Fallback: extract HTML/XHTML files directly from EPUB zip archive."""
    import zipfile

    contents = []
    with zipfile.ZipFile(epub_path, "r") as zf:
        html_files = sorted(
            n for n in zf.namelist()
            if n.endswith((".xhtml", ".html", ".htm"))
            and not n.endswith("toc.xhtml")
            and "nav" not in n.lower()
        )
        for name in html_files:
            try:
                raw = zf.read(name).decode("utf-8", errors="replace")
                contents.append(raw)
            except Exception:
                continue
    return contents


def _split_into_segments(text: str) -> list[str]:
    """
    Split chapter text into segments of ~4000-5600 chars (~1000-1400 tokens).
    Breaks on paragraph boundaries. Adds ~800 char overlap between segments.
    """
    if len(text) <= EPUB_SEGMENT_MAX_CHARS:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    segments = []
    current_chars = 0
    current_parts: list[str] = []

    for para in paragraphs:
        para_len = len(para)
        projected = current_chars + para_len

        if projected > EPUB_SEGMENT_MAX_CHARS and current_chars >= EPUB_SEGMENT_MIN_CHARS:
            # Flush current segment
            segments.append("\n\n".join(current_parts))
            # Overlap: keep trailing paragraphs that fit within EPUB_OVERLAP_CHARS
            overlap_parts: list[str] = []
            overlap_chars = 0
            for p in reversed(current_parts):
                if overlap_chars + len(p) > EPUB_OVERLAP_CHARS:
                    break
                overlap_parts.insert(0, p)
                overlap_chars += len(p)
            current_parts = overlap_parts + [para]
            current_chars = overlap_chars + para_len
        else:
            current_chars += para_len
            current_parts.append(para)

    # Flush remaining
    if current_parts:
        remaining_text = "\n\n".join(current_parts)
        if current_chars < EPUB_SEGMENT_MIN_CHARS // 2 and segments:
            segments[-1] = segments[-1] + "\n\n" + remaining_text
        else:
            segments.append(remaining_text)

    return segments


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
MAX_EMBED_CHARS = 28000  # ~7000 tokens, safe margin under 8192 limit (~4 chars/token)


def _truncate_for_embedding(text: str) -> str:
    """Truncate text to stay within embedding model token limit."""
    if len(text) <= MAX_EMBED_CHARS:
        return text
    # Cut at word boundary
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
    batch_size = 32  # Reduced from 128 to stay under Voyage 120k token limit

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


# ---------------------------------------------------------------------------
# Ingestion Logic
# ---------------------------------------------------------------------------
def should_skip(book: dict, file_checksum: str) -> bool:
    """Determine if a book can be skipped (already indexed with same versions)."""
    if book["status"] != "[INDEXED]":
        return False
    if book.get("checksum") != file_checksum:
        return False
    return True


def ingest_book(
    book: dict,
    domain_dir: Path,
    collection,
    dry_run: bool = False,
    force: bool = False,
) -> dict | None:
    """Ingest a single book (PDF or EPUB). Returns updated book dict or None if skipped."""
    file_path = domain_dir / book["file_name"]
    if not file_path.exists():
        print(f"  [SKIP] File not found: {file_path}")
        return None

    file_format = detect_format(book["file_name"])
    if file_format == "unknown":
        print(f"  [SKIP] Unsupported format: {book['file_name']}")
        return None

    file_checksum = compute_checksum(file_path)

    if not force and should_skip(book, file_checksum):
        print(f"  [SKIP] Already indexed: {book['book_id']} ({book['title']})")
        return None

    print(f"  [PROCESS] {book['book_id']}: {book['title']} ({file_format.upper()})")

    # Extract chunks based on format
    if file_format == "pdf":
        chunks = extract_pdf_chunks(file_path)
        chunk_label = "pages"
    else:
        chunks = extract_epub_chunks(file_path)
        chunk_label = "segments"

    valid_chunks = [c for c in chunks if len(c["text"]) >= MIN_CHUNK_LENGTH]
    print(f"    {chunk_label.title()} extracted: {len(chunks)}, valid (>={MIN_CHUNK_LENGTH} chars): {len(valid_chunks)}")

    if dry_run:
        print(f"    [DRY-RUN] Would index {len(valid_chunks)} {chunk_label}.")
        if file_format == "epub" and valid_chunks:
            # Show chapter/segment breakdown
            chapters = set()
            for c in valid_chunks:
                loc = c["location"]
                ch = loc.split(",")[0] if loc else "?"
                chapters.add(ch)
            print(f"    [DRY-RUN] Chapters detected: {len(chapters)}")
        book_update = dict(book)
        book_update["pages_count"] = str(len(valid_chunks))
        return book_update

    if not valid_chunks:
        print(f"    [WARN] No valid {chunk_label} to index.")
        return None

    # Prepare data for ChromaDB
    ids = [f"{book['book_id']}_{c['id_suffix']}" for c in valid_chunks]
    documents = [c["text"] for c in valid_chunks]
    source_path = f"rag/library/{book['domain']}/{book['file_name']}"
    tags_str = ",".join(book["tags"])

    metadatas = [
        {
            "book_id": book["book_id"],
            "title": book["title"],
            "author": book.get("author") or "",
            "year": book.get("year") or 0,
            "edition": book.get("edition") or "",
            "domain": book["domain"],
            "tags": tags_str,
            "page": c["page"],
            "location": c["location"],
            "source_path": source_path,
            "checksum": file_checksum,
            "index_version": INDEX_VERSION,
            "parser_version": c["parser_version"],
            "cleaning_version": CLEANING_VERSION,
        }
        for c in valid_chunks
    ]

    # Get embeddings
    print(f"    Generating embeddings for {len(documents)} {chunk_label}...")
    embeddings = get_embeddings(documents)

    # Upsert to ChromaDB
    print(f"    Upserting {len(ids)} records to ChromaDB...")
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    # Update book record
    book_update = dict(book)
    book_update["status"] = "[INDEXED]"
    book_update["checksum"] = file_checksum
    book_update["pages_count"] = str(len(valid_chunks))
    book_update["indexed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    return book_update


def main():
    parser = argparse.ArgumentParser(description="RAG Ingestion Engine")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    parser.add_argument("--force", action="store_true", help="Re-index all books regardless of status")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")

    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage")
    if provider not in EMBEDDING_MODELS:
        print(f"ERROR: Unknown EMBEDDING_PROVIDER={provider}. Use 'openai' or 'voyage'.")
        sys.exit(1)

    key_var = "VOYAGE_API_KEY" if provider == "voyage" else "OPENAI_API_KEY"
    if not args.dry_run and not os.environ.get(key_var):
        print(f"ERROR: {key_var} not set in .env. Use --dry-run to preview without embeddings.")
        sys.exit(1)

    print("=== RAG Ingestion Engine ===")
    print(f"  Manifest: {MANIFEST_PATH}")
    print(f"  Library:  {LIBRARY_DIR}")
    print(f"  ChromaDB: {CHROMA_DIR}")
    print(f"  Dry run:  {args.dry_run}")
    print(f"  Force:    {args.force}")
    print()

    books = parse_manifest(MANIFEST_PATH)
    print(f"Found {len(books)} book(s) in manifest.\n")

    if not books:
        print("No books found in manifest. Nothing to do.")
        return

    collection = None if args.dry_run else get_collection()

    updated = 0
    for book_id, book in books.items():
        domain = book["domain"]
        domain_dir = LIBRARY_DIR / domain

        if not domain_dir.exists():
            for folder in LIBRARY_DIR.iterdir():
                if folder.is_dir() and folder.name.replace("-", "_") == domain:
                    domain_dir = folder
                    break

        try:
            result = ingest_book(book, domain_dir, collection, args.dry_run, args.force)
        except Exception as e:
            print(f"  [ERROR] {book_id}: {e}")
            result = None
        if result:
            books[book_id] = result
            updated += 1

    print(f"\n{'Processed' if not args.dry_run else 'Would process'}: {updated} book(s).")

    if updated > 0 and not args.dry_run:
        write_manifest(MANIFEST_PATH, books)
        print(f"Manifest updated: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
