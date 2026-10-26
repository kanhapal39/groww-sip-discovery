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
| Stated vs inferred | tags `is_hypothesis`; answer points `basis` | Displayed separately on Investor Behaviour and in answers |

## What is not validated

- Tag accuracy against human labels: no individually reviewed Golden rows exist yet.
- Answer summaries can still paraphrase loosely (e.g. "often"); counts shown next to answers are computed in code.
- Language detection and date estimates for Reddit (ID-based windows) are rules, not verified labels.
