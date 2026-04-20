# TRADEOFFS & ARCHITECTURE DECISIONS

## Local-First vs. Server-Centric
- **Decision**: Local-First for logic and context.
- **Tradeoff**: Laptop must be available for heavy inference/indexing, but guarantees privacy and offline capability for planning.

## LLM Inference: Compute/Frontend Split
- **Decision**: Ollama (inference) on Server B (compute), OpenWebUI+LiteLLM (frontend/proxy) on Server A (gateway).
- **Tradeoff**: Network latency between servers (~1ms LAN) vs. gateway CPU too weak for inference. Split wins.
- **Alternative rejected**: GPU acceleration via iGPU — potential 2x speedup but costs significant RAM (VRAM shared from system RAM) + complex driver setup. Evaluate based on your hardware.

## LLM Proxy: LiteLLM vs. Direct Ollama
- **Decision**: LiteLLM as unified proxy for both local (Ollama) and cloud (OpenRouter) models.
- **Tradeoff**: Extra hop + container, but gives unified API, model routing, and Langfuse cost tracking across all providers.

## RAG Retrieval Granularity
- **Decision**: Page-level (chunks = pages).
- **Tradeoff**: Less precise than sentence-level, but preserves full semantic context of the author's argument.
- **Ingestion**: Deterministic Page-Level (No LLM).
  - **Decision**: 1 Page = 1 Record. Cleaned deterministically.
  - **Why**: Faster, cheaper, reproducible. No token-splitting artifacts.

