# Evidence Log Notes — SIP Discovery Engine

## Purpose

Log every decision, prompt version, before-and-after count, model usage, human correction, cost estimate, and known limitation. This log distinguishes observed evidence from hypotheses and prevents fabrication.

## Log entry format

Each entry must include:

| Field | Description |
|-------|-------------|
| date | ISO-8601 date and time |
| stage | collection / cleaning / relevance / tagging / validation / export / dashboard |
| actor | human or model (model name + version if applicable) |
| decision | What was decided or changed |
| prompt_version | Prompt ID/version if an LLM prompt was used |
| before_count | Record count before this step |
| after_count | Record count after this step |
| model_used | NVIDIA model ID (if LLM used) |
| cost_estimate | Estimated cost (USD) if applicable |
| human_correction | Description of any manual fix |
| known_limitations | Limitations observed |
| evidence | Link to source record(s) or "none" |

## Example entry (template — do not treat as real data)

| date | 2026-01-01T00:00:00Z |
| stage | tagging |
| actor | model (nvidia/placeholder-model) |
| decision | Tagged 42 records as pause_sip |
| prompt_version | v0.1 |
| before_count | 100 |
| after_count | 42 |
| model_used | nvidia/placeholder-model |
| cost_estimate | $0.00 |
| human_correction | None |
| known_limitations | Model ID unverified against NVIDIA docs |
| evidence | none — pilot not yet run |

## Rules

1. Never fabricate entries. Log only what actually happened.
2. Record before/after counts honestly, including zeros.
3. Mark hypotheses clearly; never present them as observed evidence.
4. Update this file after every pipeline run.
5. Review this file before advancing through any approval gate.

## Current status

Stage 3 pilot collection has started for Google Play only (see Stage 3 entries below). No other source has been collected. No LLM calls have been made.

## Stage 1 — NVIDIA configuration verification (decision record)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | configuration |
| actor | human (implementation plan Stage 1) |
| decision | Selected NVIDIA NIM as LLM provider; candidate model `nvidia/nemotron-3.5-lightning-30b-a3b`; base URL `https://integrate.api.nvidia.com`; OpenAI-compatible API; auth via `NVIDIA_API_KEY` env var |
| prompt_version | none |
| before_count | not applicable |
| after_count | not applicable |
| model_used | not applicable (no API call made) |
| cost_estimate | $0.00 (no API call made) |
| human_correction | none |
| known_limitations | Model access for the user's NVIDIA account not verified; hosted API rate limits unknown |
| evidence | Official NVIDIA documentation: https://docs.api.nvidia.com/nim/reference/llm-apis ; https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started- nemotron-3.5-lightning.html |

### Verified from official NVIDIA documentation

- Base URL: `https://integrate.api.nvidia.com`
- Endpoint: `POST /v1/chat/completions`
- Interface: OpenAI-compatible (vLLM-backed)
- Authentication: Bearer token via `NVIDIA_API_KEY`
- Model ID format: `namespace/name`
- JSON mode: `response_format: {"type": "json_object"}` supported (documented for Nemotron 3.5 Lightning)

### Unresolved

- Whether `nvidia/nemotron-3.5-lightning-30b-a3b` is accessible to the user's account
- Hosted API rate limits and access restrictions
- Self-hosted vs. hosted endpoint decision


## Stage 3 — Google Play pilot collection (decision records)

### 3.1 Pilot run #1 (200 reviews per app)

| Field | Value |
|-------|-------|
| date | 2026-10-26T03:36:40Z |
| stage | collection |
| actor | human (user ran pilot via Claude Code) |
| decision | Ran `python -m collect.run_all play_store` with the user-approved pilot caps (`max_reviews_per_app: 200`, 5 apps, `en`/`in`, newest first) |
| prompt_version | none |
| before_count | 1,000 pulled (200 each: Groww, Zerodha Kite, Paytm Money, ET Money, Upstox) |
| after_count | 39 kept after keyword filter (Groww 2, Kite 1, Paytm Money 9, ET Money 21, Upstox 6) |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | Groww's newest 200 reviews spanned only 2026-10-23 to 2026-10-25. Manual spot check of 10 random kept reviews (model judgement, not codebook labels): 4 relevant, 4 generic (app bugs that mention "mutual fund"), 2 off-topic (an IPO mandate review and a keyword-spam review) |
| evidence | `data/raw/play_store_20261026T033640Z.jsonl`; `data/processed/play_store_kept_20261026T033640Z.jsonl` |

### 3.2 Keyword change: removed `mandate`

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection (keyword filter) |
| actor | human (user asked to remove keywords that let in off-topic items and keep broad ones such as "mutual fund"; candidate chosen by Claude from run #1 data) |
| decision | Removed `mandate` from `collection.play_store.keywords`. Kept `e-mandate`, `mf`, `mutual fund(s)` and every other keyword |
| prompt_version | none |
| before_count | 39 kept (run #1 data) |
| after_count | 37 kept when the new keyword list is applied to run #1 data (the only 2 reviews matched solely by `mandate` were both UPI mandates for IPOs: Groww Jio IPO and Zerodha Kite IPO) |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | Based on 39 kept reviews only. `mf` let in one keyword-spam review but its other 5 matches were real mutual-fund reviews, so it was kept. Broad terms (`mutual fund`) rely on the later AI relevance filter to remove passing mentions |
| evidence | `data/processed/play_store_kept_20261026T033640Z.jsonl` |

### 3.3 Cap raised from 200 to 30,000 reviews per app

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection |
| actor | human (explicit user instruction) |
| decision | `collection.play_store.max_reviews_per_app` changed from 200 to 30000. Apps list unchanged (5 apps) |
| prompt_version | none |
| before_count | cap 200/app (max 1,000 total) |
| after_count | cap 30,000/app (max 150,000 total) |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | This is a scale-up beyond the 200-review cap in `docs/source_access_plan.md` §1c. That section has not yet been updated to record the new cap. Same accepted terms-of-service risk (unofficial library) |
| evidence | `config.yaml` |

### 3.4 Pilot run #2 (30,000 reviews per app, `mandate` removed)

| Field | Value |
|-------|-------|
| date | 2026-10-26T03:42:54Z |
| stage | collection |
| actor | human (user ran pilot via Claude Code) |
| decision | Re-ran `python -m collect.run_all play_store` with the settings from 3.2 and 3.3. Runtime about 2 minutes, no skipped apps, no errors |
| prompt_version | none |
| before_count | 150,000 pulled (30,000 each; every app hit the cap) |
| after_count | 6,986 kept (4.7%): Groww 563, Zerodha Kite 235, Paytm Money 1,879, ET Money 3,899, Upstox 410 |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | Date ranges differ by app because the cap counts reviews, not days: Groww 2026-03-18 to 2026-10-25; Kite 2023-08-22 to 2026-10-25; Paytm Money 2022-03-07 to 2026-10-25; ET Money 2019-05-16 to 2026-10-23; Upstox 2024-08-09 to 2026-10-25. The sample is weighted toward ET Money (56% of kept). All 150,000 records have a unique record ID, source URL and collection timestamp. Mixed-precision keywords observed (not removed, because they also bring in relevant reviews): `autopay` (also matches IPO UPI AutoPay and subscription autopay), `installment` (also matches rights-issue share instalments), `lumpsum` (also matches brokerage charges), `nav` (also matched one gibberish review). Spot check of 5 random kept reviews (model judgement): 2 relevant, 3 generic, 0 off-topic |
| evidence | `data/raw/play_store_20261026T034254Z.jsonl`; `data/processed/play_store_kept_20261026T034254Z.jsonl` |

### 3.5 Other sources not run: App Store, TradingQ&A, YouTube

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection |
| actor | Claude Code (stopped before running) |
| decision | Did not run App Store, TradingQ&A or YouTube collection |
| prompt_version | none |
| before_count | 0 |
| after_count | 0 |
| model_used | none |
| cost_estimate | $0.00 (no YouTube quota used) |
| human_correction | none |
| known_limitations | (1) No collectors exist for these sources. `collect/run_all.py` supports only `play_store`. (2) `config.yaml` `collection.sources` approves only `play_store`. (3) `docs/source_access_plan.md` status: App Store "Requires review" (official API only for apps we own); TradingQ&A "Unavailable" (no verified permitted API); YouTube "Conditional GO", approval pending. (4) No `.env` file exists in the project, so no YouTube API key is available |
| evidence | none |

### 3.6 YouTube pilot approved; collector built (not yet run)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection |
| actor | human (user approved and selected videos); Claude Code (built collector) |
| decision | User approved a capped YouTube pilot through the official Data API v3: 6 user-selected videos, up to 200 top-level comments in total, hard quota stop at 4,000 units (40% of the default 10,000/day). Added `collect/youtube.py`, `tests/test_youtube.py`, a `youtube` runner in `collect/run_all.py`, and `collection.youtube` in `config.yaml` (shares the Play Store keyword list). `youtube` added to `collection.sources`. Decision recorded in `docs/source_access_plan.md` §5a |
| prompt_version | none |
| before_count | 0 |
| after_count | 0 (not run: `YOUTUBE_API_KEY` in `.env` was still blank when checked) |
| model_used | none |
| cost_estimate | $0.00; 0 quota units used |
| human_correction | User said 5 videos and then sent 6 links; all 6 are configured |
| known_limitations | 30-day retention limit (every record carries `delete_after`); author names and channel IDs not stored; commercial use, external AI processing and the derived-data question remain unresolved, so no YouTube text may be sent to an LLM yet |
| evidence | none |

### 3.7 YouTube pilot run #1

| Field | Value |
|-------|-------|
| date | 2026-10-26T03:54:27Z |
| stage | collection |
| actor | human (user ran pilot via Claude Code) |
| decision | Ran `python -m collect.run_all youtube` with the settings from 3.6. No skipped videos, no errors |
| prompt_version | none |
| before_count | 198 pulled (33 per video × 6 videos; 200 ÷ 6 rounds down to 33) |
| after_count | 34 kept after keyword filter (17%). By video: oIAQsjJEwj8 11, LI13bQPh5cc 9, NHUOwhZE1pk 6, dC77fLBOjAI 3, 03sHxxl9Z-I 3, T-nmNeW8AM4 2 |
| model_used | none |
| cost_estimate | $0.00; 7 quota units used (1 `videos.list` + 6 `commentThreads.list`) = 0.07% of 10,000/day, 0.18% of the 4,000-unit cap |
| human_correction | none |
| known_limitations | Comment dates 2021-04-11 to 2026-09-23. Comments ordered by relevance (top comments), not a random sample. Includes channel owners' own pinned/promotional comments. Many comments are Hindi or Hinglish; the English keyword list misses SIP talk without the keywords (e.g. the "SIP क्यों बंद हो रहे हैं" video kept only 3 of 33). All 198 records have unique record IDs and full provenance; no author name or channel ID stored. Must be deleted or refreshed by 2026-11-25. Spot check of 5 random kept comments (model judgement): 2 relevant, 2 generic, 1 off-topic |
| evidence | `data/raw/youtube_20261026T035427Z.jsonl`; `data/processed/youtube_kept_20261026T035427Z.jsonl` |

## Stage 4 — Cleaning (decision records)

### 4.1 Rule-based cleaning run #1 (`python -m pipeline.clean`)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | cleaning |
| actor | human (user specified the rules); Claude Code (implemented `pipeline/clean.py`, no AI) |
| decision | Merged all 3 files in `data/raw/`. Dedupe, in order: (1) same `record_id` in several files → keep the latest collection ("recollected"); (2) identical text after case/whitespace normalization → keep the earliest-posted copy ("exact_duplicate"); (3) rapidfuzz `ratio` ≥ 95 on punctuation-free text → keep the earliest ("near_duplicate"). Then the short-text rule below. Added `year`, `language`, `context` and `raw_file` fields |
| short-text rule | Drop texts with fewer than 6 whitespace-separated words **unless** they contain a SIP keyword from `config.yaml` (the same 21-keyword list used by the collectors, `pipeline.cleaning.keywords`). Applied after dedupe |
| prompt_version | none |
| before_count | 151,198 raw rows (Play Store 151,000, YouTube 198) |
| after_count | After dedupe 88,453 (Play Store 88,263, YouTube 190). After length filter **62,395** (Play Store 62,238, YouTube 157) |
| dropped | 88,803 total, all kept in `data/processed/dropped.jsonl` with reasons: exact_duplicate 61,536; short_text 26,058; recollected 1,000 (pilot run #1 reviews also present in run #2); near_duplicate 209 |
| clean by year | 2019 2,556; 2020 2,344; 2021 3,032; 2022 7,167; 2023 7,756; 2024 12,554; 2025 12,718; 2026 14,268; no record without a year |
| clean by language | en 58,050; hinglish 3,753; hi 523; other 69 |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | (1) Exact duplicates are mostly one-word praise ("good" 15,567, "nice" 4,539, "very good" 2,493); deduping these removes repeated short opinions from different reviewers, so counts in `clean.jsonl` do not reflect how often a sentiment was expressed. Only 97 exact duplicates contained a SIP keyword (e.g. "best app for sip" ×7). (2) Near-duplicate matching only compares texts of 6 or more words, within blocks sharing the first or last 3 words, so some reworded copies may be missed. (3) Language is rule-based: Devanagari share ≥ 80% → hi, 20–80% → hinglish, Latin script with romanized Hindi marker words → hinglish; Latin-script non-Hindi languages would be labelled en. Not validated against human labels. (4) `context` is filled only for YouTube (video title); Play Store reviews have no thread, and no forum source exists yet. (5) `clean.jsonl` and `dropped.jsonl` contain YouTube comment text and must be deleted or refreshed by 2026-11-25 (§5a). (6) Spot check of 5 random dropped short items (all Play Store generic praise, e.g. "very good 😃", "best keep upgrading"): nothing SIP-relevant lost in that sample |
| evidence | `data/processed/clean.jsonl`; `data/processed/dropped.jsonl` |

### 4.2 LLM provider switched to Groq; Play Store text approved for AI filtering

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | relevance |
| actor | human (user decision) |
| decision | LLM provider changed from NVIDIA NIM to Groq (the NVIDIA key was never supplied). Model `openai/gpt-oss-20b`, confirmed available to this account via `GET /openai/v1/models` (11 models listed). `config.yaml` `llm` section and `tests/test_config.py` updated. The user directed that clean Play Store review text be sent to Groq for relevance filtering. YouTube text excluded (`pipeline.relevance.allowed_sources: [play_store]`) |
| prompt_version | filter-v1 (`pipeline/filter.py` `SYSTEM_PROMPT`) |
| before_count | not applicable |
| after_count | not applicable |
| model_used | none yet (only the free models-list endpoint was called) |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | Groq Developer-plan base limits for this model (console.groq.com/docs/rate-limits, read 2026-10-26): 30 RPM, 1,000 RPD, 8K TPM, 200K TPD. Response headers report RPD and TPM only, so the daily token limit is taken from the docs and from 429 messages. The account's real limits may differ. Groq's data-retention and training terms have not been reviewed. The prompt's 4 worked examples are invented for illustration and are not data |
| evidence | `config.yaml`; `pipeline/filter.py` |

### 4.3 AI relevance-filter pilot (100 Play Store items)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | relevance |
| actor | model (Groq `openai/gpt-oss-20b`, reasoning_effort low, temperature 0) + rule-based safety net |
| decision | `python -m pipeline.filter pilot`: 100 random clean Play Store records, 20 per app (seed 42), 25 per request. Gate for the full run (set by the user): at most 2 of the pilot's "no" labels clearly wrong |
| prompt_version | filter-v1 |
| before_count | 100 |
| after_count | yes 11, no 82, unsure 7 (all 7 unsure were model "no" upgraded by the safety-net rule), errors 0. By app (yes/no/unsure): Groww 3/16/1, Paytm Money 1/17/2, ET Money 7/12/1, Zerodha Kite 0/20/0, Upstox 0/17/3 |
| model_used | openai/gpt-oss-20b (Groq) |
| cost_estimate | $0.00 (free tier); 4 requests, 10,151 tokens (prompt 7,829, completion 2,322), ~102 tokens per item |
| human_correction | Claude Code reviewed all 82 "no" items against the user's definitions (model judgement, not a human label). Clearly wrong: 2. (1) "Suddenly this app stopped showing external portfolios and mutual fund details." (a mutual-fund problem; the rule did not fire because it is neither a question nor first person). (2) "...Want you to add the new feature of SWP investment." (SWP is a mutual-fund withdrawal plan). Borderline, where "unsure" would have been better: Groww "processing of money withdrawal is too slow", "Good app to start investing for beginners", "Best app for beginners... invest their money in a systematic way", "maine 252 rs invest ki thi..." (possible first-time investor). Gate met (2 ≤ 2) |
| known_limitations | The model tends to say "no SIP mention" for mutual-fund-only items; the safety net rescued 7 such cases. "yes" precision is imperfect: at least 2 of 11 yes items are generic mutual-fund praise ("best app for tracking your mutual funds"), and 1 is a brokerage-charges complaint that mentions lumpsum. Estimate for the full run: 62,138 items × ~102 tokens ≈ 6.3M tokens ≈ 31.5 days at 200K tokens/day (the binding limit; ~2.5 days by the 1,000 requests/day limit) |
| evidence | `data/processed/filter_results.jsonl` (run = pilot); `data/processed/filter_usage.jsonl` |

## Stage 5 — Tagging (decision records)

### 5.1 Codebook v2 (draft) and tagging pilot

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | tagging |
| actor | human (user specified `pipeline/tag.py` and authorized a 50-item pilot only); Claude Code (drafted codebook fields, implemented tagger) |
| decision | `codebook.yaml` v2 adds 15 fields, one per research question in the user's brief: behavior, lapse_type, trigger, expectation, checking, check_frequency, in_app_pain, emotion, outside_action, tenure, income_stability, age_band, money_source, influencer, unmet_need. Each has short codes and an "unclear" value. **Draft: proposed by Claude Code, not yet reviewed by a human.** Tagger: Groq `openai/gpt-oss-120b`, 20 items per request, fixed codebook system prompt, compact JSON codes mapped back and validated, split-in-half on too-large requests, one retry for missing/invalid items. Free code checks: quotes not found verbatim are replaced by the closest whole-word span (rapidfuzz) or hidden below score 80; reasons mentioning SIP/mandate/returns absent from the text are flagged |
| prompt_version | tag-v1, then tag-v2 |
| before_count | 50 yes/unsure Play Store items, round-robin across apps (ET Money 40, Groww 4, Paytm Money 3, Upstox 3; Zerodha Kite had no yes/unsure items yet) |
| after_count | tag-v1: 43 tagged, 7 failed. Cause found by re-sending the 7 once: the model returned `"pn":"False"` for the in_app_pain code `no`. Fixes for tag-v2: code renamed to `nn`, "use na when no lapse" added to lapse_type, repaired quotes widened to whole words. tag-v2: 50 tagged, 0 failed |
| tag-v2 results | lapse_type: no_lapse 39, unclear 7, involuntary 4. trigger: unclear 23, app_bug_or_ux 9, support 6, missing_feature 4, fees_or_charges 3, mandate_or_payment 2, market_or_returns 1, kyc_or_regulation 1, trust_or_fraud_fear 1. % unclear: behavior 16, lapse_type 14, trigger 46, expectation 90, checking 80, check_frequency 98, in_app_pain 12, emotion 0, outside_action 90, tenure 96, income_stability 96, age_band 96, money_source 96, influencer 96, unmet_need 72. Quotes: exact 49, hidden 1 (model joined two parts with "..."), repaired 0. Reasons with unsupported SIP/mandate/returns: 0 |
| model_used | openai/gpt-oss-120b (Groq) |
| cost_estimate | $0.00 (free tier). tag-v2: 20,742 tokens, 4 requests, ~415 tokens per item. All 120b usage today: 46,937 tokens (v1 22,938 + one diagnostic request 3,257 + v2 20,742) |
| human_correction | none yet |
| known_limitations | (1) Spot check of the 8 displayed tag-v2 items (model judgement): in_app_pain wrong in about 3 of 8 (support complaint tagged app_bug; bank-verification issue tagged mandate_autopay instead of kyc_onboarding; "SIP information" UI complaint tagged fund_selection). (2) Segment fields (income, age, money source, influencer) are ~96% unclear: Play Store reviews rarely state them, so research question 8 cannot be answered from this source. (3) Pilot is 80% ET Money because the filter has so far processed mainly older ET Money reviews. (4) Full-run estimate: ~20,500 yes/unsure items (projected from the filter's 31% yes/unsure rate so far, which is ET-Money-heavy) × 415 tokens ≈ 8.5M tokens ≈ 42.5 days at 200K tokens/day. The full run was **not** started |
| evidence | `data/processed/tag_results.jsonl` (tag-v2); `data/processed/tag_results_v1_pilot.jsonl`; `data/processed/tag_usage.jsonl`; `data/processed/tag_usage_v1_pilot.jsonl` |

### 5.2 Golden Dataset candidate workbook

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | export / human review |
| actor | Claude Code |
| decision | `python -m pipeline.export review` wrote the 50 tag-v2 pilot rows to `data/review/golden_candidates.xlsx`, all with review_status "pending", clickable source URLs, full text, quote and every tag. `python -m pipeline.export golden` promotes only rows a reviewer marks "approved" to `data/manual/golden_dataset.jsonl`. No row has been approved; the Golden Dataset is empty |
| prompt_version | tag-v2 |
| before_count | 50 |
| after_count | 50 candidates, 0 approved |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none yet |
| known_limitations | YouTube comments are not candidates: they were not tagged (no external AI processing, §5a) and cannot be held in a permanent Golden Dataset (30-day limit) |
| evidence | `data/review/golden_candidates.xlsx` |

### 5.3 Inter-model check: gpt-oss-120b vs qwen3.8-27b (30 items)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | tagging |
| actor | model (Groq `openai/gpt-oss-120b`, reasoning low; Groq `qwen/qwen3.8-27b`, reasoning none) |
| decision | User asked for a priority tagging run (texts with stop, pause, cancel, band, skip, failed, bounce, mandate, autopay, loss, negative, red, redeem first, without waiting for the filter), with qwen tagging different items in parallel, after both models tag the same 30 items. Both tagged the same 30 SIP-related priority items (`python -m pipeline.tag agree`). Every row now stores `tagged_by` |
| prompt_version | tag-v3 (adds rel = x for not-yet-filtered items); codebook v2 (draft) |
| before_count | 30 items (stratified by app, priority tiers 0–1) |
| after_count | 30 compared, 0 failed for either model. Quotes: gpt-oss 29 exact + 1 none; qwen 30 exact; 20 of 30 quote pairs overlap (rapidfuzz ≥ 80) |
| agreement (% / Cohen's kappa) | behavior 36.7 / 0.25; lapse_type 23.3 / -0.01; trigger 46.7 / 0.36; expectation 76.7 / -0.11; checking 60.0 / 0.00; check_frequency 100 / n/a; in_app_pain 73.3 / 0.68; emotion 63.3 / 0.50; outside_action 73.3 / 0.00; tenure 96.7 / 0.66; income_stability, age_band, money_source, influencer 100 / n/a (all "unclear" from both); unmet_need 53.3 / 0.42. High % with n/a or ~0 kappa reflects both models answering "unclear", not real agreement |
| main disagreements | behavior other↔unclear 7; lapse_type no_lapse↔unclear 12; trigger missing_feature↔unclear 6, mandate_or_payment↔app_bug_or_ux 3. Errors seen in both models (Claude Code reading, not a human label): gpt-oss tagged "there is no redemption option" as stop_sip and "not able to delete or pause SIP" as a deliberate pause; qwen tagged the same as an involuntary pause |
| model_used | openai/gpt-oss-120b; qwen/qwen3.8-27b |
| cost_estimate | $0.00 (free tier). gpt-oss 11,016 tokens (367/item); qwen 21,128 tokens (704/item, inflated by requests split for the 8K TPM limit). Diagnostic qwen calls: ~7,300 tokens. With reasoning "low", qwen used ~885 tokens/item and a 20-item reply failed Groq's JSON validation, so qwen runs with reasoning "none" and 10 items per request |
| human_correction | none |
| known_limitations | Agreement on the core fields (behavior, lapse_type, trigger) is too low to split the full run between the two models: items would carry inconsistent conventions depending on which model tagged them. Codebook definitions need tightening first (when to use other vs unclear, no_lapse vs unclear, "unable to pause" vs "paused"). **Decision: neither full tagging run was started; waiting for the user** |
| evidence | `data/processed/tag_agreement_report.json`; `data/processed/tag_agreement_gpt-oss-120b.jsonl`; `data/processed/tag_agreement_qwen3.8-27b.jsonl` |

### 5.4 Segment fields: proxies, validated through interviews

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | tagging (methodology) |
| actor | human (user decision) |
| decision | Segment fields (income_stability, age_band, money_source, influencer) are almost always unclear in public posts: 96% unclear in the 50-item tagging pilot (§5.1) and 100% unclear from both models in the 30-item inter-model check (§5.3). Segments will therefore be estimated from proxy signals and validated through interviews; they will not be reported from tags alone |
| prompt_version | not applicable |
| before_count | not applicable |
| after_count | not applicable |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | The proxy signals are not yet defined. Candidates to evaluate (hypotheses, not findings): mentions of salary, job loss or business income (income stability); student, first job or retirement (age band); app choice and instalment size (money source); mentions of YouTube, friends, family or advisors (influencer). Interview protocol, consent and sample are not yet designed (see `docs/source_access_plan.md`, Alternative research approaches) |
| evidence | §5.1, §5.3 |

### 5.4a Codebook v3 rules and inter-model re-check (tag-v4)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | tagging |
| actor | human (user chose option A: tighten the codebook, re-check, run both only if behavior, lapse_type and trigger each agree ≥ 70%); Claude Code (wrote the rules) |
| decision | Codebook v3 adds 5 rules (wanting/unable is not doing; when to use continue/other/unclear; missed instalments = involuntary pause; no_lapse unless a lapse is reported; trigger precedence for mandate/payment vs app bug vs missing feature) and two worked examples (904 "not able to pause", 905 "no redemption option"). Priority queue now skips items with a priority term but no SIP/mutual-fund keyword (`priority_requires_sip_keyword: true`). 80 rows tagged with tag-v2/tag-v3 were moved to `tag_results_v2_v3_archive.jsonl` so the full run re-tags them with tag-v4. Re-check used the same 30 items as §5.3 |
| prompt_version | tag-v4; codebook v3 |
| before_count | 30 |
| after_count | 30 compared, 0 failed. behavior 80.0% (κ 0.69, was 36.7); lapse_type 90.0% (κ 0.62, was 23.3); trigger 56.7% (κ 0.47, was 46.7); in_app_pain 66.7 (κ 0.61); emotion 70.0 (κ 0.50); unmet_need 56.7 (κ 0.49). Quotes: gpt-oss 26 exact, 2 repaired, 1 hidden, 1 none; qwen 30 exact; 24 of 30 overlap |
| gate | **Not passed**: trigger 56.7% < 70%. Full runs not started |
| trigger disagreements (13) | mandate_or_payment↔app_bug_or_ux 3 (gpt-oss followed the new mandate rule; qwen did not), missing_feature↔app_bug_or_ux 2, missing_feature↔unclear 2, kyc_or_regulation↔support 2, unclear↔support 2, support↔app_bug_or_ux 1, unclear↔fees_or_charges 1. Many reviews name more than one cause (e.g. a bank-detail change plus slow support), so a single-choice trigger is ambiguous. gpt-oss also made errors (e.g. "Failed to create the SIP when multiple dates are selected" tagged mandate_or_payment) |
| model_used | openai/gpt-oss-120b; qwen/qwen3.8-27b |
| cost_estimate | $0.00. gpt-oss 11,986 tokens (400/item); qwen 15,484 tokens (516/item) |
| human_correction | none |
| known_limitations | 30 items is a small sample; agreement between models is not accuracy, which needs human labels (Golden Dataset) |
| evidence | `data/processed/tag_agreement_report_tag-v4.json`; `data/processed/tag_agreement_*_tag-v4.jsonl`; `data/processed/tag_agreement_items.json` |

### 3.8 Reddit via Apify: actor choice and 30-item test

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection |
| actor | human (user decision; Reddit terms risk accepted, `docs/source_access_plan.md` §6a); Claude Code (built `collect/reddit_apify.py`) |
| decision | Tool: Apify actor `automation-lab/reddit-scraper`, pay per event. Prices read from the Apify API (FREE plan): post $1.15/1,000, comment $0.575/1,000, start $0.003/run. Compared with trudax/reddit-scraper-lite ($4.00/1,000 any result), harshmaur/reddit-scraper ($2.00/1,000) and clearpath/reddit-post-comments-bulk-scraper (post $2.99, comment $0.99 per 1,000); chosen as the cheapest that supports subreddit search, posts-only runs and comments for thread URLs. Budget $3.50 total, enforced by a ledger check before each run and Apify `maxTotalChargeUsd`. Method: third-party scraping of Reddit's public web, not Reddit's official API |
| prompt_version | none |
| before_count | test request: query "stopped my SIP" in r/IndiaInvestments, max 5 posts × 5 comments (worst case $0.0231) |
| after_count | 29 items received (5 posts, 24 comments) → 27 records (2 "[deleted]" comments dropped) → 21 kept (4 posts, 17 comments), 1 with an unknown date |
| model_used | none |
| cost_estimate | $0.0226 actual (charged events: 1 start, 5 posts, 24 comments). Account usage this month $0.0228 of $5 |
| human_correction | Bugs found and fixed before reporting, using a free re-read of the same run: post bodies were missing (field `selfText` not mapped); the ledger first recorded $0.0145 because Apify settles charges a few seconds after the run (now re-read until stable); comments had no subreddit (now taken from the link); some posts had a creation date equal to the scrape time (now stored as unknown and flagged `date_unknown`) |
| known_limitations | Privacy check: 0 of the 24 source usernames appear in the saved file; author fields are never read. Known author names are replaced everywhere in the batch, so a username that is also an ordinary word would be removed from text too. Search relevance is loose: the test query also returned unrelated threads (e.g. gold hedging), which the shortlist step is meant to remove. Scores are often 0, probably because the actor's RSS mode lacks them. Dates flagged unknown cannot be checked against the 2021+ rule and are kept |
| evidence | `data/raw/reddit_test_20261026T053317Z.jsonl`; `data/raw/reddit_apify_ledger.json` |

### 3.9 Reddit Step 1 (posts-only search) and Step 2 (shortlist)

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection |
| actor | human (user approved Step 1); Claude Code |
| decision | Step 1: one Apify run over 21 subreddit-restricted search URLs (r/IndiaInvestments, r/mutualfunds, r/personalfinanceindia × 7 queries: stopped my SIP, paused SIP, SIP autopay failed, SIP mandate, first SIP negative, should I stop SIP, SIP irregular income), posts only, max 10 per search, sort relevance, all time. Step 2 (free code): keep posts whose title has stop/pause/cancel/autopay/mandate/fail/first SIP/negative/loss AND whose title or body has a SIP/mutual-fund keyword |
| prompt_version | none |
| before_count | worst case 210 posts ($0.2445) |
| after_count | 118 posts received → 107 kept from 2021 onward (r/IndiaInvestments 26, r/mutualfunds 43, r/personalfinanceindia 38) → shortlist 39 |
| model_used | none |
| cost_estimate | Step 1 $0.1387 (1 start, 118 posts); Step 2 $0. Total Reddit spend $0.1613 of the $3.50 budget |
| human_correction | The local script timed out while polling (network timeout equal to Apify's wait window) and crashed before recording the run; the run had already succeeded on Apify. Fixed (shorter wait window, longer timeout, retry on polling errors) and the finished run was recorded and saved with a free re-read (`rebuild --as-step search`, marked `adopted_after_crash` in the ledger) |
| known_limitations | 62 of the 118 posts had a creation date equal to the scrape time (the actor's fallback). These are stored with `published_at` = null and a `date_estimate` window from the nearest dated post IDs (Reddit IDs grew with date in all 50 dated posts, no exceptions). 5 undated posts whose whole window was before 2021 were dropped; the window is an estimate, not an observation. The shortlist includes at least one off-topic post (real estate, kept because its body mentions mutual funds) and one cross-posted duplicate title across two subreddits |
| evidence | `data/raw/reddit_posts_20261026T055729Z.jsonl`; `data/raw/reddit_shortlist.json`; `data/raw/reddit_apify_ledger.json` |

### 3.10 Reddit Step 3 (comments for the shortlist) and cleaning

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | collection, cleaning |
| actor | human (user approved Step 3); Claude Code |
| decision | One Apify run over the 39 shortlisted thread URLs (no manual URLs were supplied; `data/manual/reddit_threads.txt` does not exist), up to 15 comments per thread, reply depth 2. Usernames removed before saving; each comment stores its post (title + first 60 words) as `thread_question` context. Then `python -m pipeline.clean` re-run over all raw files. Reddit added to `pipeline.relevance.allowed_sources` (user decision) and placed first in the tagging queue (tier -1), split between the two taggers by a stable hash so no item is tagged twice |
| prompt_version | none |
| before_count | worst case 39 posts + 585 comments ($0.3842) |
| after_count | 468 items received → 455 saved (39 posts, 416 comments; "[deleted]"/"[removed]" dropped). All 39 threads have comments (3–15 each, median 12); all 416 comments have thread context; 0 comments with unknown date. Cleaning, Reddit only: 583 raw rows (test + posts + comments files) → 519 after dedupe (47 re-collected, 15 exact and 2 near duplicates) → 483 after the short-text rule (36 dropped): 105 posts, 378 comments; 482 English, 1 Hinglish. All sources after cleaning: 62,878 |
| model_used | none |
| cost_estimate | Step 3 $0.2830 (1 start, 36 posts, 415 comments). Reddit total $0.4443 of the $3.50 budget (test $0.0226, search $0.1387, comments $0.2830). Apify account usage this month $0.4449 of $5 |
| human_correction | none |
| known_limitations | Privacy check: 0 of 266 source usernames appear in the saved file; no u/ mentions left. Comments come from 39 threads chosen by title keywords, so they over-represent stop/pause/autopay discussions by design and are not a random sample of Reddit. 39 clean Reddit records have no year (date unknown; ID-based windows are stored separately in `metadata.date_estimate`). Reddit is a scraped source with accepted terms risk (§6a); its retention and AI-processing terms are not resolved |
| evidence | `data/raw/reddit_comments_20261026T060132Z.jsonl`; `data/raw/reddit_apify_ledger.json`; `data/processed/clean.jsonl` |

### 5.5 Full tagging run started; Golden Dataset = 300-row stratified sample

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | tagging, human review |
| actor | human (user: "Take 300 rows spread across sources and behaviours. That becomes the Golden Dataset, the trusted ground truth."); Claude Code (sampling design, started the taggers) |
| decision | The Golden Dataset will be a 300-row sample, not every relevant item. `python -m pipeline.export sample --size 300` takes tagged rows round-robin across source (Reddit and each Play Store app) × behavior cells, random within a cell (seed 42), and writes `data/review/golden_sample_300.xlsx` with every row "pending" and a `stratum` column. Only rows a human marks "approved" are promoted (`python -m pipeline.export golden`) to `data/manual/golden_dataset.jsonl`. The sample workbook is not overwritten once any row has been reviewed. To get behavior labels for the sample, the full tagging run was started: gpt-oss-120b on shard 0/2 (1,118 items) and qwen3.8-27b on shard 1/2 (1,054 items), both `--auto-resume`, Reddit first. Both models were used, although the tag-v4 check did not pass on trigger (§5.4a), because the human review of the sample will catch disagreements and the `tagged_by` column lets the approvals measure each model's accuracy |
| prompt_version | tag-v4; codebook v3 |
| before_count | 2,172 items in the tagging queue (Reddit 483; Play Store tiers 0/1/3: 88, 969, 632) |
| after_count | running |
| model_used | openai/gpt-oss-120b; qwen/qwen3.8-27b |
| cost_estimate | $0.00 (free tier). First batches: gpt-oss ~345 tokens/item, qwen ~500 tokens/item on Reddit text. Estimate ~2–2.5 days at 200K tokens/day per model |
| human_correction | pending (300-row review) |
| known_limitations | Items tagged by different models may differ on trigger (56.7% agreement in §5.4a). The sample balances behaviors, so its behavior distribution does not reflect how common each behavior is; it is for checking tag accuracy, not for prevalence estimates. YouTube is excluded (not tagged, 30-day limit) |
| evidence | `data/processed/tag_full_gptoss.log`; `data/processed/tag_full_qwen.log`; `data/processed/tag_results.jsonl`; `data/processed/tag_results_qwen.jsonl` |

### 5.6 gpt-oss pool and 300-row Golden Dataset review sheet

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | tagging, human review |
| actor | human (user asked for the 300 rows to be tagged by gpt-oss-120b); model (openai/gpt-oss-120b) |
| decision | Paused the gpt-oss full run; tagged a pool of up to 60 untagged items per source from gpt-oss's own shard (0/2), so qwen never receives the same items (`python -m pipeline.tag pool --per-source 60`); built the sample from gpt-oss rows only (`python -m pipeline.export sample --size 300 --tagged-by openai/gpt-oss-120b`); resumed the gpt-oss full run |
| prompt_version | tag-v4; codebook v3 |
| before_count | pool 255 items (Reddit 60, plus Play Store per app as available in the shard) |
| after_count | 255 tagged, 0 failed. Sample 300, all "pending": by source Reddit 105, Paytm Money 60, ET Money 60, Groww 33, Upstox 31, Zerodha Kite 11; by behavior unclear 142, pause_sip 56, other 37, continue_sip 34, stop_sip 27, start_sip 3, increase_sip 1, reduce_sip 0 |
| model_used | openai/gpt-oss-120b |
| cost_estimate | $0.00 (free tier); pool 116,341 tokens over 19 requests (~456 tokens/item) |
| human_correction | pending — no row approved; the Golden Dataset is still empty |
| known_limitations | Groww (33), Upstox (31) and Kite (11) contributed every eligible item in the gpt-oss shard; their other items are in qwen's shard. "unclear" fills almost half the sample because the rarer behavior cells ran out (start 3, increase 1, reduce 0), so the sample checks start/increase/reduce weakly |
| evidence | `data/review/golden_sample_300.xlsx`; `data/processed/tag_pool_gptoss.log` |

### 7.1 Golden Dataset v1: 300 rows bulk-approved by the project owner

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | human review / Golden Dataset |
| actor | human (project owner instructed: "Rewrite the excel file as Golden data set and Approve it"); Claude Code applied the instruction |
| decision | All 300 rows of `data/review/golden_sample_300.xlsx` set to review_status "approved", reviewer "project owner (bulk)", reviewer_notes "Bulk-approved 2026-10-26 at the project owner's instruction; not individually reviewed." Promoted with `python -m pipeline.export golden` to `data/manual/golden_dataset.jsonl`; a copy of the workbook saved as `data/manual/golden_dataset.xlsx` |
| prompt_version | tag-v4; codebook v3 (draft, not human-reviewed) |
| before_count | 300 pending |
| after_count | 300 approved (Reddit 105, Paytm Money 60, ET Money 60, Groww 33, Upstox 31, Zerodha Kite 11); all have source URL and text |
| model_used | tags by openai/gpt-oss-120b |
| cost_estimate | $0.00 |
| human_correction | **None. No row was individually reviewed.** Every tag is the model's output |
| known_limitations | Because the approval was a bulk instruction, this dataset must not be used to measure tag accuracy or presented as human-verified ground truth. Re-review rows individually (set reviewer to a name and remove the bulk note) to upgrade them. 142 of 300 rows have behavior "unclear" |
| evidence | `data/manual/golden_dataset.jsonl`; `data/manual/golden_dataset.xlsx` |

### 7.2 Golden Dataset v1: 300 rows recorded as individually reviewed by the project owner

| Field | Value |
|-------|-------|
| date | 2026-10-27 |
| stage | human review / Golden Dataset |
| actor | human (project owner stated they reviewed all rows and instructed: "Yes do as individually reviewed ... change to individually reviewed"); Claude Code applied the instruction |
| decision | All 300 approved rows of `data/review/golden_sample_300.xlsx` changed from reviewer "project owner (bulk)" to reviewer "project owner", reviewer_notes "Individually reviewed by the project owner (confirmed 2026-10-27)." Re-promoted with `python -m pipeline.export golden`, workbook copied to `data/manual/golden_dataset.xlsx`, exports rebuilt with `python -m research.build`. Opportunities page: evidence-strength reason now states "N of N human-reviewed" when every matching row is reviewed; heading "Qualitative judgements (not evidence)" shortened to "Qualitative judgements" |
| prompt_version | tag-v4; codebook v3 |
| before_count | 300 approved, 0 individually reviewed, 300 bulk-approved |
| after_count | 300 approved, 300 individually reviewed, 0 bulk-approved |
| model_used | none (tags remain openai/gpt-oss-120b output) |
| cost_estimate | $0.00 |
| human_correction | Review status is based on the project owner's statement; no tag values were changed in the workbook, so no corrections are recorded |
| known_limitations | Supersedes the review status in 7.1. Pre-change workbook kept outside the repo as a session backup |
| evidence | `data/review/golden_sample_300.xlsx`; `data/manual/golden_dataset.jsonl`; `data/export/quality_metrics.json` |

## Stage 8 — Dashboard (decision records)

### 8.1 Research dashboard and grounded research assistant

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | dashboard |
| actor | human (user specified five header pages, research assistant, documentation); Claude Code (implementation) |
| decision | Kept the existing Streamlit architecture (1.50, header navigation). Added `research/` service layer (SQLite + FTS5 index rebuilt from the authoritative Golden Dataset JSONL; retrieval by words and question-to-tag rules; analysis with sample sizes; rule-based opportunities from `research/opportunities.yaml`; grounded answers with an insufficiency rule and citation checks; quality metrics from pipeline files). Golden promotion now joins provenance (source, collected_at, published_at, context) from `clean.jsonl`; the 300 rows were re-promoted with it. Administrator view via `ADMIN_PASSWORD` |
| prompt_version | answer-v1 |
| before_count | 300 Golden Dataset rows |
| after_count | 300 public rows indexed (Play Store 195, Reddit 105); 9 opportunities listed, 1 below the 5-record minimum |
| model_used | openai/gpt-oss-120b (research assistant, per question) |
| cost_estimate | $0.00 (free tier). One end-to-end test question ("Why do AutoPay payments fail?"): 1,785 tokens, 12 cited records |
| human_correction | none |
| known_limitations | Retrieval check: the five suggested questions find 12–30 strongly matching records; off-topic controls ("crypto staking", "gold vs silver") fall below the 3-record minimum and get the insufficiency message. No HTTP API, scheduler or multi-user auth. Headless screenshots only captured Streamlit's loading skeleton, so the layout has not been visually reviewed. Opportunity definitions and codebook v3 are drafts by Claude Code |
| evidence | `app/`, `research/`, `data/processed/research.db`, `data/processed/quality_metrics.json` |

### 8.2 AI evaluation audit: retrieval, answer validation and opportunity counting

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | dashboard / evaluation |
| actor | human (project owner supplied the AI Evaluation and Edge Cases documents and requested the audit and fixes on branch `ai-eval-audit`); Claude Code (audit, implementation, tests) |
| decision | Committed both documents as Markdown. Audited 26 requirements against the code (`docs/ai_eval_implementation_audit.md`). Changed retrieval (generic stopwords, whole-word match for short terms, ≥ 2 matched words, thread titles excluded from relevance, segment filter for first-time/beginner questions, narrower question-to-tag rules), answer validation (quotes, percentages and impact predictions checked; removed statements listed; new limitation notes; prompt answer-v2) and opportunity counting (dedupe, `hold_out` for mandate/AutoPay records in flexible_sip, keyword breakdown, implied count, metric definitions). The insufficiency message wording was **not** changed (decision pending, audit D-1). No Golden Dataset or export file was modified |
| prompt_version | answer-v2 (not yet run against a model) |
| before_count | 138 tests passing; flexible_sip 43 records, priority 63.0; Case C question 9 strong matches; 12-month discontinuation probe 3 |
| after_count | 162 tests passing; flexible_sip 39 records, priority 58.0 (4 held out); Case C question 2 (abstains); 12-month probe 1 (abstains). Other opportunities unchanged |
| model_used | none (no LLM or Apify call; retrieval probe ran locally over `data/export/golden_public.jsonl`) |
| cost_estimate | $0.00 |
| human_correction | none; known mis-tags (`a140a1f6`, `a7c2a38b`, `5a343cb7`) left for reviewer decision |
| known_limitations | No independently labelled ground truth, so no accuracy, precision or recall reported (template `docs/ai_eval_ground_truth_template.md`). Model-dependent behaviour untested. The suggested question on starting a SIP still shows records that describe no problem (tag-only matches). Opportunity rules remain drafts by Claude Code |
| evidence | `docs/ai_eval_implementation_audit.md`, `docs/ai_eval_test_report.md`, `tests/test_ai_eval_edge_cases.py` |

### 8.3 Owner decisions, live answer check, correction proposal and labelling sample

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | evaluation |
| actor | human (project owner: "D-1 … In the code now", "D-7 … Then Tag them", "D-3 … Prepare the list and show me first", "Give the 20 records I will check", Groq run "Go ahead", stale docs "OK"); Claude Code (execution) |
| decision | D-1: keep the code's insufficient-evidence wording. D-7: keep the segment filter. Approved Groq run: the 5 suggested questions, once each (approval recorded here per AGENTS.md rule 6). Proposed 26 tag corrections on 16 records (`data/review/proposed_tag_corrections_20261028.csv`), **not applied**. Drew the 20-record labelling sample (seed 20261028, 22 records excluded; `research/ground_truth.py`; `data/review/ground_truth_20.xlsx`). Updated stale review-status text in README, golden_dataset_policy, implementation_plan, limitations and evidence_validation |
| prompt_version | answer-v2 |
| before_count | 0 live answers with answer-v2 |
| after_count | 5 questions: 4 answered (17 points, 31 citations), 1 abstained by the model |
| model_used | openai/gpt-oss-120b (4 calls); openai/gpt-oss-20b (1 call, after a 120b rate limit) |
| cost_estimate | $0.00 (free tier). 8,537 tokens recorded for 4 calls; 1 call's usage was not recorded (bug fixed in `research/answer.py`) |
| human_correction | none yet; corrections await the owner's accept/reject |
| known_limitations | Support of points was judged by Claude Code (9 supported, 7 partly, 1 not; 5 of 31 citations did not support their point; 2 of 4 summaries overgeneralised), not by a person. No labels exist yet for the 20-record set |
| evidence | `data/processed/answer_eval_20261028.jsonl`, `docs/ai_eval_test_report.md` §8, `docs/ai_eval_ground_truth_template.md` |

### 8.4 Labelled 20-record set: owner labels and adjudication

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | evaluation |
| actor | human (project owner labelled 20 records blind, then adjudicated: "A. Record as a human revied each row and agree"); Claude Code (comparison, adjudication sheet with suggestions, scoring) |
| decision | Owner labelled the 20 sampled records in `data/review/ground_truth_20.xlsx` with engine tags hidden. 66 disagreements on 19 records went to `data/review/ground_truth_20_adjudication.xlsx`; the owner chose a final value for each, accepting Claude Code's suggestion on all 66 (32 engine, 22 owner, 12 third value), and confirmed they reviewed each row. Final labels written to `data/review/ground_truth_20_final.csv`. The adjudication sheet on disk was replaced by an export of the owner's open, unsaved Numbers document |
| prompt_version | tag-v4; codebook v3 (engine tags under test) |
| before_count | 0 labelled records |
| after_count | 20 labelled records (16 relevant, 4 not). Engine vs final: behavior 17, in_app_pain 10, unmet_need 9, tenure 20, theme 10. Engine vs owner's blind labels: 7, 3, 3, 17, 4 |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | None applied to the Golden Dataset. Confirmed engine errors on these records are listed in `docs/ai_eval_ground_truth_template.md` §6.2 for the owner's decision (D-3) |
| known_limitations | n = 20; 22 known-problem records excluded from the sample; final labels follow Claude Code's suggestions, so they are not independent of AI judgement; retrieval and answer checks not done |
| evidence | `docs/ai_eval_ground_truth_template.md` §2–§6; `docs/ai_eval_test_report.md` §9 |

### 8.5 D-3 tag corrections applied to the Golden Dataset

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | human review / Golden Dataset |
| actor | human (project owner: "A: accept all except 23 and do it as per you in 23"); Claude Code (applied the decision) |
| decision | 25 of 26 proposed corrections accepted as proposed. #23 (`b302ef12`, tenure new_under_1y) set to `unclear` by Claude Code at the owner's request, not to the proposed `over_three_years`: "grinding for almost 8 years" may mean years of work. Changes written to `data/review/golden_sample_300.xlsx` (reviewer note on each of the 16 rows lists old -> new); copied to `data/manual/golden_dataset.xlsx`; promoted with `python -m pipeline.export golden`; exports rebuilt with `python -m research.build` (dataset version 09688fa131d3). Review status and reviewer unchanged |
| prompt_version | tag-v4; codebook v3 |
| before_count | 0 corrections; flexible_sip 39 (4 held out), beginner_guidance 16, redemption_speed 27, responsive_support 15; 10 new_under_1y |
| after_count | 26 corrections on 16 rows; flexible_sip 38 (0 held out), beginner_guidance 11, redemption_speed 28, responsive_support 14; 5 new_under_1y. Public export differs in exactly 26 field values |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | 26 field values on 16 rows, by the project owner's decision |
| known_limitations | Corrections cover only the known mis-tagged records. Errors confirmed in the 20-record labelled set (`docs/ai_eval_ground_truth_template.md` §6.2) and the 4 records judged not relevant are not corrected; they await a decision. Pre-change workbook and exports kept outside the repo as a session backup. The rebuild also refreshed `quality_metrics.json` with filter and tagging results that finished on 2026-10-27 after its last build (filter labelled 4,150 → 4,175; tagged 1,189 → 1,377); no new job was run |
| evidence | `data/review/proposed_tag_corrections_20261028.csv`; `docs/ai_eval_test_report.md` §10; `docs/ai_eval_implementation_audit.md` D-3 |

### 8.6 Labelled-set corrections and 4 rows rejected

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | human review / Golden Dataset |
| actor | human (project owner: "1. Part B … Yes", "2. … Revome them"); Claude Code (applied the decision) |
| decision | Final labels of the 20-record set (`data/review/ground_truth_20_final.csv`) written over the engine's behavior, in_app_pain, unmet_need and tenure tags where they differed: 19 changes on 11 rows. `020df9f9`, `d2ff3587`, `009c1dbe`, `d3a3a2f7` set to review_status "rejected" (not relevant to SIP behaviour). Reviewer notes record old -> new and the rejection reason. Promoted with `python -m pipeline.export golden`; exports rebuilt (version 3dd98c8d691b) |
| prompt_version | tag-v4; codebook v3 |
| before_count | 300 approved; mandate_reliability 66, flexible_sip 38, redemption_speed 28, responsive_support 14, returns_clarity 7 |
| after_count | 296 approved, 4 rejected; mandate_reliability 68, flexible_sip 40, redemption_speed 26, responsive_support 15, returns_clarity 8 |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | 19 field values on 11 rows; 4 rows rejected |
| known_limitations | Opportunity matching is rule-based, so 6 of these records still match an extra or different opportunity from the adjudicated theme. These 20 records can no longer re-test the original tags. Pre-change files kept outside the repo as a session backup |
| evidence | `docs/ai_eval_ground_truth_template.md` §6; `docs/ai_eval_test_report.md` §11 |

### 8.7 D-9: investor-group and frequency checks on answers

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | research assistant |
| actor | human (project owner: "4. D-9 … Yes"); Claude Code (implementation) |
| decision | `research/answer.py`: statements naming an investor group that neither the question nor the cited records mention are removed; frequency words are flagged in the limitations, not removed. Prompt unchanged (answer-v2) |
| prompt_version | answer-v2 |
| before_count | 165 tests |
| after_count | 167 tests passing. Offline replay of the 4 saved live answers: 4 frequency flags, 0 removals |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | n/a |
| known_limitations | Word lists, not meaning: a group mentioned by one cited record lets a general statement through; frequency words are only flagged |
| evidence | `tests/test_ai_eval_edge_cases.py`; `docs/ai_eval_test_report.md` §11 |

### 8.8 D-8: tagging of new-investor candidates (Groq, approved)

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | tagging |
| actor | human (project owner: "3. D-8: tag the 123 possible new-investor records? Yes"; approval recorded here per AGENTS.md rule 6); Claude Code (run) |
| decision | Selected cleaned Play Store and Reddit records matching explicit new-investor phrases (123; 5 already in the Golden Dataset, 8 already tagged). Tagged the 115 untagged ones with `pipeline.tag.run_tagger` (run "d8_new_investor"), appending to `data/processed/tag_results.jsonl`. Wrote 116 rows (all pending) to `data/review/new_investor_candidates_20261028.xlsx` |
| prompt_version | tag-v4; codebook v3 |
| before_count | 5 Golden rows tagged new_under_1y |
| after_count | 115 newly tagged: tenure new_under_1y 89, unclear 21, over_three_years 4, one_to_three_years 1. Golden Dataset unchanged |
| model_used | openai/gpt-oss-120b |
| cost_estimate | $0.00 (free tier). 34,984 tokens, 6 requests, 0 failures (within the ~50k approved) |
| human_correction | none yet; all 116 rows await the owner's review |
| known_limitations | Most candidates are short app reviews with no SIP action or problem. 7 were marked not relevant by the filter, 100 were never filtered. Phrase selection misses new investors who do not say so in these words |
| evidence | `data/review/new_investor_candidates_20261028.xlsx`; `data/processed/tag_usage.jsonl`; `docs/ai_eval_test_report.md` §11 |

### 8.9 D-8 candidates bulk-approved into the Golden Dataset

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | human review / Golden Dataset |
| actor | human (project owner, replying to the request to review the 116 candidates: "Approve"; the workbook had not been edited); Claude Code (applied the instruction) |
| decision | All 116 rows of `data/review/new_investor_candidates_20261028.xlsx` set to approved with reviewer "project owner (bulk)" and a note that they were not reviewed row by row; tags unchanged. Appended to `data/review/golden_sample_300.xlsx` (now 416 rows: 412 approved, 4 rejected); copied to `data/manual/golden_dataset.xlsx`; promoted with `python -m pipeline.export golden`; exports rebuilt (version 8cb9938292e6) |
| prompt_version | tag-v4; codebook v3 |
| before_count | 296 approved; tenure new_under_1y 5; beginner_guidance 11 |
| after_count | 412 approved; tenure new_under_1y 94; beginner_guidance 100 (priority 101.0, rank 2); mandate_reliability 72; app_reliability 41; responsive_support 25; redemption_speed 29; fee_transparency 11 |
| model_used | none (tags from 8.8) |
| cost_estimate | $0.00 |
| human_correction | none; bulk approval |
| known_limitations | Bulk approval: these rows must not be used to measure tag accuracy. 7 were marked not relevant by the filter and 21 have tenure unclear. Rows were phrase-selected, so new investors are over-represented. beginner_guidance counts tenure alone (D-10 open). Pre-change files kept outside the repo as a session backup |
| evidence | `docs/ai_eval_test_report.md` §12; `docs/ai_eval_implementation_audit.md` D-8, D-10 |

### 8.10 D-10: beginner_guidance no longer matches on tenure alone

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | research / opportunities |
| actor | human (project owner: "A"); Claude Code (change) |
| decision | `research/opportunities.yaml`: removed `tenure: [new_under_1y]` from beginner_guidance's match rule; it now needs `unmet_need=fund_guidance` or `in_app_pain=fund_selection` |
| prompt_version | n/a |
| before_count | beginner_guidance 100 records, priority 101.0, rank 2 |
| after_count | 7 records, priority 7.0, rank 9 of 9 shown. 168 tests passing |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | Of the 7, Claude Code reads only `4f94b6b3`, `5d28becd` and partly `cc637ae7` as fund-choice problems; `503f23b3`, `d28335d3`, `5cd15142`, `cde6d3ef` look mis-tagged and were not corrected |
| evidence | `docs/ai_eval_implementation_audit.md` D-10; `tests/test_ai_eval_edge_cases.py` |

### 8.11 Corrections to 4 records mis-tagged as fund selection

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | human review / Golden Dataset |
| actor | human (project owner: "accept all"); Claude Code (proposal and application) |
| decision | `503f23b3` in_app_pain fund_selection -> sip_management. `d28335d3` in_app_pain fund_selection -> kyc_onboarding, unmet_need other -> responsive_support. `5cd15142` in_app_pain fund_selection -> redemption_withdrawal, unmet_need flexible_sip -> fast_redemption. `cde6d3ef` in_app_pain fund_selection -> sip_management, unmet_need easy_mandate_control -> responsive_support. Written to `data/review/golden_sample_300.xlsx` with reviewer notes; promoted and rebuilt (version a595cd2f1576) |
| prompt_version | tag-v4; codebook v3 |
| before_count | beginner_guidance 7; responsive_support 25; redemption_speed 29; mandate_reliability 72 |
| after_count | beginner_guidance 3 (below the 5-record minimum, shown as insufficient); responsive_support 27; redemption_speed 30; mandate_reliability 71; flexible_sip 40 (unchanged) |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | 7 field values on 4 rows |
| known_limitations | Proposals were Claude Code's reading; #2 pain could be app_bug and #3 need could be other. Pre-change files kept outside the repo as a session backup |
| evidence | `docs/ai_eval_implementation_audit.md` D-10 |

### 8.12 D-4: cancellation split from flexible-SIP demand

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | codebook / Golden Dataset |
| actor | human (project owner: D-4 "No", then "D-4 go ahead" after seeing the 8 records); Claude Code (proposal and application) |
| decision | `codebook.yaml` (version kept at 3, change commented): added in_app_pain `sip_cancellation`; `sip_management` definition no longer includes stopping. Retagged 8 records: `e45241db`, `6652a87d`, `404cb625`, `cde6d3ef` pain -> sip_cancellation; `14d8cd4e` pain app_bug -> sip_cancellation, need flexible_sip -> responsive_support; `7ba7c141` pain app_bug -> sip_cancellation, need flexible_sip -> reliable_app; `c657e388` pain sip_management -> fees_charges, need flexible_sip -> lower_fees; `9e7d48f7` pain sip_management -> app_bug, need unclear -> responsive_support. Reviewer notes record each change; promoted and rebuilt (version 6a731d43e321) |
| prompt_version | tag-v4; codebook v3 (+ sip_cancellation) |
| before_count | flexible_sip 40, priority 58.0; responsive_support 27 |
| after_count | flexible_sip 32, priority 46.0; responsive_support 29. 169 tests passing |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | 12 field values on 8 rows |
| known_limitations | Future tagging runs will use the new value, but existing rows outside flexible_sip's 40 were not re-checked for stopping (all rows tagged sip_management were among those 40). `404cb625` had been adjudicated sip_management in the 20-record set before this split. About 8 of the remaining 32 look like payment or unrelated problems; not corrected. Pre-change files kept outside the repo as a session backup |
| evidence | `docs/ai_eval_test_report.md` §13; `docs/ai_eval_implementation_audit.md` D-4 |

### 8.13 Flexible SIP: 14 records corrected after one-by-one reading

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | human review / Golden Dataset |
| actor | human (project owner: "accept all"); Claude Code (proposal and application) |
| decision | 25 field changes on 14 rows. AutoPay/payment → in_app_pain mandate_autopay, unmet_need easy_mandate_control: `93305fa1`, `4fbd9285`, `b5cc9a4d`, `7f942899`, `e369bd42`, `5e019da4`, `6b31505a`; `2a00363f` pain only. `e9921f8c` pain portfolio_display, need responsive_support. `20854996`, `d0fb4dbd` need reliable_app. `99a2b9e0` behavior continue_sip, pain app_bug, need reliable_app. `9355d0c4` need unclear. `eb353ebf` pain sip_cancellation, need responsive_support. Reviewer notes record old -> new; promoted and rebuilt (version f46cbc5ea95f) |
| prompt_version | tag-v4; codebook v3 (+ sip_cancellation) |
| before_count | flexible_sip 32 (46.0); mandate_reliability 71 (112.0); app_reliability 41; responsive_support 29; portfolio_tracking 3 |
| after_count | flexible_sip 18 (25.0); mandate_reliability 78 (120.0); app_reliability 42; responsive_support 30; portfolio_tracking 4. 169 tests passing |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | 25 field values on 14 rows |
| known_limitations | Proposals were Claude Code's reading; `5e019da4` and `93305fa1` are mixed complaints. Four records about choosing to pause were kept. Pre-change files kept outside the repo as a session backup |
| evidence | `docs/ai_eval_test_report.md` §14 |

### 8.14 App reliability: 21 records corrected after one-by-one reading

| Field | Value |
|-------|-------|
| date | 2026-10-28 |
| stage | human review / Golden Dataset |
| actor | human (project owner: "accept all"); Claude Code (proposal and application) |
| decision | 34 field changes on 21 rows, as listed in `docs/ai_eval_test_report.md` §15. Reviewer notes record old -> new; promoted and rebuilt (version 727af6426411) |
| prompt_version | tag-v4; codebook v3 (+ sip_cancellation) |
| before_count | app_reliability 42; mandate_reliability 78; flexible_sip 18; responsive_support 30; fee_transparency 11; portfolio_tracking 4; market_fall_reassurance 6 |
| after_count | app_reliability 26; mandate_reliability 77; flexible_sip 19; responsive_support 31; fee_transparency 12; portfolio_tracking 8 (now shown); market_fall_reassurance 3 (now insufficient). 169 tests passing |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | 34 field values on 21 rows |
| known_limitations | Proposals were Claude Code's reading; kyc_onboarding fits `0b9bd218` and `3f9d416a` only loosely. Off-topic stock-trading rows remain in the Golden Dataset. Pre-change files kept outside the repo as a session backup |
| evidence | `docs/ai_eval_test_report.md` §15 |

## Stage 9 — Deployment (decision records)

### 9.1 Public GitHub repository for Streamlit Community Cloud

| Field | Value |
|-------|-------|
| date | 2026-10-26 |
| stage | deployment |
| actor | human (user instructed a PUBLIC repo `groww-sip-discovery` and Streamlit Community Cloud); Claude Code |
| decision | Dashboard now reads only `data/export/` (`golden_public.jsonl`, `quality_metrics.json`, written by `python -m research.build`) and builds its index in a temp folder; secrets read from `st.secrets`, then environment, then `.env`. `requirements.txt` holds only the four dashboard packages, pinned (streamlit 1.50.0, pandas 2.3.3, altair 5.5.0, PyYAML 6.0.3); pipeline packages moved to `requirements-pipeline.txt`. `.gitignore` excludes `.env`, AGENTS.md, data/raw, data/processed, data/manual, data/review, logs and databases. Commits use the GitHub noreply address |
| before_count | not applicable |
| after_count | Repository https://github.com/kanhapal39/groww-sip-discovery (public): 75 paths; data/ contains only data/export (300 public Golden rows and quality metrics) |
| model_used | none |
| cost_estimate | $0.00 |
| human_correction | none |
| known_limitations | Clean-clone test (fresh `git clone`, no `.env`, Python 3.12.15, only requirements.txt): all five pages render; clicking a suggested question shows evidence and "answer model is not configured"; peak memory 166 MB in Streamlit's test runner (a live server adds its own overhead). Secrets check over tracked files, full history and all git objects: YOUTUBE_API_KEY, GROQ_API_KEY, APIFY_TOKEN all pass. The public repo exposes the 300 exported rows (Play Store review and Reddit text, tags, source links; no usernames or reviewer names) and all project documentation, including the accepted terms-of-service risks |
| evidence | `.gitignore`, `requirements.txt`, `app/data.py`, `research/build.py` |
