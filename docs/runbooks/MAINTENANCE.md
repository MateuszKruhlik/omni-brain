# Runbook: Quarterly Repo Maintenance

Run this every ~3 months. Time: ~1h with an AI agent / ~2-3h manually.
A second brain accumulates entropy like any other system — scratch files, drifted
docs, duplicate ingests, stale prompts. This checklist catches all of it.

> **Light monthly hygiene** (binary gate, INDEX anti-drift, dead links, git gc, secrets)
> lives in its own runbook: `MONTHLY_CLEANUP.md`. Quarterly = monthly + the deep part
> below (RAG health check, prompts, disks & backups).

## 1. Artifacts & junk (10 min)

```bash
# Junk tracked in git (scratch/temp/output files in repo root)
git ls-files | grep -vE '/' | grep -E 'scratch|temp|output|\.zip$'

# Empty files and directories (outside .git, venv, indexes)
find . -type d -empty -not -path './.git/*' -not -path '*/.venv/*' -not -path './rag/indexes/*'
find . -type f -empty -not -path './.git/*' -not -path '*/.venv/*' -not -path './rag/indexes/*'

# Large directories — did anything grow unexpectedly?
du -sh */ .[!.]*/ 2>/dev/null | sort -rh | head -12

# There should be exactly one venv (rag/.venv)
find . -maxdepth 3 -name pyvenv.cfg -not -path './.git/*'
```

## 2. Documentation consistency (10 min)

- [ ] `AGENTS.md` / `README.md`: expert count, chunk count, paths — still accurate?
- [ ] `docs/projects/INDEX.md` — is the **"Gaps (anti-drift)"** section empty? (`python3 tools/projects_index/build.py`)
- [ ] Archive candidates? Closed projects → `git mv docs/projects/<category>/<project> docs/projects/_archive/<project>`; project binaries → `<YOUR_ARCHIVE_LOCATION>`.
- [ ] Finished projects in `docs/projects/_archive/` carry a clear `CLOSED/RETIRED/STANDBY + date + reason` status at the top of SUMMARY?
- [ ] `experts/contracts.md` ↔ `experts/prompts/*` ↔ router — same expert list everywhere?

## 3. Expert prompts (15 min)

- [ ] Shared GROUNDING RULES block in sync: `python3 experts/sync_grounding.py --check` (drift → `--write`; source of truth: `experts/prompts/_shared/grounding_rules.md`)
- [ ] No dead references (experts/files mentioned in prompts that don't exist)
- [ ] Example `book_id`s in evidence blocks exist in `rag/manifests/library_manifest.md`? (examples are configured in `EXPERTS` inside `sync_grounding.py`)
- [ ] Time-bound facts embedded in prompts (project states, launch dates) — update or move to `domains/*/NOTES.md` with a date

## 4. RAG health check (15 min)

```bash
# Per-domain stats from the query log (top1, partial coverage)
rag/.venv/bin/python - <<'EOF'
import json, collections, statistics
es = [json.loads(l) for l in open('rag/logs/query_log.jsonl')]
by = collections.defaultdict(list)
for e in es: by[e.get('domain') or '-'].append(e)
print(f"total: {len(es)}")
for d, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f"{d:<14} n={len(v):<5} top1_med={statistics.median(e['top1'] for e in v):.3f} "
          f"partial={100*sum(1 for e in v if e.get('partial_coverage'))/len(v):.0f}%")
EOF

# Chroma inventory vs manifest — hunt duplicates
# (identical chunk counts for two different book_ids = a course/book ingested twice)
rag/.venv/bin/python - <<'EOF'
import chromadb, collections
col = chromadb.PersistentClient(path="rag/indexes/chroma").get_collection("unified_library")
metas = []
for off in range(0, col.count(), 5000):
    metas += col.get(limit=5000, offset=off, include=["metadatas"])["metadatas"]
c = collections.defaultdict(collections.Counter)
for m in metas: c[m.get("domain","?")][m.get("book_id","?")] += 1
print(f"chunks: {col.count()}")
for d, b in sorted(c.items()): print(f"{d}: {sum(b.values())} chunks, {len(b)} sources")
EOF
```

- [ ] `partial_coverage` > 30% in a domain → your library doesn't cover those topics (add sources or accept it)
- [ ] `top1_med` dropping vs last quarter → new queries may be drifting outside your library
- [ ] Identical chunk counts for different book_ids → duplicate ingest (delete one set: `col.delete(where={"book_id": {"$in": [...]}})`)
- [ ] Run 1-2 test queries with `--mode expert --debug` — any duplicated content inside one Evidence Pack?
- [ ] **Recalibrate `DOMAIN_THRESHOLDS`** in `rag/ingest/query.py` once a domain has ~100 logged queries: set (top1, avg5) to the 25th percentile from the stats above

## 5. Disks & backups (5 min)

- [ ] Any "source of truth" files excluded from git (binary docs, PDFs) — do they have a backup outside this machine?
- [ ] `df -h` — nothing close to full?

## 6. Wrap-up

- [ ] Short report in `docs/projects/repo_maintenance_<date>.md` (what was done, what was deferred)
- [ ] Commit: `chore(maintenance): quarterly review <date>`
- [ ] Schedule the next review (~3 months out)
