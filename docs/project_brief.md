# Project Brief — SIP Discovery Engine

## Product objective

Build an AI-powered investor research platform that helps understand why people start, continue, pause, reduce, or stop their Systematic Investment Plans (SIPs). The platform collects permitted public discussions, cleans and classifies the data, tags investor behaviour, builds an approved Golden Dataset, identifies evidence-backed product opportunities, and displays findings in a Streamlit dashboard.

## Users

- Product managers investigating SIP behavior drivers
- Researchers analyzing investor decision-making
- Compliance/legal reviewers ensuring data-use boundaries

## Research questions

1. What triggers investors to start a SIP?
2. What factors lead investors to continue a SIP?
3. What causes investors to pause, reduce, or stop a SIP?
4. Which product opportunities are supported by observed evidence vs. hypotheses?

## Data sources

- Permitted public discussions only (forums, social media, review platforms where collection is allowed by terms of service).
- Candidate sources assessed in `docs/source_access_plan.md`: Google Play Store reviews, Apple App Store reviews, Reddit, TradingQ&A, YouTube, Apify Reddit actors.
- **No source is approved for collection.** Each source requires explicit approval after review of its access method, terms of service, rate limits, and cost.
- No data has been collected yet.

## Data-quality rules

1. Every record must carry provenance: source URL, collection timestamp, stable record ID.
2. No fabricated findings, quotations, or statistics.
3. Distinguish observed evidence from hypotheses explicitly.
4. Minimum and maximum text length enforced during cleaning.
5. Duplicates removed by source URL.
6. Relevance filtering applied before tagging (threshold TBD).

## Tagging requirements

- Tag each record with one SIP behavior: start, continue, pause, reduce, or stop.
- Each tag requires a confidence score (0.0–1.0) and an optional verbatim evidence quote.
- Mark each tag as observed evidence or hypothesis.
- Tag definitions live in `codebook.yaml`.

## Golden Dataset policy

- Human-labeled subset of records forms the Golden Dataset.
- Golden Dataset records must be reviewed and approved before use.
- Approval workflow documented in implementation plan.
- Stored in `data/manual/` (gitignored).

## Dashboard requirements

- Built with Streamlit.
- Display tag distributions, evidence quotes, and product opportunities.
- Clearly separate observed evidence from hypotheses.
- No invented statistics.

## Human-review workflow

1. Pipeline produces tagged candidates.
2. Human reviewer approves, rejects, or requests revision per record.
3. Approved records enter the Golden Dataset.
4. Review workbooks stored in `data/review/` (gitignored).

## Deployment target

- Local Streamlit app for initial review.
- Unresolved: production deployment target (cloud/platform TBD).

## Unresolved decisions

- Which source(s) to approve for pilot collection (see `docs/source_access_plan.md` for assessment).
- NVIDIA model ID and endpoint (to be verified against NVIDIA documentation; model access not yet verified).
- Relevance score threshold.
- Production deployment target.
