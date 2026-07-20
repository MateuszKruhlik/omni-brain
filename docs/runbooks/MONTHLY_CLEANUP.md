# Runbook: Monthly Repo Cleanup

Cadence: **once a month** (~15–20 min). Light hygiene — no deep repo analysis: every step has a command and a PASS criterion, so you can run it with your AI agent or by hand.
The deep review (RAG health check, expert prompts, disks & backups) stays **quarterly**: `MAINTENANCE.md`.

## Ground rules (always apply)

- **Never `git add .`** — only add explicit paths.
- **Do NOT touch**: `rag/` (indexes, venv, thresholds), git history (if you publish/mirror this repo!), or anything your own setup marks as generated.
- Product/application code lives in its own repositories — this repo holds knowledge and docs only. Don't pull code back in.
- Don't print secrets into the transcript or commits.
- **PASS = the command's PRINTOUT, not its exit code.** `grep` with no match returns exit 1 — at PASS that's EXPECTED, not an error. That's why the counters below end with `|| true`, and why you must not chain checks with `&&`.
- `<YOUR_ARCHIVE_LOCATION>` = wherever you keep large offloaded binaries (an external disk / NAS, e.g. mounted under `/Volumes/...` or `/mnt/...`). Define it once for yourself.
- **Never delete files autonomously** (exception: `.DS_Store` in step 6, and the explicit `git rm` after a verified copy). List deletion candidates in your summary for the user to decide.

## 0. Snapshot (1 min)

```bash
git status --short          # look it over: does everything here belong?
du -sh . .git docs rag tools
```

**Baseline** — record your own here, with a date (update it after any explained growth, as part of the cleanup commit; otherwise every future run will FAIL on the same, already-explained growth):

| date | repo | .git | docs | rag | tools |
|:-----|:-----|:-----|:-----|:----|:------|
| _(fill in)_ | | | | | |

**PASS:** nothing grew unexpectedly by >20% without a known reason. If it did → `du -sh <dir>/* | sort -rh | head` and find out what.

## 1. Binary gate (2 min)

Untracked-but-not-ignored binaries under `docs/` = a hole in `.gitignore` (one `git add` away from a mistake):

```bash
git ls-files --others --exclude-standard -- docs | grep -iE '\.(png|jpe?g|gif|pdf|wav|mp3|mp4|zip|mov|psd|fig)$' || true
```

**PASS:** empty. If something shows up → add a pattern to `.gitignore` (the "Project doc binaries" section) or move the file to `<YOUR_ARCHIVE_LOCATION>`. Only text goes in the repo; project assets live in `assets/` (ignored, only `.md` tracked).

## 2. INDEX anti-drift (2 min)

```bash
python3 tools/projects_index/build.py
sed -n '/## Gaps/,$p' docs/projects/INDEX.md
```

**PASS:** the "Gaps (anti-drift)" section reads `None — every project has a SUMMARY/README with a Status line. ✅`
If there are gaps → add a `**Status:** ...` line to the flagged project's SUMMARY (or create a short SUMMARY.md). A new project goes to `docs/projects/<category>/<slug>/SUMMARY.md` — categories are just the folders you create under `docs/projects/` (plus the reserved `_archive`).

While you're here, glance at the INDEX tables: any status outside `_archive/` shouting "CLOSED/RETIRED/done"? If so → candidate for step 3.

## 3. Archiving (2 min; often "nothing to do")

A project that's closed/retired but still in the hot tree? Procedure (convention: `docs/projects/_archive/README.md`):

```bash
# 0) Is your archive volume mounted? If not -> STOP, tell the user. (rsync to an unmounted
#    /Volumes or /mnt target silently creates a GHOST directory on the system disk and fakes
#    a successful archive!) Check first:
mount | grep -i <your_archive_volume> || true

git mv docs/projects/<category>/<slug> docs/projects/_archive/<slug>
# 1) SUMMARY starts with a status line: **Status:** CLOSED/RETIRED/STANDBY + <date> + reason/successor
# 2) project binaries -> <YOUR_ARCHIVE_LOCATION>/<slug>/
#    (rsync -a --checksum; THEN compare file count & bytes source vs dest; ONLY THEN git rm)
# 3) grep -rn "docs/projects/<category>/<slug>" --include='*.md' . -> fix references to _archive/
```

**Candidate backlog (keep this list current):** (none yet)

## 4. Dead links (1 min)

```bash
python3 tools/brain/build.py 2>&1 | grep -A20 "dead link" || true
```

**PASS:** matches your known-baseline list below (initially: **0**). Any NEW dead link → fix the source `.md` (usually a path typo or a file moved without updating the link).

Known-baseline dead links: _(none)_

## 5. Git housekeeping (2 min)

```bash
git worktree prune -v
git branch --merged main | grep -vE '^\* |^ *(main|<your-working-branch>)$' || true   # merged branches to delete
git count-objects -v
```

**PASS:** no orphaned worktrees; no merged zombie branches; `count` (loose objects) **< 1000** and `garbage: 0`.
If `count` ≥ 1000 or garbage > 0:

```bash
find .git/objects -name 'tmp_obj_*' -type f -delete   # only if garbage > 0
git gc
```

## 6. Junk & inbox (2 min)

```bash
find . -name .DS_Store -not -path './.git/*' -delete
ls -la inbox/
```

**PASS:** `inbox/` holds only things deliberately "in the waiting room". Files older than a month → **list them in your summary as candidates for the user to decide** (proper home / archive / delete). **Do not delete anything from `inbox/` yourself** — it's git-ignored, so a deleted file is gone for good (e.g. an active personal note is not junk). There's no `Temporary/`-style folder (and we don't create one — `inbox/` is for that).

## 7. Secrets (1 min)

An IDE/agent allowlist must not contain secrets inside command strings (allowlists can accidentally capture one-off commands that embed a password or key). Check with COUNTERS, don't print values. Counter #1 excludes lines containing `grep` so the check command can't match itself if it ever lands in the allowlist:

```bash
grep "sshpass -p '" .claude/settings.local.json | grep -cv "grep" || true    # expected: 0
grep -cE "ApiKey [A-Za-z0-9]{10,}" .claude/settings.local.json || true       # expected: 0
grep -cE "password['\"]?[:=]" .claude/settings.local.json || true            # expected: 0
git ls-files | grep -E '^\.env$|secrets' | grep -v example || true           # expected: empty
```

**PASS:** all counters 0 (remember: exit 1 on no-match = OK). A counter > 0 → first `grep -n` for the pattern only (without printing values) and check whether the hit is an allowlist entry containing the check command itself; a real secret → remove the entry from `permissions.allow` (one-off historical commands have no permission value; a generic `Bash(sshpass:*)` is enough), validate the JSON (`python3 -c "import json; json.load(open('.claude/settings.local.json'))"`), and **tell the user that rotation is required**.

## 8. Wrap-up (1 min)

- **Branch:** run on your working branch. If your workflow forbids committing straight to `main` and you're on `main` → STOP and switch.
- Changes from steps 0–7 → one commit: `chore(cleanup): monthly review <YYYY-MM>` (the pre-commit hook refreshes INDEX.md + brain.html).
- **Push after the user confirms**, so your backup/mirror sees the commit.
- **No report** — the monthly cleanup is light. Reports are the quarterly `MAINTENANCE.md`'s job.
- Summary for the user: what PASSed, what you fixed, and the **list of candidates for their decision** (inbox, archiving). Anything outside the checklist → one line in the "Anomaly log" below.

> **Tip.** If you use Claude Code, add a local slash command `.claude/commands/cleanup.md` (the `.claude/` dir is git-ignored) with front-matter `description: Monthly repo cleanup — execute MONTHLY_CLEANUP.md step by step` and this body: "Execute `docs/runbooks/MONTHLY_CLEANUP.md` steps 0–8. Read the whole runbook first — the Ground Rules are binding. For each step run the command and compare with the PASS criterion; PASS → next, FAIL → apply the described fix. Don't analyze the repo beyond the runbook. Never delete anything autonomously (except `.DS_Store`) — list candidates in the summary."

## Anomaly log

- (empty)
