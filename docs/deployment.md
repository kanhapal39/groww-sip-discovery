# Deployment

## Local (the only tested target)

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-pipeline.txt
cp .env.example .env            # fill in real values; never commit .env
python -m pipeline.export golden   # if the review workbook has approved rows
python -m research.build           # writes data/export/golden_public.jsonl and quality_metrics.json
streamlit run app/streamlit_app.py # http://localhost:8501
```

The dashboard reads only `data/export/golden_public.jsonl` and `data/export/quality_metrics.json` (written by `research.build`) and builds its search index in a temporary folder at startup. Without them every page shows an empty state.

## Secrets

Read at runtime from `st.secrets` (Streamlit Community Cloud), then environment variables, then `.env` in the project root: `GROQ_API_KEY` (research assistant), `ADMIN_PASSWORD` (administrator view). Collectors also need `YOUTUBE_API_KEY` and `APIFY_TOKEN`. Without `GROQ_API_KEY` the assistant shows matching evidence but no generated answer.

## Refreshing data

Manual: run collectors → `python -m pipeline.clean` → `python -m pipeline.filter full --auto-resume` → `python -m pipeline.tag full --auto-resume` → export, review, `export golden` → `python -m research.build`. There is no scheduler.

## Streamlit Community Cloud

- Repository files: `requirements.txt` (dashboard only, pinned), `.streamlit/config.toml`, `config.yaml`, `codebook.yaml`, `app/`, `research/`, `pipeline/filter.py`, `collect/`, `data/export/`.
- Main file: `app/streamlit_app.py`. Secrets (App settings → Secrets, TOML): `GROQ_API_KEY`, `ADMIN_PASSWORD`.
- To publish new data: run the pipeline locally, `python -m research.build`, commit `data/export/`, push. Community Cloud redeploys on push.
- The public repository contains the 300 exported Golden Dataset rows (review and post text, tags, source links). Usernames and reviewer names are not included.

## Other hosting

Not decided and not tested. Before any hosted deployment: choose a host that keeps `data/` private, set secrets as server environment variables, put the app behind authentication if review data is present, and confirm that publishing review and post excerpts is acceptable under each source's terms.
