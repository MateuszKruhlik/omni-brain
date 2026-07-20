<p align="center">
  <img src="docs/assets/logo.png" width="128" alt="Omni Brain">
</p>

# Omni Brain

> **Local-First Multi-Expert System**
> Personal knowledge meets AI-powered execution.

Your **second brain as a GitHub repo** — a full team of specialized AI experts, RAG from books + video courses, and clean contracts. If Cursor/Claude is your assistant and Notion is your notes, Omni Brain is an entire **team of experts living inside your repo**.

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![RAG](https://img.shields.io/badge/RAG-PDF%20%7C%20EPUB%20%7C%20Video-orange)
![Architecture](https://img.shields.io/badge/architecture-local--first-blue)

---

## Quick Start (5 Minutes)

```bash
git clone https://github.com/MateuszKruhlik/omni-brain.git
cd omni-brain
cp .env.example .env
# Fill in .env (minimum: Voyage or OpenAI key)

python3 -m venv .venv && source .venv/bin/activate && pip install -r rag/ingest/requirements.txt

git config core.hooksPath .githooks   # auto-refresh docs/projects/INDEX.md + brain.html on each commit
```

Open the repo in your IDE and load:

```
experts/prompts/onboarding_guide.md
```

**Pro tip.** After reading onboarding, paste this **Master Prompt** into your AI chat:

> *"I have just cloned Omni Brain. I have read the onboarding guide. Please initialize my environment and ask me what I want to do next: create a project, create an expert, or explore the video pipeline."*

The Onboarding Guide will take over, welcome you, and guide you through your first steps.

---

## Omni Brain Is for You If…

- You want **structured, consistent AI assistants** grounded only in your own knowledge
- You have libraries of books, notes, and video courses you want to turn into real RAG
- You live in an IDE (Cursor, Claude Code, Windsurf, Continue.dev, OpenAI Codex…) and prefer loading ready-made prompts
- You value **local-first** and full control (Ollama, LM Studio, Groq, OpenAI, Anthropic…)
- You document projects properly (SUMMARY, decisions, risks)

---

## Key Benefits

| Benefit | Why it matters |
|:--------|:---------------|
| **Expert contracts** | Repeatable answers, zero hallucinations |
| **Built-in Prompt Engineer** | Create, review, refactor expert prompts with a dedicated expert |
| **Full video pipeline** | Turn any Udemy/YouTube course into an expert in minutes |
| **NOTES > RAG priority** | Domain NOTES outrank standard RAG hits |
| **Projects folder** | Long-term work, architecture decisions, risk registers |
| **Self-tuning retrieval** | Cross-encoder reranking, per-domain confidence thresholds calibrated from your own query log, multi-domain search |
| **Drift-proof prompts** | Shared GROUNDING RULES template synced into every RAG expert (`sync_grounding.py --check/--write`) |
| **Zero infra** | Works instantly in any AI IDE — no custom app |

### RAG Cost (Recommendation)

I use **Voyage AI** for chunking and embedding.
Add a card → **Tier 1 = 200 M tokens free**.
A solid RAG with a dozen books uses on average ~**2–3 M tokens**.
One subscription easily handles dozens of experts and entire course libraries.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       OMNI BRAIN SYSTEM                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────────────┐  ┌────────────────────┐  ┌────────┐ │
│   │     experts/       │  │     domains/       │  │  rag/  │ │
│   │ Prompts+contracts  │  │ NOTES.md+knowledge │  │ChromaDB│ │
│   └────────────────────┘  └────────────────────┘  └────────┘ │
│                                                              │
│               (optional) Servers via SSH / SMB               │
└──────────────────────────────────────────────────────────────┘
```

**Local-first** — everything lives on your laptop. Servers are only for heavy lifting (WhisperX, inference).

---

## How Documentation Works

The `docs/` folder is your project memory — structured so both you **and** your AI experts can navigate it consistently.

### Projects (`docs/projects/`)

Each project gets its own folder with three files:

| File | Purpose |
|:-----|:--------|
| `SUMMARY.md` | Architecture, service map, deployment steps, incident log |
| `decisions.md` | Architecture Decision Records — what was decided, why, alternatives considered |
| `risks.md` | Risk register — what could go wrong, likelihood, mitigation |

Experts read your project docs before answering, so they always have context. Copy `docs/projects/example_category/example_project/` to start a new one.

**Categories & INDEX.** Group projects into any categories you like — categories are simply the folders you create under `docs/projects/` (e.g. `clients/`, `products/`, `infra/`). `_archive/` is reserved for closed projects (see `docs/projects/_archive/README.md`). A full, auto-generated `docs/projects/INDEX.md` is rebuilt by the pre-commit hook and flags any project missing a `**Status:**` line.

### Patterns (`docs/patterns/`)

Reusable operational patterns shared across projects:

- **`TRADEOFFS.md`** — decision-making frameworks
- **`OPERATIONS.md`** — common operational procedures
- **`SECURITY.md`** — security guidelines and checklists

### Runbooks (`docs/runbooks/`)

| Runbook | Purpose |
|:--------|:--------|
| **`NEW_EXPERT.md`** | How to add a new AI expert (with or without RAG) |
| **`NEW_VIDEO_COURSE.md`** | How to turn a video course into a RAG knowledge base |
| **`MONTHLY_CLEANUP.md`** | Monthly light cleanup — binary gate, INDEX drift, dead links, gc, secrets (~15–20 min) |
| **`MAINTENANCE.md`** | Quarterly cleaning checklist — artifacts, doc drift, prompt sync, RAG health check |
| **`BRAIN_HTML.md`** | Single-file knowledge viewer (`brain.html`) — build & usage |

### Brain viewer (`brain.html`)

`python3 tools/brain/build.py` generates a single-file offline browser of your whole repo — open `brain.html` with a double-click (sidebar tree, dashboard, `⌘K` search). It rebuilds automatically on every commit once the pre-commit hook is active. See `docs/runbooks/BRAIN_HTML.md`.

### System Context (`docs/SYSTEM_CONTEXT.md`)

Single source of truth for the entire system. Experts read this first, every time. Edit it immediately after cloning — fill in your infra details or simplify for local-only use.

---

## What Omni Brain Is NOT

- Not another RAG chat/app
- Not an autonomous agent
- Not a wrapper over LangChain/CrewAI
- Does not require its own database or complicated deployment
- Not a home for application/product code — that lives in its own repositories; this repo holds knowledge and docs only

It's simply the cleanest way to turn your repo into an intelligent **second brain**.

---

## Where to Go Next

| Document | Purpose |
|:---------|:--------|
| [`onboarding_guide.md`](experts/prompts/onboarding_guide.md) | **Start here** — guided system walkthrough |
| [`NEW_EXPERT.md`](docs/runbooks/NEW_EXPERT.md) | How to add a new expert (with or without RAG) |
| [`NEW_VIDEO_COURSE.md`](docs/runbooks/NEW_VIDEO_COURSE.md) | How to turn an entire video course into RAG |
| [`BRAIN_HTML.md`](docs/runbooks/BRAIN_HTML.md) | Single-file offline knowledge viewer (`brain.html`) |
| [`MONTHLY_CLEANUP.md`](docs/runbooks/MONTHLY_CLEANUP.md) · [`MAINTENANCE.md`](docs/runbooks/MAINTENANCE.md) | Monthly light cleanup · quarterly deep maintenance |
| [`SYSTEM_CONTEXT.md`](docs/SYSTEM_CONTEXT.md) | Global system state — **edit this first** |
| [`contracts.md`](experts/contracts.md) | Expert contracts + routing table |
| [`prompt_engineer.md`](experts/prompts/prompt_engineer.md) | Create, review, or refactor expert prompts |

---

## Directory Structure

```
omni-brain/
├── experts/
│   ├── prompts/              # AI expert prompts (load in your IDE)
│   │   ├── onboarding_guide.md
│   │   └── prompt_engineer.md
│   ├── sync_grounding.py     # Sync shared GROUNDING RULES across prompts
│   └── contracts.md          # Expert contracts + routing table
│
├── domains/
│   └── example_domain/NOTES.md
│
├── rag/
│   ├── library/              # Place PDF/EPUB files here (git-ignored)
│   ├── manifests/
│   ├── indexes/chroma/       # ChromaDB (git-ignored)
│   └── ingest/               # Ingestion + query scripts
│       ├── ingest.py         # PDF/EPUB → ChromaDB
│       ├── ingest_video.py   # Video chunks → ChromaDB
│       ├── query.py          # Multi-stage retrieval
│       └── schema.md
│
├── video_pipeline/           # Video → transcript → chunks pipeline
│
├── tools/
│   ├── projects_index/       # docs/projects/INDEX.md generator (auto-detects categories)
│   └── brain/                # brain.html viewer (build.py, serve.py, template.html, vendor/)
│
├── .githooks/pre-commit      # Rebuild INDEX + brain.html on commit (git config core.hooksPath .githooks)
│
├── docs/
│   ├── SYSTEM_CONTEXT.md     # Global system state (edit this!)
│   ├── projects/
│   │   ├── INDEX.md          # Auto-generated project index
│   │   ├── <your categories>/  # Any folders you create (clients/, products/, infra/…)
│   │   └── _archive/         # Reserved: closed projects
│   ├── runbooks/
│   └── patterns/
│
├── .env.example
├── .gitignore
└── README.md                 # You are here
```

---

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

If this helps you build your second brain — [![GitHub stars](https://img.shields.io/github/stars/MateuszKruhlik/omni-brain?style=social)](https://github.com/MateuszKruhlik/omni-brain)

> *"We shape our tools and thereafter our tools shape us."*
