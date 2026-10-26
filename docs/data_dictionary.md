# Data dictionary

## RawRecord (`data/raw/*.jsonl`, all collectors)

| Field | Type | Meaning |
|---|---|---|
| record_id | string | Stable UUID5 of the source item (same item → same ID on re-collection) |
| source_url | string | Link to the review / comment / post |
| collected_at | ISO-8601 | When our collector fetched it (UTC) |
| text | string | Original text (Reddit: usernames replaced with `[user]`) |
| metadata.source | string | `play_store`, `youtube` or `reddit` |
| metadata.* | | Play Store: app_id, review_id, rating, reviewed_at. YouTube: video_id, video_title, comment_id, published_at, delete_after. Reddit: kind (post/comment), reddit_id, subreddit, published_at (null if unreliable), date_unknown, date_estimate, thread_question, post_id |

## Clean record (`data/processed/clean.jsonl`)

RawRecord fields plus: `source`, `year` (from publication date), `language` (en / hi / hinglish / other, rule-based), `context` (YouTube video title or Reddit thread question), `raw_file`.
`dropped.jsonl` holds every removed item with `drop_reason` (recollected, exact_duplicate, near_duplicate, short_text) and `drop_detail`.

## Filter result (`data/processed/filter_results.jsonl`)

record_id, source, app_id, year, `relevant` (yes / no / unsure — final), `model_label`, `reason` (≤10 words), `rescued_by_rule`, `error`, model, prompt_version, run, labelled_at.

## Tag result (`data/processed/tag_results.jsonl` gpt-oss, `tag_results_qwen.jsonl` qwen)

record_id, source_url, collected_at, source, app_id, year, relevance, priority, status (ok / failed), error, model, `tagged_by`, prompt_version, codebook_version, run, tagged_at, the 15 codebook fields below, confidence (0–1), is_hypothesis (true if any tag is implied), model_quote (as returned), `evidence_quote` (checked), quote_status (exact / repaired / hidden / none), quote_score, reason, reason_truncated, reason_unsupported_terms.

### Codebook fields (`codebook.yaml` v3)

behavior, lapse_type, trigger, expectation, checking, check_frequency, in_app_pain, emotion, outside_action, tenure, income_stability, age_band, money_source, influencer, unmet_need. Every field has an `unclear` value meaning the text gives nothing. Allowed values and definitions are in `codebook.yaml`.

## Golden Dataset row (`data/manual/golden_dataset.jsonl`)

All review-workbook columns (review_status, reviewer, reviewer_notes, stratum, record_id, source_url, app_id, year, relevance, text, evidence_quote, quote_status, codebook fields, confidence, is_hypothesis, reason, tagged_by, prompt_version, codebook_version) plus provenance joined at promotion: source, collected_at, published_at, context, kind, subreddit, rating, language.

## Dashboard index (`data/processed/research.db`)

`golden` table: the Golden Dataset row fields above plus `platform_detail` (app ID or r/subreddit), `individually_reviewed` (reviewer set and not the bulk marker), `public` (approved, publishable source, full provenance). `golden_fts`: FTS5 over text, evidence_quote, reason, context and tag words.

## Derived fields (computed in `research/analysis.py`)

- **Journey stage:** Starting = start_sip; Continuing = continue_sip or increase_sip; Lapsing = pause_sip, reduce_sip or stop_sip; others excluded.
- **Lapse records:** behavior in pause_sip, reduce_sip, stop_sip.
