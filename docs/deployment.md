# Deployment

## Local

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

Read at runtime from `st.secrets` (Streamlit Community Cloud), then environment variables (Render), then `.env` in the project root: `GROQ_API_KEY` (research assistant), `ADMIN_PASSWORD` (administrator view). Collectors also need `YOUTUBE_API_KEY` and `APIFY_TOKEN`. Without `GROQ_API_KEY` the assistant shows matching evidence but no generated answer.

## Refreshing data

Manual: run collectors → `python -m pipeline.clean` → `python -m pipeline.filter full --auto-resume` → `python -m pipeline.tag full --auto-resume` → export, review, `export golden` → `python -m research.build`. There is no scheduler.

## Streamlit Community Cloud

Live at https://groww-sip-discovery.streamlit.app/. That page shows the deployer's GitHub photo and name ("Created by") and a Streamlit badge. Both sit on Streamlit's hosting page, outside the app's iframe, so app code and CSS cannot remove them.

The inner address https://groww-sip-discovery.streamlit.app/~/+/ opens the app without that hosting page: no creator badge, Streamlit badge or Fork button. Tested 2026-11-06 in a fresh browser session: all five pages, reload and direct page links work. It is not a documented Streamlit address and could stop working. Not tested: what a visitor sees when the app has gone to sleep, because the wake-up control is likely on the hosting page.

`?embed=true` is not a substitute: it adds a "Built with Streamlit" footer and cut the page off at about 180px in testing.

- Repository files: `requirements.txt` (dashboard only, pinned), `.streamlit/config.toml`, `config.yaml`, `codebook.yaml`, `app/`, `research/`, `pipeline/filter.py`, `collect/`, `data/export/`.
- Main file: `app/streamlit_app.py`. Secrets (App settings → Secrets, TOML): `GROQ_API_KEY`, `ADMIN_PASSWORD`.
- To publish new data: run the pipeline locally, `python -m research.build`, commit `data/export/`, push. Community Cloud redeploys on push.
- The public repository contains the 456 exported Golden Dataset rows (review and post text, tags, source links). Usernames and reviewer names are not included.

## Render (prepared, not deployed)

`render.yaml` defines a free web service with no hosting badge. It has not been run on Render.

1. In Render, choose New → Blueprint and connect `kanhapal39/groww-sip-discovery`.
2. Enter `GROQ_API_KEY` and `ADMIN_PASSWORD` when prompted. Render asks for `sync: false` values only when the Blueprint is first created; change them later under the service's Environment settings.
3. Confirm all five pages load, then delete the Community Cloud app if it is no longer wanted.

Pushes to `main` redeploy the service. The free plan has 0.1 CPU and 512 MB, so startup may be slow. Whether the app fits in 512 MB is unconfirmed until it runs there.

## Other hosting

Not tested. Before any other hosted deployment: choose a host that keeps `data/` private, set secrets as server environment variables, put the app behind authentication if review data is present, and confirm that publishing review and post excerpts is acceptable under each source's terms.
