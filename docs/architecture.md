# Architecture — SIP Discovery Engine

This document describes the code that exists today. Gaps are listed at the end.

## Data flow

```
collect/ (connectors) ──> data/raw/*.jsonl
        │
pipeline/clean.py ──────> data/processed/clean.jsonl, dropped.jsonl
        │
pipeline/filter.py ─────> data/processed/filter_results.jsonl   (Groq gpt-oss-20b: yes / no / unsure)
        │
pipeline/tag.py ────────> data/processed/tag_results*.jsonl     (Groq gpt-oss-120b / qwen3.8-27b, codebook.yaml)
        │
pipeline/export.py ─────> data/review/*.xlsx  ──(human review)──>  data/manual/golden_dataset.jsonl  [authoritative]
        │
research/build.py ──────> data/processed/research.db (SQLite + FTS5), quality_metrics.json   [rebuildable]
        │
app/ (Streamlit) ───────> five pages; research assistant calls Groq per question
```

## Components

| Concern | Where | Notes |
|---|---|---|
| Frontend | `app/streamlit_app.py`, `app/views/*.py`, `app/ui.py`, `.streamlit/config.toml` | Streamlit 1.50, header navigation (`st.navigation(position="top")`), five pages |
| Backend service layer | `research/` | Python modules called in-process by the frontend. **There is no separate HTTP API.** |
| Source connectors | `collect/play_store.py`, `collect/youtube.py`, `collect/reddit_apify.py` | Each writes RawRecord JSONL with record ID, source URL, collection timestamp |
| Ingestion runner | `collect/run_all.py` (Play Store, YouTube), `collect/reddit_apify.py` CLI (Reddit steps) | Manual CLI runs |
| Cleaning & deduplication | `pipeline/clean.py` | Rule-based; rapidfuzz near-duplicates; every dropped item kept with a reason |
| Relevance filter | `pipeline/filter.py` | Groq LLM + keyword safety net; resumable, rate-limit aware |
| Classification & tagging | `pipeline/tag.py`, `codebook.yaml` | Groq LLMs; validation against the codebook; quote checks; resumable |
| Golden Dataset management | `pipeline/export.py` | Review workbooks, stratified sample, promotion of approved rows with provenance |
| Evidence validation | `pipeline/tag.py` (quote/reason checks), `pipeline/export.py` (provenance), `research/store.py` (public eligibility) | See `docs/evidence_validation.md` |
| Search & retrieval | `research/store.py`, `research/retrieval.py` | SQLite FTS5 + question-to-tag rules; no vector index |
| Research analysis | `research/analysis.py` | Distributions with sample sizes; emerging-theme guard |
| Product opportunities | `research/opportunities.py`, `research/opportunities.yaml` | Human-authored definitions, evidence counted from data |
| Grounded answers | `research/answer.py` | Insufficiency rule, citation validation, computed coverage and limitations |
| Data quality metrics | `research/quality.py`, `research/build.py` | Computed from pipeline files |
| Authentication & authorisation | `app/data.py` (`admin_login`) | Single administrator password from `.env` (`ADMIN_PASSWORD`); public viewers see approved, eligible records only |
| Scheduling & background jobs | — | **Not implemented.** Long runs use `nohup … --auto-resume` started by hand |
| Logging & monitoring | `data/processed/*.log`, `*_usage.jsonl`, Reddit ledger | Plain files; shown to administrators on the Data Quality page. No alerting |

## Storage

- **Authoritative:** `data/manual/golden_dataset.jsonl` — written only by `python -m pipeline.export golden` from rows a reviewer marked "approved". Recoverable by re-running that command on the review workbook.
- **Rebuildable index:** `data/processed/research.db` — table `golden` (one row per record) and FTS5 table `golden_fts`. Delete and rebuild with `python -m research.build`.
- **Pipeline files:** JSONL under `data/raw/` and `data/processed/`; workbooks under `data/review/`. All `data/` folders are gitignored.

## Configuration and secrets

- `config.yaml` — models, paths, thresholds, collection settings, research-assistant settings.
- `codebook.yaml` — tagging fields and rules (v3, draft).
- `research/opportunities.yaml` — opportunity definitions (draft hypotheses).
- `.env` — secrets only (`GROQ_API_KEY`, `YOUTUBE_API_KEY`, `APIFY_TOKEN`, `ADMIN_PASSWORD`), gitignored. `.env.example` lists the names with placeholders.

## LLM provider

Groq (OpenAI-compatible, `https://api.groq.com/openai/v1`). Models: `openai/gpt-oss-20b` (filter), `openai/gpt-oss-120b` (tagging, research assistant), `qwen/qwen3.8-27b` (second tagger). The project switched from NVIDIA NIM on 2026-10-26 (evidence log §4.2); NVIDIA is no longer used.

## Known architectural gaps

- No HTTP API; the frontend imports the service layer directly.
- No scheduler; collection, filtering and tagging are started manually.
- Single shared administrator password; no user accounts or roles.
- No vector/semantic search; retrieval is keyword and tag based.
- No monitoring or alerting beyond log files.
