# SYSTEM CONTEXT (Local-First Multi-Expert System)

**Date:** <YYYY-MM-DD>
**Source of Truth:** Laptop (Local-First)
**Runtime Environment:** Dual-Server Architecture (optional)
- **Server A** @ <YOUR_SERVER_A_IP> — Media & Automation Hub
- **Server B** @ <YOUR_SERVER_B_IP> — Compute Worker

> [!IMPORTANT]
> This system follows a **Local-First** architecture for logic and planning, with optional server runtime.
> - **Brain (Laptop)**: Documentation, planning, prompts, RAG index.
> - **Storage & Media (Server A)**: Docker containers, automation workflows, media storage.
> - **Compute (Server B)**: Heavy processing (WhisperX, video pipeline), GPU-capable workloads.
>
> You can run everything locally on a single machine — the dual-server setup is optional.

---

## 1. FUNDAMENTAL PRINCIPLES (Local-First Agent)

### 1.1 Storage & Source of Truth
- **Laptop**: Primary Source of Truth for *context*. Holds `SYSTEM_CONTEXT.md`, project docs, expert prompts, and domain NOTES.
- **Server**: "Warehouse" and "Factory". Stores heavy files (PDF/EPUB), backups, and runs the actual stacks (Docker).
- **Access**: Agent uses local file paths for context, and SSH/network for server operations.

### 1.2 Secrets & Security
- **Rule**: Secrets NEVER go into markdown documentation.
- **Location**: Secrets reside ONLY in `.env` files (local or server).
- **Reference**: Docs refer to secrets by variable name (e.g., `NOTION_TOKEN`), never by value.

---

## 2. SERVER INFRASTRUCTURE (Runtime Reality)

> [!NOTE]
> Fill in this section with your own server details. Below is an example structure.

### 2.1 Service Architecture
- **Docker management**: Dockge, CasaOS, or Portainer — your choice.
- **Monitoring**: Beszel, Uptime Kuma, or similar.
- **Automation**: n8n, Home Assistant, or custom scripts.

### 2.2 Network Infrastructure
- **Router**: Your home router or dedicated networking device.
- **DNS filtering**: AdGuard Home, Pi-hole, etc.
- **Remote access**: Tailscale, WireGuard, Cloudflare Tunnel.

---

## 3. LOCAL ARCHITECTURE (The "Brain")

### 3.1 Directory Structure (Laptop)
- `/docs`: Project documentation, patterns, logs.
- `/experts`: Prompts and contracts for AI experts.
- `/domains`: Knowledge captures (NOTES.md).
- `/rag`: Vector indexes (ChromaDB `unified_library`), library manifests.
- `/video_pipeline`: Video course processing (WhisperX transcription → chunking → RAG).

### 3.2 RAG Sources
| Source Type | Pipeline | Status | Runbook |
|-------------|----------|--------|---------|
| PDF/EPUB | `rag/ingest/ingest.py` | Template (0 chunks) | `NEW_EXPERT.md` |
| Video | `video_pipeline/scripts/*` | Template (0 chunks) | `NEW_VIDEO_COURSE.md` |

### 3.3 Expert Workflow
Each expert follows a consistent pattern:
1. Read `SYSTEM_CONTEXT.md` for global constraints
2. Read project `SUMMARY.md` + `decisions.md` for project-specific context
3. Read domain `NOTES.md` for accumulated knowledge
4. (If RAG-backed) Query `rag/ingest/query.py` for evidence from books/videos
5. Produce structured output per their contract

---

## 4. UNIVERSAL PATTERNS
- **Tradeoffs**: `docs/patterns/TRADEOFFS.md`
- **Operations**: `docs/patterns/OPERATIONS.md`
- **Security**: `docs/patterns/SECURITY.md`

## 5. HARD CONSTRAINTS (NEVER VIOLATE)
- **Rollback Safety**: Never recommend risky actions without an explicit rollback plan.
- **Server State**: Never suggest restarting an entire server without explicit instruction.
- **Storage Rules**: Respect SSD/HDD segregation (SSD for apps/downloads, HDD for media).
- **Permissions**: Assume permission issues in container persistence are common until evidence says otherwise.

---

## 6. ACTIVE PROJECTS (Local)
> List your active projects here. Each project should have a folder in `docs/projects/<project_name>/`
> with at minimum a `SUMMARY.md` file.

*No projects configured yet. See `docs/projects/example_project/` for the template.*
