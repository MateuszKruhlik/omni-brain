# RAG LIBRARY MANIFEST

**Index Location:** `rag/indexes/chroma`
**Ingest Tool:** Voyage Embeddings (voyage-4-large)

## Status Types
- `[INDEXED]`: Processed and available in RAG.
- `[PENDING]`: File exists but not yet indexed.
- `[ARCHIVED]`: Removed from active index.

## Library Inventory

### Example Domain
| ID | Title | File Name | Tags | Status | Checksum | Pages/Segments | Indexed At | Author | Year | Edition |
|---|---|---|---|---|---|---|---|---|---|---|
| ex_01 | Your Book Title | your_book.pdf | `tag1`, `tag2` | [PENDING] |  |  |  | Author Name | Year |  |

> **How to add books:** See `docs/runbooks/NEW_EXPERT.md` for the full process.
> Place PDF/EPUB files in `rag/library/<domain>/` and add entries above with `[PENDING]` status.
