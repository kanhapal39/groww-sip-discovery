# Implementation Plan — SIP Discovery Engine

Stages run in execution order. Do not advance to the next stage until its approval gate is met.

## Stage 0 — Foundation (complete)

Create project structure, documentation, configuration, and gitignore.

**Approval gate:** All required files exist; basic checks pass; no external credentials required.

**Status: Complete**

## Stage 1 — Configuration verification (complete)

- Verify NVIDIA available models and supported API interface using NVIDIA service documentation.
- Confirm model ID, base URL, and API interface in `config.yaml`.
- Document unresolved decisions; do not guess.

**Approval gate:** `config.yaml` model settings match verified NVIDIA documentation. No API call made.

**Status: Complete**

## Stage 2 — Skeleton modules (complete)

Create empty module files with type stubs in `collect/`, `pipeline/`, `app/`.

**Approval gate:** Modules import without error; `pytest tests/` passes (no external services).

**Status: Complete** — All 16 tests pass. All skeleton modules import cleanly. Unimplemented interfaces raise `NotImplementedError`.

## Stage 2.5 — Source access approval (new gate)

Before Stage 3 (data collection) can begin, every candidate data source must be reviewed and approved.

**Documents reviewed:** `docs/source_access_plan.md` — one section per source (Google Play Store, Apple App Store, Reddit, TradingQ&A, YouTube, Apify Reddit actors). Google Play Store reviews of third-party apps are confirmed unavailable. Reddit is BLOCKED (commercial use + AI/ML training restrictions). YouTube is CONDITIONAL GO (official free API, commercial use not explicitly prohibited).

**Approval gate requirements:**

1. **User explicitly approves each source** after reviewing its access method, terms of service, rate limits, and cost implications.
2. **No source is marked approved** without verified supporting documentation (official API docs or terms of service).
3. **Commercial use terms must be acceptable** for the product (e.g., Reddit free tier is non-commercial only and BLOCKED; YouTube commercial use is permitted per API ToS).
4. **If a paid service is considered (e.g., Apify Reddit actor), actual pricing and maximum potential cost must be presented to the user** before any actor is started or credits consumed.
5. **Google Play / Apple App Store review APIs are only usable for apps we own** — not for third-party investment apps.
6. **Reddit is BLOCKED** pending written clarification or approval from Reddit regarding commercial use and AI/ML training restrictions. Cannot be approved for pilot collection under current terms.
7. **No collection begins** until this gate is met.

**Status: Partially decided** — On 2026-10-26 the user explicitly approved a capped Google Play reviews pilot using an unofficial library, accepting the terms-of-service risk (`docs/source_access_plan.md` §1c). On 2026-10-26 the user also approved a capped YouTube comments pilot through the official API (6 user-selected videos, 200 comments, 4,000-unit quota cap, 30-day retention; §5a). All other sources remain pending.

## Stage 3 — Data collection (pilot)

- Build collectors for approved sources only.
- Run a small pilot collection.
- Log before/after counts, source URLs, timestamps.

**Approval gate:** Pilot run completed; provenance verified on all collected records; no terms-of-service violations.

## Stage 4 — Cleaning and relevance filtering

- Implement cleaning (normalization, length limits, dedup).
- Implement relevance filtering with documented threshold.

**Approval gate:** Before/after counts logged; duplicates removed; relevance threshold documented.

**Status: In progress** — Rule-based cleaning implemented in `pipeline/clean.py` and run on 2026-10-26 (counts in `docs/evidence_log_notes.md` §4.1). On 2026-10-26 the user switched the LLM provider from NVIDIA to Groq and authorized an AI relevance-filter pilot (`pipeline/filter.py`, 100 Play Store items), followed by the full run if at most 2 of the pilot's "no" labels are clearly wrong. YouTube text is excluded from AI processing (§5a).

## Stage 5 — Tagging pipeline

- Implement SIP behavior tagging per `codebook.yaml`.
- Confidence scores and evidence quotes required.
- Observed vs. hypothesis flag on every tag.

**Approval gate:** Tag distribution matches codebook; evidence quotes are verbatim; no invented quotes.

**Status: Pilot only** — On 2026-10-26 the user authorized `pipeline/tag.py` and a 50-item pilot (no full run). Codebook v2 fields are a draft awaiting human review. Pilot results in `docs/evidence_log_notes.md` §5.1; candidate review workbook §5.2.

## Stage 6 — Validation and export

- Validate records against codebook constraints.
- Export to `data/export/`; generate review workbooks in `data/review/`.

**Approval gate:** All exported records pass validation; review workbooks open correctly.

## Stage 7 — Human review and Golden Dataset

**Status (2026-10-26):** 300-row stratified sample created and bulk-approved by the project owner without row-by-row review (evidence log §7.1). Individual review is outstanding.

- Reviewers approve/reject/request revision per record.
- Approved records enter Golden Dataset (`data/manual/`).

**Approval gate:** Golden Dataset approved; review log complete.

## Stage 8 — Dashboard

- Build Streamlit app in `app/`.
- Display tag distributions, evidence quotes, product opportunities.
- Separate observed evidence from hypotheses.

**Approval gate:** Dashboard runs locally; no invented statistics shown.

**Status: Implemented, local only (2026-10-26).** Five header-navigation pages (Overview with grounded research assistant, Investor Behaviour, Product Opportunities, Evidence Explorer, Data Quality & Validation) in `app/`, backed by `research/`. All figures are computed from `data/manual/golden_dataset.jsonl` via `python -m research.build`. Smoke-tested with Streamlit's test runner and a local server; visual review of the layout by a person is still outstanding. Not implemented: HTTP API, scheduler, multi-user authentication.

## Stage 9 — Testing and deployment

- Add unit and integration tests.
- Run full test suite.
- Document deployment target (TBD).

**Approval gate:** `pytest tests/` passes; deployment target documented.

## Testing approach

- Unit tests for cleaning, filtering, tagging, validation logic.
- No tests require NVIDIA API credentials or external services.
- Mock any external dependency in tests.

## Unresolved decisions

- Specific collection sources.
- NVIDIA model ID and endpoint.
- Relevance threshold.
- Production deployment target.
