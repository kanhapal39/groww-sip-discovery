# SIP Discovery Engine

Research platform for understanding why investors start, continue, pause, reduce or stop their Systematic Investment Plans (SIPs). It collects public discussions, cleans and classifies them, tags investor behaviour, builds a reviewed Golden Dataset, ranks evidence-backed product opportunities and shows the findings in a Streamlit dashboard with a grounded research assistant.

The project distinguishes observed evidence from hypotheses and must not invent findings, quotations or statistics.

## Status (2026-10-26)

| Stage | State |
|---|---|
| Collection | Google Play (5 apps, 150,000 reviews), YouTube (6 videos, 198 comments), Reddit via Apify (583 rows). App Store and TradingQ&A not integrated |
| Cleaning | Done: 62,878 clean records |
| Relevance filter | Running in the background (partial) |
| Tagging | Running in the background (gpt-oss-120b and qwen3.8-27b, Reddit first) |
| Golden Dataset | 296 rows, recorded as individually reviewed by the project owner on 2026-10-27 (evidence log §7.2). On 2026-10-28, on the owner's decisions: 26 tag corrections on 16 records (D-3, §8.5), 19 more on 11 labelled records and 4 not-relevant rows rejected (§8.6) |
| AI evaluation | Audit and edge-case tests done (`docs/ai_eval_test_report.md`). 20-record labelled set drawn, **not yet labelled**, so no accuracy figures exist |
| Dashboard | Five pages implemented; tested locally |

See `docs/evidence_log_notes.md` for every decision and count.

## Quick start

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-pipeline.txt
cp .env.example .env              # add keys; never commit .env
python -m research.build          # index the Golden Dataset and compute quality metrics
streamlit run app/streamlit_app.py
pytest tests/
```

## Dashboard pages

Overview (question box, five suggested questions, evidence summaries) · Investor Behaviour (behaviour, expectations, discontinuation tabs) · Product Opportunities · Evidence Explorer · Data Quality & Validation. Navigation is in the page header.

## Layout

- `collect/` — source connectors (Play Store, YouTube, Reddit via Apify)
- `pipeline/` — cleaning, relevance filter, tagging, review export and Golden Dataset promotion
- `research/` — Golden Dataset store and index, retrieval, analysis, opportunities, grounded answers, quality metrics
- `app/` — Streamlit frontend
- `tests/` — unit and smoke tests (no network)
- `data/` — all data, gitignored
- `docs/` — brief, plans, architecture, policies, limitations, evidence log

## Documentation

`docs/architecture.md`, `docs/implementation_plan.md`, `docs/data_dictionary.md`, `docs/golden_dataset_policy.md`, `docs/evidence_validation.md`, `docs/limitations.md`, `docs/deployment.md`, `docs/source_access_plan.md`, `docs/evidence_log_notes.md`.

AI evaluation: `docs/ai_evaluation_documentation.md`, `docs/edge_cases_and_failure_modes.md`, `docs/ai_eval_implementation_audit.md`, `docs/ai_eval_test_report.md`, `docs/ai_eval_ground_truth_template.md`.

## LLM provider

Groq (`GROQ_API_KEY` in `.env`). Credentials are never committed.
