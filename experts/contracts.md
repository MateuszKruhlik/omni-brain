# Expert Contracts (Single Source of Truth)

Purpose: clear role boundaries to avoid overlap and chaos.
Every expert operates in: **Input → Output → Not in scope** mode.

---

## 0) onboarding_guide — START HERE
**Decision types:** first-run orientation, repo walkthrough, system explanation, initial configuration.
**Inputs:** new user opening the repo for the first time (or asking "how does this work?").
**Outputs:** step-by-step guided tour (7 steps) — architecture → folders → experts → domains → RAG → video pipeline → first config.
**Not in scope:** domain-specific advice (hand off to the relevant expert).
**Sources priority:** SYSTEM_CONTEXT.md → contracts.md → example_project.

---

## 1) prompt_engineer
**Decision types:** prompt structure, instruction clarity, Input/Output Contract enforceability, scope consistency with expert ecosystem.
**Inputs:** mode (create/review/refactor) + expert role description or existing prompt + (optional) domain constraints, output examples.
**Outputs:**
- Review: audit table + top 3 issues + prioritized change list.
- Refactor: refactored prompt + key changes diff + architectural notes.
- Create: new prompt + proposed contract entry + architectural notes.
**Not in scope:** API integration code, domain knowledge evaluation (e.g., whether a training plan is effective), routing decisions.
**Sources priority:** `experts/contracts.md` (scope verification) → existing prompt → user provided context.

---

## Routing rule of thumb

Pick by **decision type**, not by topic.

| Decision type | Expert | Example queries |
|---|---|---|
| First run, system orientation, repo tour | `onboarding_guide` | "How does this work?", "Where do I start?" |
| Prompt structure, review, optimization | `prompt_engineer` | "Review my expert prompt", "Create a new expert" |

> **Add more rows** as you create new experts. Follow the pattern above.

**If unsure:** pick the closest match. If a query spans two experts, split by decisions.
