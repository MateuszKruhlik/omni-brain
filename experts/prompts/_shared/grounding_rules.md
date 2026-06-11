<!--
  CANONICAL GROUNDING RULES block for every RAG-backed expert.
  This file is the SOURCE OF TRUTH — do not edit the copies inside prompts.

  To change the grounding policy:
    1. edit this file,
    2. run: python3 experts/sync_grounding.py --write

  Placeholders (filled per expert from the EXPERTS config in sync_grounding.py):
    {{RAG_EXAMPLE_1}}, {{RAG_EXAMPLE_2}} — example citations with REAL book_ids
    {{GK_EXAMPLE_1}}, {{GK_EXAMPLE_2}}  — example general-knowledge entries
-->
1. **No phantom sources.** You may ONLY cite `book_id`, `title`, `page`/`location` that **literally appeared** in the Evidence Pack terminal output. Copy them exactly — do NOT invent book_ids, do NOT guess chapter names, do NOT use `[0000]` or any placeholder. If a source was NOT in the retrieval results, you CANNOT cite it.
2. **Video citations use timestamps.** For video sources, `location` is a timestamp — cite as `[book_id] Lesson title @ HH:MM:SS`.
3. **No fake quotes from dirty chunks.** If a chunk contains OCR artifacts, garbled text, or encoding errors — do NOT quote it verbatim. Instead either:
   - use a different chunk, or
   - paraphrase with the label: `paraphrase based on [Title, p.X]`
4. **Evidence audit block.** At the very end of your response, append this exact structure with TWO separate sections:
   ```
   ---
   Evidence used (RAG):
   - {{RAG_EXAMPLE_1}}
   - {{RAG_EXAMPLE_2}}

   General knowledge (not in RAG):
   - {{GK_EXAMPLE_1}}
   - {{GK_EXAMPLE_2}}
   ```
   Rules for this block:
   - **RAG section**: Copy `book_id`, `title`, `page`/`location`, and `score` EXACTLY from the Evidence Pack header lines. Do NOT round, rename, or fabricate.
   - **General knowledge section**: List any concepts, frameworks, or authors you referenced that did NOT come from the Evidence Pack. Be specific (author + concept name).
   - If you used ONLY RAG sources, write `General knowledge (not in RAG): none`.
   - If RAG returned nothing, write `Evidence used (RAG): none` and list everything under General knowledge.
