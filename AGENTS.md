# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

---

## High-Level Architecture

**Omni Brain** is a Local-First Multi-Expert System combining:
- **Experts** (`experts/prompts/`) — Specialized AI personas (markdown prompts) loaded into IDEs (Cursor, Claude Code, Windsurf)
- **RAG (Retrieval-Augmented Generation)** — ChromaDB vector index (`rag/indexes/chroma/`) storing chunked PDF/EPUB books
- **Domain Knowledge** (`domains/NOTES.md`) — Personal learning accumulated per domain, treated as first-class sources in expert queries
- **Video Pipeline** — WhisperX-based transcription → chunking → RAG ingestion for video courses

### Data Flow
1. **Ingestion**: Books (PDF/EPUB) → `rag/ingest/ingest.py` → parsed into chunks → embedded (Voyage or OpenAI) → ChromaDB `unified_library` collection
2. **Query**: Expert prompt → `rag/ingest/query.py` → multi-stage retrieval (fallback logic) → evidence-backed answers
3. **Context**: Expert reads SYSTEM_CONTEXT.md + project SUMMARY.md + domain NOTES.md + RAG results → produces structured output per contract

### Directory Structure
```
omni-brain/
├── experts/prompts/         # AI expert prompts (load into IDE)
│   ├── onboarding_guide.md  # START HERE — welcome wizard
│   └── router_checklist.md  # Pick the right expert
├── experts/contracts.md     # Input/output contracts for each expert
├── domains/*/NOTES.md       # Domain-specific knowledge captures
├── rag/ingest/              # Ingestion and query tools (Python)
│   ├── ingest.py            # PDF/EPUB → ChromaDB
│   ├── ingest_video.py      # Video chunks → ChromaDB
│   ├── query.py             # Multi-stage retrieval (CLI + expert modes)
│   └── schema.md            # ChromaDB record schema
├── rag/library/             # PDF/EPUB storage (git-ignored)
├── rag/indexes/chroma/      # ChromaDB vector store (git-ignored)
├── rag/manifests/           # Book inventory manifest (markdown table)
├── video_pipeline/example_course/  # Video → transcript → chunks pipeline
├── docs/SYSTEM_CONTEXT.md   # Global system state & constraints
├── docs/projects/           # Per-project documentation
└── docs/runbooks/           # How-to guides (NEW_EXPERT.md, NEW_VIDEO_COURSE.md)
```

---

## Essential Development Commands

### RAG Ingestion & Querying

**Setup (one-time):**
```bash
# Initialize Python environment
python3 -m venv rag/.venv
source rag/.venv/bin/activate
pip install -r rag/ingest/requirements.txt

# Configure secrets
cp .env.example .env
# Edit .env with EMBEDDING_PROVIDER (voyage or openai) and API key
```

**Index PDF/EPUB books:**
```bash
# Preview changes without writing to ChromaDB
python rag/ingest/ingest.py --dry-run

# Full index (computes checksums, chunks, embeds, persists to ChromaDB)
python rag/ingest/ingest.py

# Force re-index all books (ignores checksums)
python rag/ingest/ingest.py --force
```

**Query the RAG index (for testing/debugging):**
```bash
# CLI mode — short excerpts for human reading
python rag/ingest/query.py "how to improve code quality"
python rag/ingest/query.py "python architecture patterns" --domain software_engineering

# Expert mode — full text, multi-stage fallback, diverse results
python rag/ingest/query.py "system design best practices" --mode expert --domain software_engineering

# Debug mode — show fallback stages and confidence signals
python rag/ingest/query.py "tags SEO optimization" --mode expert --debug
```

### Manifest Management

**Edit book inventory:**
- Update `rag/manifests/library_manifest.md` manually (add rows to the domain section)
- Ingest script auto-updates the manifest with `[INDEXED]` status, checksums, and timestamps

**Library structure:**
```
rag/library/
├── some_domain/             # Domain folder (one per domain)
│   ├── book_1.pdf
│   ├── book_2.epub
│   └── ...
├── example_domain/          # Create folders for your domains
└── ...
```

---

## Key Implementation Details

### RAG Chunking Strategy

| Format | Unit      | Size                     | Citation Example                  |
|--------|-----------|--------------------------|-----------------------------------|
| **PDF**  | Page      | 1 page = 1 chunk         | Example Book, p. 24               |
| **EPUB** | Segment   | ~4000–5600 chars (~1000–1400 tokens) | Example Guide, ch. 4, seg. 2      |

**EPUB segmentation rules:**
- Split on paragraph boundaries (never mid-paragraph)
- Segments <400 chars are skipped
- Segments <800 chars are merged into the previous segment
- 800-char overlap between adjacent segments for context

### ChromaDB Record Metadata

All chunks store: `book_id`, `title`, `author`, `domain`, `tags`, `page` (PDF) or `location` (EPUB: `ch.X, seg.Y`), `source_path`, `checksum`, parser/cleaning versions.

See `rag/ingest/schema.md` for the complete record schema and version tracking policy.

### Expert Contracts

Experts are strictly scoped by input/output contracts. See `experts/contracts.md` for the routing table.

Template ships with 1 example expert:
- **onboarding_guide**: System orientation (read this first)

Each expert reads: SYSTEM_CONTEXT.md → project SUMMARY.md → domain NOTES.md → RAG query results.

Add new experts by following `docs/runbooks/NEW_EXPERT.md`.

---

## Configuration & Secrets

**Environment variables** (`.env` file, **never committed**):
- `EMBEDDING_PROVIDER`: `voyage` (default) or `openai`
- `VOYAGE_API_KEY` or `OPENAI_API_KEY`: Required for embedding
- `CHROMA_DIR`: ChromaDB persist path (default: `rag/indexes/chroma`)

**Manifest metadata** (tracked in `library_manifest.md`):
- `checksum`: SHA-256 of source file (detect changes between runs)
- `indexed_at`: Timestamp of last ingestion
- `status`: `[PENDING]`, `[INDEXED]`, or `[ARCHIVED]`

---

## Common Workflows

### Add a new book
1. Copy PDF/EPUB to `rag/library/<domain>/`
2. Add a row to `rag/manifests/library_manifest.md` (follow existing format)
3. Run `python rag/ingest/ingest.py --dry-run` (preview chunks)
4. Run `python rag/ingest/ingest.py` (index to ChromaDB)
5. Verify: `python rag/ingest/query.py "topic from book" --domain <domain>`

### Add a new expert prompt
1. Create `experts/prompts/<expert_name>.md`
2. Define **Scope**, **Input/Output Contract**, **RAG Integration**, **Grounding Rules**
3. Document the expert in `experts/contracts.md`
4. Load the prompt in your IDE and test

### Add a video course
1. See `docs/runbooks/NEW_VIDEO_COURSE.md` for detailed steps
2. Short version: Video → audio (ffmpeg) → transcript (WhisperX) → chunks (JSONL) → ChromaDB
3. Example scripts in `video_pipeline/example_course/scripts/`

### Query RAG for evidence
```bash
# From an expert prompt or CLI
python rag/ingest/query.py "your question" --domain <domain> --mode expert
```

---

## Important Constraints

- **Local-First**: All logic, planning, and context live on your laptop. Servers (optional) handle heavy compute/storage only.
- **Secrets**: Never include API keys or tokens in markdown. Use `.env` file exclusively.
- **Source of Truth**: `SYSTEM_CONTEXT.md` defines the system state—update it as architecture evolves.
- **RAG Grounding**: Experts must cite sources. Multi-stage fallback retrieval prevents hallucinated citations.
- **Version Tracking**: ChromaDB records store `parser_version` and `cleaning_version`. Changing parsing/cleaning logic requires full re-index.

---

## References

- **Start Here**: `docs/SYSTEM_CONTEXT.md` (system state & principles)
- **How Experts Work**: `experts/contracts.md` (routing & scoping)
- **RAG Schema**: `rag/ingest/schema.md` (record structure, chunking rules)
- **Onboarding**: `experts/prompts/onboarding_guide.md` (7-step walkthrough)
- **New Expert**: `docs/runbooks/NEW_EXPERT.md` (how to add an expert)
- **New Video**: `docs/runbooks/NEW_VIDEO_COURSE.md` (video → RAG pipeline)
