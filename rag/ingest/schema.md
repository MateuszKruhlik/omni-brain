# ChromaDB Record Schema — unified_library

## Collection
- **Name**: `unified_library`
- **Embedding Model**: `voyage-4-large` (Voyage AI) — 1024 dimensions, configurable via `EMBEDDING_PROVIDER` in `.env`
- **Persist Directory**: `rag/indexes/chroma`

## Record Structure

### ID Format

**PDF:**
```
{book_id}_p{page_num}
```
Example: `ex_01_p12`

**EPUB:**
```
{book_id}_ch{chapter}_s{segment}
```
Example: `ex_02_ch4_s2`

### Document
- Chunk text content (cleaned, whitespace-normalized).
- Chunks with `len(text.strip()) < 50` are **skipped**.

### Chunking Strategy

| Format | Unit         | Size                          | Citation Example                         |
|--------|--------------|-------------------------------|------------------------------------------|
| PDF    | Page         | 1 page = 1 chunk              | Example Book, p. 24                      |
| EPUB   | Segment      | ~900–1200 words per segment   | Example Guide, ch. 4, seg. 2             |

**EPUB segmentation rules:**
- Each EPUB document item (typically a chapter) is split into segments.
- Segments break on paragraph boundaries (never mid-paragraph).
- Target: 900–1200 words per segment.
- Segments shorter than 450 words are merged into the previous segment.
- Chapters shorter than 1200 words remain as a single segment.

### Metadata Fields

| Field              | Type            | Required | Description                                              |
|--------------------|-----------------|----------|----------------------------------------------------------|
| `book_id`          | string          | yes      | Primary key from manifest (e.g., `ex_01`)                |
| `title`            | string          | yes      | Book title                                               |
| `author`           | string          | yes      | Author name(s)                                           |
| `year`             | int             | no       | Publication year                                         |
| `edition`          | string          | no       | Edition identifier                                       |
| `domain`           | string          | yes      | Domain category (e.g., `marketplace`)                    |
| `tags`             | string          | yes      | Comma-separated tags (e.g., `"copywriting,seo"`)         |
| `page`             | int             | yes      | Page number (1-indexed for PDF, `0` for EPUB)            |
| `location`         | string          | yes      | EPUB: `ch.{N}, seg.{M}` — empty for PDF                 |
| `source_path`      | string          | yes      | Relative path to source file                             |
| `checksum`         | string          | yes      | SHA-256 hash of source file                              |
| `index_version`    | int             | yes      | Schema/index version (current: `1`)                      |
| `parser_version`   | string          | yes      | `pypdf_v1` for PDF, `ebooklib_v1` for EPUB               |
| `cleaning_version` | string          | yes      | Text cleaning version (e.g., `v1`)                       |

## Version Tracking
- **index_version**: Increment when schema changes require full re-index.
- **parser_version**: Tracks extraction method per format. Change triggers re-index.
- **cleaning_version**: Tracks text normalization logic. Change triggers re-index.
