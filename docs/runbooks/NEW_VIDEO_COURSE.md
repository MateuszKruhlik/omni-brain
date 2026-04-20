# Runbook: Adding a New Video Course to RAG

**Last updated:** <YYYY-MM-DD>
**Existing deployments:** *add yours here*

---

## When to Use This Runbook

When you want to add a new video course to the RAG system. Pipeline: Video → Audio → Transcription → Chunks → Embeddings.

> **Difference vs NEW_EXPERT.md:**
> - NEW_EXPERT.md = adding an AI expert (prompt + contract + optionally RAG from PDF/EPUB)
> - NEW_VIDEO_COURSE.md = adding a knowledge source from video

---

## Pre-flight: Decisions to Make

| # | Question | Example |
|---|----------|--------|
| 1 | Course slug (snake_case) | `example_course` |
| 2 | Video folder structure | `Module/Submodule/Lesson.mp4` or flat |
| 3 | Course language | `en` (WhisperX auto-detect) |
| 4 | Estimated length | ~10h = ~200 chunks |
| 5 | Target RAG domain | `video` or specific (e.g., `cooking`) |

---

## Phase 1: Set Up Structure

### 1.1 Create the course folder
```bash
mkdir -p video_pipeline/<course_slug>/{input,audio,transcripts,chunks,glossary,knowledge_map,summaries,manifests,reports,logs,scripts}
```

### 1.2 Copy scripts from the template
> [!WARNING]
> **WATCH OUT FOR HARDCODED PATHS!**
> Scripts may contain hardcoded paths. Always review `.py` files and clean up old paths/JSON keys if copying from another course instead of the clean template!

```bash
cp video_pipeline/example_course/scripts/*.py video_pipeline/<course_slug>/scripts/
```

### 1.3 Copy or symlink source video
```bash
# Option A: Symlink (saves disk space)
ln -s /path/to/course/videos video_pipeline/<course_slug>/input

# Option B: Copy (independent)
cp -r /path/to/course/videos/* video_pipeline/<course_slug>/input/
```

### 1.4 Create venv (if no global one exists)
```bash
cd video_pipeline/<course_slug>
python3 -m venv .venv
source .venv/bin/activate
pip install whisperx torch torchaudio
```

---

## Phase 2: Build Manifest

### 2.1 Run the manifest builder
```bash
python scripts/build_manifest.py --input input --output manifests/video_manifest.jsonl
```

### 2.2 Verify the output
```bash
wc -l manifests/video_manifest.jsonl  # Number of lessons
head -1 manifests/video_manifest.jsonl | jq .  # Structure
```

**Verify:**
- [ ] `lesson_id` is unique per lesson
- [ ] `module` and `submodule` correctly detected
- [ ] `duration_sec` is reasonable (not 0)

---

## Phase 3: Transcription

### 3.1 Extract audio (if the script handles it)
```bash
# If batch_transcribe.py does this automatically, skip
# Otherwise: ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav
```

### 3.2 Pilot test (1 lesson)
```bash
python scripts/batch_transcribe.py --manifest manifests/video_manifest.jsonl --pilot
```

**Check:**
- [ ] `transcripts/lesson_*.json` created
- [ ] JSON has `segments` with `words` (word-level timestamps)
- [ ] Language detected correctly

### 3.3 Full transcription
```bash
python scripts/batch_transcribe.py --manifest manifests/video_manifest.jsonl
```

> ⚠️ **Time:** ~1x realtime on GPU, ~5x on CPU. A 40h course = 40h+ on CPU.

---

## Phase 4: Chunking

### 4.1 Batch chunk
```bash
python scripts/batch_chunk.py
```

Default parameters (in `chunk_transcript.py`):
- `target_words=500`, `max_words=800`, `min_words=300`
- `overlap_ratio=0.15`
- `pause_threshold=0.8`

### 4.2 Chunk audit
```bash
# If you have an audit script:
python scripts/audit_chunks.py --output reports/chunk_audit.md
```

**Check `chunk_audit.md`:**
- [ ] `missing_keys: 0`
- [ ] `empty_text: 0`
- [ ] `avg word_count` ~500

---

## Phase 5: Metadata Enrichment

### 5.1 Glossary + Knowledge Map (heuristic)
```bash
python scripts/batch_glossary_and_map.py
python scripts/build_global_knowledge_map.py
```

### 5.2 Summaries (extractive placeholder)
```bash
# If you have the script:
python scripts/batch_summaries.py
```

### 5.3 Build summaries index
```bash
python scripts/build_summaries_index.py
```

---

## Phase 6: Embedding + RAG Integration (TODO v1.1)

### 6.1 Embed chunks
```bash
# Using the same flow as PDF/EPUB:
rag/.venv/bin/python rag/ingest/ingest_video.py --course <course_slug>
```

### 6.2 Test retrieval
```bash
rag/.venv/bin/python rag/ingest/query.py "your query" --mode expert --domain video --debug
```

**Check:**
- [ ] Evidence Pack contains chunks from the new course
- [ ] `source_type=video` in metadata
- [ ] Timestamp (`start_time_hms`) instead of page

---

## Phase 7: Documentation

| File | What to update |
|------|----------------|
| `docs/SYSTEM_CONTEXT.md` | Section 3.1 (RAG status) |

---

## Final Checklist

```
[ ] Folder structure created
[ ] Manifest built, lesson_id unique
[ ] Transcription: pilot OK + batch OK
[ ] Chunking: audit without critical issues
[ ] Glossary + knowledge map generated
[ ] Summaries index created
[ ] (v1.1) Embeddings in ChromaDB
[ ] (v1.1) Retrieval test OK
[ ] Docs updated
```

---

## Known Gotchas

1. **WhisperX requires GPU** — on CPU it's 5-10x slower. Use GPU if available.
2. **Audio quality matters** — noise, background music, and strong accents reduce transcription quality.
3. **Input folder structure** — `build_manifest.py` assumes `Module/Submodule/Lesson.mp4`. Flat structure requires modifications.
4. **Large MP4 files** — for long lessons (>2h), consider splitting before transcription.
5. **Summaries are extractive** — until v1.1, don't rely on the summary field, use full transcripts.
6. **venv isolation** — WhisperX has different deps than RAG. Use a separate venv for the video pipeline.

---

## TODO / Technical Debt
- [ ] Build a central `video_pipeline/template_scripts/` directory with clean scripts that have no hardcoded parameters. Scripts should rely *only* on CLI arguments.

---

## Example Commands (example_course)

```bash
cd video_pipeline/example_course
source .venv/bin/activate

# Full pipeline
python scripts/build_manifest.py --input input --output manifests/video_manifest.jsonl
python scripts/batch_transcribe.py --manifest manifests/video_manifest.jsonl
python scripts/batch_chunk.py
python scripts/batch_glossary_and_map.py
python scripts/build_global_knowledge_map.py
python scripts/build_summaries_index.py
```
