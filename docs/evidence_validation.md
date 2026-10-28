# Evidence validation

Checks that run in code, where they run, and what they do.

| Check | Where | What happens |
|---|---|---|
| Provenance on every raw record | `collect/base.py accept_record` | Record without ID, source URL or collection time is rejected |
| Usernames removed (Reddit) | `collect/reddit_apify.py` | Author fields never read; u/ mentions, profile links and known author names replaced by `[user]` before writing |
| Codebook values | `pipeline/tag.py validate_item` | Every field must be an allowed code; invalid items retried once, then stored as failed |
| Quote is verbatim | `pipeline/tag.py check_quote` | Exact substring → "exact". Otherwise the closest whole-word span (rapidfuzz) is used and marked "repaired"; below score 80 the quote is hidden |
| Reason invents terms | `pipeline/tag.py unsupported_reason_terms` | Flags reasons mentioning SIP, mandate or returns when the text does not |
| Relevance false negatives | `pipeline/filter.py should_rescue` | "no" upgraded to "unsure" when the text names a SIP/MF term and is a question or first person |
| Inter-model agreement | `python -m pipeline.tag agree` | Same items tagged by both models; per-field agreement and kappa; full parallel run gated at 70% on core fields |
| Golden provenance | `pipeline/export.py add_provenance` | Approved rows without a clean record or collection time are refused |
| Public eligibility | `research/store.py is_public` | Only approved, publishable, fully-provenanced rows are shown publicly |
| Insufficient evidence | `research/answer.py` | Fewer than `research.min_records` strongly matching records → insufficiency message, no model call |
| Citation check | `research/answer.py validate_points` | Answer points without a valid record citation are dropped; quotes shown come from stored records, not model text |
| Stated vs inferred | tags `is_hypothesis`; answer points `basis` | Displayed separately on Investor Behaviour and in answers; implied-tag count shown per opportunity |
| Strong match | `research/answer.py strong_matches`, `research/retrieval.py search` | A record is evidence only if it matches a question tag, or ≥ 60% and ≥ 2 of the question's content words appear in its own text, quote, reason or tags (thread titles excluded). Generic words such as "experience" and "time" are ignored |
| Segment attribution | `research/retrieval.py SEGMENT_RULES`, `research/answer.py strong_matches` | Questions naming first-time, new or beginner investors use only records tagged `tenure=new_under_1y`, with a limitation note |
| Verbatim quotes and numbers in answers | `research/answer.py unsupported` | A point or summary quoting ≥ 3 words not found in its cited records, or giving a percentage they do not contain, is removed and listed as removed |
| Impact predictions | `research/answer.py unsupported` (`IMPACT_CLAIM`) | Statements that a change will improve or reduce retention, continuation or cancellation are removed and listed as removed |
| Duplicates in counts | `research/analysis.py dedupe`; `research/store.py build_database` | Same record ID or same text counted once in answers and opportunities; the index keeps the first row per ID |
| Mis-tagged opportunity evidence | `research/opportunities.py held_out`; `opportunities.yaml hold_out` | Flexible-SIP records tagged `in_app_pain=mandate_autopay` are not counted and are listed for review |
| Malformed Golden file | `research/store.py load_golden` | A malformed line stops the build with its line number; it is never skipped |

## What is not validated

- Tag accuracy against human labels: rows are recorded as reviewed, but no tag was corrected and no independent labels exist yet (`docs/ai_eval_ground_truth_template.md`).
- Whether a cited record supports a paraphrased point is not checked in code. Answer summaries can still overgeneralise ("mainly", "new investors often"; observed 2026-10-28). Counts shown next to answers are computed in code.
- Language detection and date estimates for Reddit (ID-based windows) are rules, not verified labels.
