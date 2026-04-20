# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT** open a public issue
2. Email the maintainer directly (or use GitHub's private vulnerability reporting if enabled)
3. Include a description of the vulnerability, steps to reproduce, and potential impact

We will acknowledge receipt within 48 hours and provide a fix timeline.

## Scope

This project is a local-first template — it runs on your machine and does not expose network services by default. However, security concerns may include:

- **API key exposure** — Keys in `.env` should never be committed. The `.gitignore` excludes `.env` files.
- **RAG content leakage** — ChromaDB indexes and PDF/EPUB files are git-ignored. Do not commit them.
- **Git history** — If you fork this template, ensure no secrets exist in your commit history before making the repo public.

## Best Practices

- Always use `.env` for secrets (never hardcode in markdown or Python)
- Review `.gitignore` before your first commit
- Use `git-filter-repo` or an orphan branch if you need to clean history
