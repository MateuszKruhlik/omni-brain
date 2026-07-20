# _archive — closed projects

Text of closed/retired projects **stays in the repo** (greppable, visible in `brain.html`).
Only documentation is archived — code and large binaries live elsewhere.

## Rules

- **Binaries** (screenshots, dumps, recordings) → `<YOUR_ARCHIVE_LOCATION>` (external disk / NAS);
  removed from the repo with `git rm` — git history still keeps them.
- **Status marker**: the archived project's `SUMMARY.md` (or `README.md`) starts with a status line, e.g.
  `**Status:** CLOSED <YYYY-MM-DD> — reason` / `RETIRED — replaced by <successor>` / `STANDBY — can be reactivated`.
- **Reactivation** = `git mv docs/projects/_archive/<project> docs/projects/<category>/<project>`.

## Contents

| Project | Status |
|:--------|:-------|
| `example_archived_project` | CLOSED <YYYY-MM-DD> — placeholder row, replace with your own |

Full auto-generated list of all projects: [`INDEX.md`](../INDEX.md).
