# SECURITY PATTERNS

## Secrets Management
- **Local**: stored in `.env` file at root (git-ignored).
- **Server**: injected via environment variables or protected `.env` files.
- **Docs**: Reference secrets by NAME only (e.g., `MY_SERVICE_SECRET`), never value.

## Access Control
- **mTLS**: Preferred for service-to-service communication if exposed.
- **Tailscale**: Preferred for remote access (no open ports).

## LLM/AI Service Exposure
- **Ollama API** (`:11434`): No auth by default. Restrict to LAN only. Never expose to WAN.
- **LiteLLM** (`:4000`): Set a strong master key in `.env`. LAN only.
- **OpenWebUI** (`:3000`): Consider enabling `WEBUI_AUTH=true` if accessible beyond localhost.
- **Langfuse** (`:3001`): Regenerate default secrets (NEXTAUTH_SECRET, SALT, DB password) before any external exposure.
