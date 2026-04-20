# Runbook: Adding a New Expert (with or without RAG from PDF/EPUB)

**Last updated:** <YYYY-MM-DD>
**Existing deployments:** *add yours here*

> **Other runbooks:**
> - **Video courses → RAG**: See [NEW_VIDEO_COURSE.md](NEW_VIDEO_COURSE.md)
> - This runbook covers **PDF/EPUB** as knowledge sources.

---

## When to Use This Runbook

When you want to add a new expert to the system. Two variants:
- **Variant A: Expert + RAG (PDF/EPUB)** — expert with its own book domain (full path)
- **Variant B: Expert without RAG** — expert using only domain NOTES + contracts (short path, skip steps marked 📖)

---

## Pre-flight: Decisions to Make

Answer these questions before starting:

| # | Question | Example |
|---|----------|---------|
| 1 | Expert name (snake_case) | `my_expert` |
| 2 | RAG domain (snake_case, short) | `my_domain` |
| 3 | Book ID prefix (3 letters) | `dom` |
| 4 | Manifest section header | `My Domain & Topic` |
| 5 | How many books / what formats? | N (PDF/EPUB) |
| 6 | Scope overlap with existing domains? | Check existing domains for duplicate books |
| 7 | What query types should the expert handle? | topic research, best practices, how-to guides |

> **Scope overlap:** If a book already exists in another domain, you must decide:
> - **Duplication** (separate chunks per domain) — simpler, but costs more embeddings
> - **Cross-domain query** (no `--domain` filter) — broader access, but expert sees other domains' sources

---

## Phase 1: Code Changes (Prerequisites) 📖

> 📖 = only for Variant A (with RAG)

### 1.1 `rag/ingest/ingest.py` — 3 places to edit

**DOMAIN_MAP** (~line 49):
```python
DOMAIN_MAP = {
    "marketplace": "marketplace",
    "YOUR_DOMAIN": "YOUR_DOMAIN",  # ← add
}
```

**Manifest parser — conditional branch** (~line 68):
```python
if "marketplace" in header_text or "listing" in header_text:
    current_domain = "marketplace"
elif "YOUR_KEYWORD" in header_text:  # ← add BEFORE else
    current_domain = "YOUR_DOMAIN"
else:
    current_domain = header_text.replace(" ", "_")
```

> ⚠️ **Gotcha:** The else branch generates a domain name from the header via `replace(" ", "_")`. A header like "Career & Business" would produce `career_&_business`, not `career`. Always add an explicit branch.

**domain_titles** (~line 121):
```python
domain_titles = {
    "marketplace": "Marketplace & Listings",
    "YOUR_DOMAIN": "Your Section Header",  # ← add
}
```

### 1.2 `rag/ingest/query.py` — intent packs

Add 3–5 intent packs for the new domain (~line 66+):
```python
"pack_name": {
    "keywords": ["word1", "word2", "word3_local", "word3_en"],
    "subquery": "English phrases covering the intent",
},
```

**Rules for creating intent packs:**
- Each pack = one query type (e.g., "pricing", "negotiation", "branding")
- Keywords: mix of languages, minimum 4–6 per pack
- Subquery: English, 5–8 phrases separated by spaces
- Don't duplicate keywords between packs of the same domain

> ⚠️ **Gotcha:** Without intent packs, Stage 2 fallback is dead for your domain. The expert will only get results from Stage 0/1 (embedding similarity). For broad queries, this may not be enough.

---

## Phase 2: RAG Library 📖

### 2.1 Folder + files
```
rag/library/<domain>/    ← create folder
                         ← add PDF/EPUB files
```

### 2.2 Manifest (`rag/manifests/library_manifest.md`)

Add a section at the end of the file:
```markdown
### Your Section Header
| ID | Title | File Name | Tags | Status | Checksum | Pages/Segments | Indexed At | Author | Year | Edition |
|---|---|---|---|---|---|---|---|---|---|---|
| xxx_01 | Book Title | exact_filename.pdf | `tag1`, `tag2` | [PENDING] |  |  |  | Author | Year | Edition |
```

**Rules:**
- **File Name** = exact filename in the folder (with extension, case-sensitive)
- **ID** = `prefix_NN` (e.g., `mkt_01`, `biz_01`)
- **Tags** = always start with the domain tag (e.g., `marketplace`, `business`)
- **Status** = `[PENDING]` (ingest will change to `[INDEXED]`)
- Author/Year/Edition = optional, but helpful for citations

---

## Phase 3: Ingest 📖

### 3.1 Dry-run
```bash
rag/.venv/bin/python rag/ingest/ingest.py --dry-run
```

**Check the output:**
- [ ] New books have your domain prefix (e.g., `mkt_01`, not `ux_09`)
- [ ] Format detected correctly (PDF/EPUB)
- [ ] Number of valid chunks is reasonable (not 0)
- [ ] Existing books show `[SKIP]` (not re-indexing)

### 3.2 Full ingest
```bash
rag/.venv/bin/python rag/ingest/ingest.py
```

**Check:**
- [ ] "Processed: N book(s)" — N = number of new books
- [ ] "Manifest updated" at the end
- [ ] Manifest has `[INDEXED]` statuses + checksums + timestamps

> ⚠️ **Gotcha:** `ingest.py` has no `--domain` flag. It iterates over ALL books in the manifest. Existing indexed books will be skipped automatically (checksum match).

### 3.3 Retrieval test
```bash
rag/.venv/bin/python rag/ingest/query.py "test query for your domain" --mode expert --domain YOUR_DOMAIN --debug
```

**Check:**
- [ ] Evidence Pack contains chunks from NEW books (not old ones)
- [ ] `books=N` — is there diversification (≥3 different books)?
- [ ] Stage 0 sufficient? If not — check intent packs
- [ ] Scores are reasonable (top1 > 0.45 for Voyage)

---

## Phase 4: Expert Definition

### 4.1 Contract (`experts/contracts.md`)

Add at the end (before "Routing rule of thumb"):
```markdown
## N) expert_name
**Decision types:** ...
**Inputs:** ...
**Outputs:** ...
**Not in scope:** ... (point to which expert to redirect to)
**Safety:** ... (if applicable — disclaimer)
**Sources priority:** domain NOTES (domain) → RAG (domain) → assumptions.
```

Add a routing rule:
```markdown
- **"triggering question?"** → expert_name
```

### 4.2 Prompt (`experts/prompts/<name>.md`)

**Use the following structure.** Minimum required sections:

| Section | Required? | Description |
|---------|-----------|-------------|
| ROLE & MISSION | ✅ | Who the expert is, what it does, tone |
| SCOPE | ✅ | What it does + what it does NOT (with redirects) |
| INPUT CONTRACT | ✅ | How to ask the expert |
| OUTPUT CONTRACT | ✅ | Response format (bullet points) |
| SOURCES + RAG command | 📖 RAG only | Mandatory action + command |
| GROUNDING RULES | 📖 RAG only | No phantom sources + evidence audit block |
| QUALITY RULES | ✅ | Quality rules for responses |

**RAG command in the prompt** (copy and replace domain):
```
rag/.venv/bin/python rag/ingest/query.py "YOUR QUERY HERE" --mode expert --domain YOUR_DOMAIN
```

> ⚠️ **Gotcha:** Without GROUNDING RULES the expert will hallucinate book_ids, invent citations, and skip the evidence audit block. This is the most common cause of low-quality RAG-backed responses.

### 4.3 Domain NOTES (`domains/<domain>/NOTES.md`)

Create a placeholder:
```markdown
# Domain Name — Domain Notes

## Key Decisions & Context
## Current Situation
## Lessons Learned
```

The expert treats NOTES as a first-class source (higher priority than RAG).

### 4.4 Routing Table (`experts/contracts.md`)

Add a row to the "Routing rule of thumb" table at the bottom of `contracts.md`:
```markdown
| Your decision type | `expert_name` | "example query 1?", "example query 2?" |
```

---

## Phase 5: Documentation (Close the Loop)

| File | What to update |
|------|----------------|
| `docs/SYSTEM_CONTEXT.md` | **CRITICAL:** Section 3.1 (domain count, chunk count), 3.2 (RAG Sources count), 3.3 (expert workflow — add new RAG-backed expert) |
| `docs/patterns/OPERATIONS.md` | No changes (unless new pattern) |

> ⚠️ **SYSTEM_CONTEXT.md is the source of truth for the entire system.** If you don't update sections 3.1–3.3, future sessions will have stale context about available experts and RAG domains.

---

## Final Checklist

```
[ ] Code: DOMAIN_MAP + parser branch + domain_titles (ingest.py)
[ ] Code: intent packs (query.py)
[ ] Library: folder + files + manifest entries
[ ] Ingest: dry-run OK + full ingest OK + manifest updated
[ ] Test: retrieval with --debug returns reasonable results
[ ] Contract: entry in contracts.md
[ ] Prompt: full prompt with output contract + grounding rules
[ ] NOTES: domains/<domain>/NOTES.md created
[ ] Routing: row in contracts.md routing table
[ ] Docs: **SYSTEM_CONTEXT** (sections 3.1, 3.2, 3.3!)
```

---

## Known Gotchas

1. **Manifest parser else branch** — without an explicit branch, it generates the wrong domain name from the header
2. **`ingest.py --domain` does not exist** — don't try it, ingest iterates over the entire manifest
3. **Intent packs are per-domain** — without them, Stage 2 fallback doesn't work for your domain
4. **Prompt without grounding rules** = hallucinated sources
5. **File Name in manifest must be EXACT** — case-sensitive, with extension, with spaces if any
6. **Books may re-index** — on the first ingest after manifest changes, existing books may re-index (upsert, safe, but costs tokens). Subsequent runs will skip them.
