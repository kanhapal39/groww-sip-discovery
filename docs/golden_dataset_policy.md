# Golden Dataset policy

## What it is

The Golden Dataset is the set of tagged records a human reviewer has approved. It is the only data the dashboard and research assistant use. It lives in `data/manual/golden_dataset.jsonl` (gitignored) and is the authoritative copy; the SQLite index is rebuilt from it.

## How records get in

1. Records are cleaned, filtered and tagged by the pipeline.
2. `python -m pipeline.export sample --size 300 [--tagged-by MODEL]` writes a review workbook (`data/review/golden_sample_300.xlsx`) with rows sampled across source × behaviour; every row starts "pending".
3. A reviewer sets `review_status` to approved, rejected or needs_revision, with corrections in `reviewer_notes` and their name in `reviewer`.
4. `python -m pipeline.export golden` promotes only "approved" rows, adds provenance (source, collected_at, published_at, context) from the clean record, and refuses any row without a clean record and collection timestamp.
5. `python -m research.build` rebuilds the dashboard index.

The sample workbook is never overwritten once any row has been reviewed (unless `--force`).

## Current state (2026-10-26)

- 300 rows, all tagged by `openai/gpt-oss-120b` (tag-v4, codebook v3 draft).
- **All 300 were bulk-approved by the project owner without row-by-row review** (evidence log §7.1). Each row carries reviewer "project owner (bulk)" and a note saying so. The dashboard shows "0 individually validated" and labels every finding "(unverified)".
- Consequence: the dataset can be used to explore and cite evidence, but must not be presented as human-verified ground truth or used to measure tagging accuracy.

## Upgrading a row to verified

Review the row, put a person's name in `reviewer`, remove the bulk note, keep or correct the tags in notes, and re-run `export golden` and `research.build`.

## Eligibility for public display

A row is public when it is approved, comes from a publishable source (Play Store or Reddit), and has record ID, source URL and collection timestamp. YouTube comments are never eligible (30-day retention limit; no external AI processing). Reviewer name and notes, review status and stratum are hidden from public viewers.

## Sampling caveat

The sample is balanced across behaviours to make review efficient, so its distributions are not prevalence estimates.
