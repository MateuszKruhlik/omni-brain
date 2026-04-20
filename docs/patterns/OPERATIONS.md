# OPERATIONS PATTERNS

## Core Principles
1. **Local-First**: Always verify locally before deploying stateful changes.
2. **Idempotency**: Automations should be re-runnable without side effects.
3. **Observability**: Logs should be text-based and easy to grep (stored in `docs/logs` or standard stdout).

## Deployment Stacks
- **Server A**: Main runtime for automations (n8n, Docker).
- **Server B**: Compute worker (WhisperX, LLM inference).
- **Laptop**: Development and configuration management.

## Adding a New Expert (with or without RAG)
**Full runbook:** [`docs/runbooks/NEW_EXPERT.md`](../runbooks/NEW_EXPERT.md)

Quick checklist (details + gotchas in runbook):
1. **Code** 🔖: `DOMAIN_MAP` + `domain_titles` + manifest parser branch in `ingest.py`
2. **Intent packs** 🔖: 3–5 domain-specific packs in `query.py`
3. **Library** 🔖: `rag/library/<domain>/` + PDF/EPUB files
4. **Manifest** 🔖: `### <Section>` + book entries `[PENDING]` in `library_manifest.md`
5. **Ingest** 🔖: `ingest.py --dry-run` → verify → `ingest.py`
6. **Test** 🔖: `query.py "<query>" --mode expert --domain <domain> --debug`
7. **Expert**: contract + prompt (with grounding rules 🔖) + domain NOTES + router
8. **Docs**: SUMMARY + decisions + risks + SYSTEM_CONTEXT

🔖 = only for RAG-backed experts

## Monitoring (Beszel / Uptime Kuma)
1. **Sensor Exclusion**: Use `SENSORS=-sensor_name` environment variable in agent config to exclude problematic sensors.
2. **Multi-Server Setup**: Hub on Server A, agents on all servers. Same KEY for all agents.
3. **Adding New Host**: In monitoring UI → Add System → copy KEY → deploy agent with that KEY.

## LLM Stack (Ollama + LiteLLM + OpenWebUI)
1. **Embedding Offload**: RAG embeddings (nomic-embed-text) can run on a separate Ollama instance. Configure in OpenWebUI: Admin → Settings → Documents → Embedding Engine = Ollama, URL = `http://<YOUR_COMPUTE_SERVER>:11434`.
2. **Model Management**: Pull/remove models via `docker exec ollama ollama pull <model>` or `ollama rm <model>`.
3. **LiteLLM Config Reload**: After editing config, restart the container.
4. **Concurrent Workloads**: Ollama and WhisperX video pipeline should NOT run simultaneously on RAM-limited machines.
5. **Cost Tracking**: Cloud models (via OpenRouter) show real costs. Local models (Ollama) show $0 but track token counts.

## Dashboard
1. **API Key**: Generate via your dashboard's management interface.
2. **Apps vs Integrations**: Apps = links (no API). Integrations = live data widgets.
3. **Widget Limitations**: Most widgets poll every ~10-30s, not real-time.
