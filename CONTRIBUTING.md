# Contributing to Omni Brain

Thank you for your interest in contributing! This document explains how to get involved.

## Ways to Contribute

- **Add an Expert** — Create a new AI expert prompt following the runbook at `docs/runbooks/NEW_EXPERT.md`
- **Improve Documentation** — Fix typos, clarify instructions, add examples
- **Report Bugs** — Open an issue describing what went wrong and how to reproduce it
- **Suggest Features** — Open an issue with a clear description of the feature and its use case

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/omni-brain.git`
3. Create a branch: `git checkout -b feature/my-feature`
4. Set up the environment:
   ```bash
   cp .env.example .env
   # Fill in your API keys
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r rag/ingest/requirements.txt
   ```
5. Make your changes
6. Test your changes (especially RAG ingestion/query if you touched Python code)
7. Commit and push: `git push origin feature/my-feature`
8. Open a Pull Request

## Code Style

- **Python**: Follow PEP 8. Use type hints for function signatures.
- **Markdown**: Use ATX-style headers (`#`). Keep lines readable.
- **Expert Prompts**: Follow the structure in `experts/contracts.md` — every expert needs Scope, Input/Output Contract, and Grounding Rules.

## Commit Messages

Use conventional commit style:
- `feat: add new expert for <domain>`
- `fix: correct manifest parser for <edge case>`
- `docs: update runbook for <topic>`

## Questions?

Open an issue or start a discussion. We're happy to help!
