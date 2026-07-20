# Brain HTML — runbook

**Status:** Active
**Last updated:** <YYYY-MM-DD>

A single-file knowledge browser for the whole repo: `brain.html` at the repo root
(open it with a double-click — it works from `file://`, no server needed).

---

## Daily use

- **Open:** double-click `brain.html` (or ⌘R / F5 in an open tab after a rebuild).
- **Navigate:** sidebar (tree that mirrors your folders) · dashboard (`#/` — active projects, recently edited) · `⌘K` search (diacritic-insensitive: "dzialal" also matches "działał") · `⌘\` toggles the sidebar.
- **From reading to editing:** the `path` / `md` buttons in the title bar copy the file's absolute path or its raw markdown — paste into your AI agent.
- **Rebuild:** automatically on every commit (pre-commit hook), or manually:
  ```bash
  python3 tools/brain/build.py        # <1 s, stdlib only, no venv
  ```
- **Edit mode (optional):**
  ```bash
  python3 tools/brain/serve.py        # builds, opens http://127.0.0.1:8643, self-stops after 10 min idle
  ```
  Over HTTP an **`edit`** button appears in the title bar: a textarea with the raw md → `save (⌘S)` overwrites the file (path-validated, atomic write), rebuilds brain.html and reloads the view. Good for quick fixes (statuses, checkboxes, typos); large edits still belong in your editor/agent. From `file://` the button is hidden (a browser cannot write to disk).

## Architecture (why it's built this way)

- `fetch()` and ES modules **do not work from `file://`** → the whole corpus is embedded as JSON inside the HTML, with hash routing `#/path.md::anchor`.
- **The markdown in the payload is untouched** (original — "copy md" returns it 1:1); the client rewrites links at render time: inside the corpus → hash route; exists on disk but out of scope → dotted underline, click copies the path; no target → wavy "dead link" + a build-time warning (link-rot linter).
- Client-side render: vendored **marked** (GFM) + **highlight.js** + **MiniSearch** (`tools/brain/vendor/`, pinned versions, no npm/CDN).
- Metadata without frontmatter: 3 regexes (`# title`, `**Status:**`, `**Last updated:**`); dates from a single `git log --name-only` (fallback: mtime).

## Files

```
tools/brain/build.py        # builder (stdlib only)
tools/brain/serve.py        # optional edit-mode server (port 8643)
tools/brain/template.html   # UI: tokens + components + JS
tools/brain/vendor/         # marked 15.0.12 · highlight.js 11.11.1 (+dart) · minisearch 7.1.2
.githooks/pre-commit        # rebuild on commit (activate: git config core.hooksPath .githooks)
brain.html                  # artifact (git-ignored)
```

## How to change

- **Content scope:** `SCOPE_DIRS` / `SCOPE_FILES` in `build.py`. (`inbox` is in the default scope so a local `inbox/` shows up in the viewer; it is git-ignored, so it never gets committed.)
- **Highlight language:** drop `languages/<lang>.min.js` from a highlight.js cdn release into `vendor/` and add it to the `VENDOR` list in `build.py`.
- **Colors/theme:** `:root` / `[data-theme=dark]` blocks in `template.html` — ~10 seeds per theme, the rest is derived (color-mix). A new skin = copy the dark block and swap the seeds.
- **Dashboard "archived" status:** the `ARCHIVED_RE` regex in `template.html`.

## Troubleshooting

- **Stale view** → rebuild (`python3 tools/brain/build.py`) and ⌘R; the hook only fires on commits.
- **Hook doesn't run after a fresh clone** → `git config core.hooksPath .githooks`.
- **Theme not remembered (Safari)** → localStorage on `file://` is undefined per spec there; it degrades to `prefers-color-scheme` (intended).
- **File > 15–20 MB** (if the repo grows a lot) → switch the payload to a sibling `.js` loaded via a relative `<script src>` (still works from file://).
