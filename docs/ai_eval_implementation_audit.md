# AI Evaluation — Implementation Audit

**Date:** 2026-10-28 · **Branch:** `ai-eval-audit` · **Author:** Claude Code, at the project owner's request

This audit compares the expectations in the two evaluation documents against the code that exists, then records what this branch changed. Companion documents:

- `docs/ai_evaluation_documentation.md` — the AI Evaluation document (Cases A–C, human-review Cases 1–3). Cited below as **Eval**.
- `docs/edge_cases_and_failure_modes.md` — 20 edge cases and the scorecard. Cited below as **Edge**.
- `docs/ai_eval_test_report.md` — per-edge-case test results, severities and retests.
- `docs/ai_eval_ground_truth_template.md` — template for the 20-record labelled set (not yet labelled).

## 1. Sources read and method

**Locating the evaluation documents.** Before this branch, the repository held no AI Evaluation or Edge Cases document under any name: the root, `docs/` and the code were searched for "evaluation", "edge case" and "failure mode". The only hit was `docs/source_access_plan.md`, which uses "evaluate" for source assessment. The two documents were supplied by the project owner as Word files. They were converted to Markdown, with the text verified identical character for character after stripping formatting, and committed as the files above (commit `3c03c60`).

**Project instructions.** `AGENTS.md` exists in the working copy but is gitignored (`.gitignore` line 10; evidence log §9.1). It is therefore absent from the public GitHub repository. This is a note, not a finding. Its rules were followed: no Groq or Apify calls, no Golden Dataset writes, and tests were run.

**Documents read:** `README.md`, `docs/project_brief.md`, `docs/architecture.md`, `docs/implementation_plan.md`, `docs/source_access_plan.md` (grep for evaluation terms), `docs/golden_dataset_policy.md`, `docs/evidence_validation.md`, `docs/limitations.md`, `docs/data_dictionary.md`, `docs/evidence_log_notes.md` (§7–9), `config.yaml`, `codebook.yaml`, `research/opportunities.yaml`.

**Code read:** `research/` (all modules), `app/data.py`, `app/views/{overview,opportunities,evidence}.py`, the quote, reason and provenance checks in `pipeline/` and `collect/`, and the tests in `tests/`.

**How results were established.**
- **Unit tests:** `pytest`, with synthetic fixtures and a fake answer model.
- **Local retrieval probe:** a script outside the repo builds a throw-away index from `data/export/golden_public.jsonl` (the dashboard's input: 300 public rows) and runs the deterministic retrieval and opportunity code. **No LLM was called**, no data was collected, and no project data file was written.
- **Status labels:** a result is marked VERIFIED only when a test exercising that behaviour ran and passed. The existence of a function or test file was not enough.

## 2. How the engine works (as implemented)

| Stage | Code | What it does |
|---|---|---|
| Collection | `collect/*.py`, `collect/base.py:accept_record` | Raw JSONL with record ID, source URL and collection time; records without these are rejected |
| Cleaning | `pipeline/clean.py:dedupe` | Exact and near-duplicate removal (rapidfuzz ≥ 95) before tagging; drops kept with a reason |
| Relevance filter | `pipeline/filter.py` | Groq LLM yes/no/unsure plus a keyword rescue rule |
| Tagging | `pipeline/tag.py` | Groq LLM against `codebook.yaml` v3 (draft); `check_quote` verifies quotes; `is_hypothesis` flags implied tags |
| Golden Dataset | `pipeline/export.py` | Promotes only rows marked "approved" in the review workbook, adding provenance |
| Index | `research/store.py` | SQLite + FTS5 built from the approved, public rows |
| Retrieval | `research/retrieval.py:search` | Rule-based question-to-tag mapping, word coverage and BM25 tie-break. **No semantic or vector search** |
| Answers | `research/answer.py:answer_question` | Evidence gate (≥ 3 strong matches) → LLM summary citing R1..Rn → citation validation; limitations computed in code |
| Opportunities | `research/opportunities.py:build` + `opportunities.yaml` | Human-written hypotheses; a record matches if any listed tag matches; priority formula shown to users |

## 3. Requirement-to-code mapping

Result columns: **Before** = state of `main` at `0d11e77`; **After** = state on this branch. "EC n" refers to the numbered edge cases in the audit brief (also used as test names); "Edge n" refers to the Edge Cases document.

| ID | Requirement | Related criterion | Source (file:function) | Test before → after | Before | After | Evidence | Corrective action |
|---|---|---|---|---|---|---|---|---|
| R-01 | Keyword overlap alone must not make a record evidence | EC1, EC12; Edge 1, 10; Eval Case C | `research/retrieval.py:query_terms`, `term_hits`; `research/answer.py:strong_matches` | none → `test_ec1_*` | NOT IMPLEMENTED | PARTIALLY IMPLEMENTED (deterministic part VERIFIED) | Case C reproduced: 9 strong matches; 6 matched only "experience", "time", "setting", "up" (e.g. "up" prefix-matched "upi", "upstox"). Now 2 matches, and the question abstains | Done: generic stopwords, whole-word match for short terms, ≥ 2 matched words for text-only matches. Remaining: deciding true relevance still needs human or LLM judgement |
| R-02 | Payment/mandate failures not counted as flexible-SIP demand | EC2; Edge 2; Eval Case 1 | `research/opportunities.py:held_out`; `opportunities.yaml` `flexible_sip.hold_out` | none → `test_ec2_*` | NOT IMPLEMENTED | IMPLEMENTED AND VERIFIED (counting); tags themselves unchanged | Record `a140a1f6` "not able to set up auto pay" is tagged `in_app_pain=mandate_autopay`, `unmet_need=flexible_sip`. 4 such records are now held out of flexible_sip and listed for review | Done. Data decision needed: correct the tags in the review workbook (§5, D-3) |
| R-03 | Cancellation friction kept distinct from pause/edit demand | EC3; Edge 3; Eval Case 2, §9 | `research/opportunities.py:breakdown`; `opportunities.yaml` `flexible_sip.breakdown` | none → `test_ec3_*` | NOT IMPLEMENTED | PARTIALLY IMPLEMENTED | Real data: of 39 flexible_sip records, 10 mention pausing/skipping, 10 editing amount/date, 10 only cancelling/stopping, 9 none of these (keyword rules) | Done: breakdown and validation gap shown. Remaining: a codebook value for explicit pause demand vs cancellation (D-4) |
| R-04 | No motivation inferred without evidence | EC4; Edge 4; Eval Case 3 | `research/answer.py:SYSTEM_PROMPT` (basis stated/inferred; new rule on reasons for stopping) | none → none | IMPLEMENTED BUT NOT VERIFIED | IMPLEMENTED BUT NOT VERIFIED | Depends on LLM output; no live call allowed. Tags: record `a7c2a38b` ("cancel it with profit of 9 percent") is tagged `trigger=support`, `unmet_need=flexible_sip`, `is_hypothesis=False` | Run the prompt against the labelled set (§6) |
| R-05 | Tenure/demographics not inferred; segment claims need segment evidence | EC5, EC7, EC21; Edge 5, 17; Eval Case C | `research/retrieval.py:SEGMENT_RULES`, `segment_targets`; `research/answer.py:strong_matches`, `limitations` | none → `test_ec5_ec7_ec21_*` | NOT IMPLEMENTED ("first" and "new" mapped to `start_sip`; "start" mapped to tenure=new) | PARTIALLY IMPLEMENTED (retrieval VERIFIED) | 274 of 300 public rows have tenure "unclear"; 10 are new_under_1y. One of those 10 ("I really wish I could start Sip in those international index funds") states no tenure | Done: segment questions use only segment-tagged records and carry a note. Remaining: tenure tags are AI inferences (D-3) |
| R-06 | Explicit vs implied tags distinguished | EC6 | `pipeline/tag.py` (`is_hypothesis`); `research/answer.py:coverage`; `research/opportunities.py:build` (`implied`) | partial → `test_ec6_*` | PARTIALLY IMPLEMENTED (answers only) | IMPLEMENTED AND VERIFIED (counts shown) | 50 of 300 public rows have implied tags; flexible_sip: 13 of 39 | Done. `is_hypothesis` is per record, not per tag (limitation) |
| R-07 | Duplicates do not inflate counts or priority | EC8; Edge 7 | `pipeline/clean.py:dedupe` (upstream); `research/analysis.py:dedupe`; `research/store.py:build_database` | `test_clean.py::test_dedupe_*` (upstream) → + `test_ec8_*` | PARTIALLY IMPLEMENTED (cleaning only; index silently replaced repeated IDs) | IMPLEMENTED AND VERIFIED | 0 duplicate texts in the 300 public rows (measured). Guard added for answers, opportunities and the index | Done |
| R-08 | Percentages have defined numerator and denominator; labelled as dataset statistics | EC9; Edge 8; Eval Case A ("reported-lapse percentage denominator") | `research/opportunities.py:METRIC_DEFINITIONS`; `app/views/opportunities.py` | partial → `test_ec9_*` | PARTIALLY IMPLEMENTED (hover text only; no "not prevalence" statement) | IMPLEMENTED AND VERIFIED | Reproduced: mandate 66/300 = 22%, lapse 41/66 = 62% (pause/reduce/stop tags ÷ matching records) | Done |
| R-09 | Weak or short quotes not presented as strong evidence | EC10; Edge 9 | `pipeline/tag.py:check_quote`; `research/answer.py:limitations`; `research/opportunities.py:evidence_strength` | `test_tag.py::test_check_quote` → + `test_ec10_ec15_*` | PARTIALLY IMPLEMENTED | PARTIALLY IMPLEMENTED | 22 exact quotes are under 5 words; strength counts them like longer ones | Answers now flag short quotes. Remaining: strength label ignores quote length (D-5) |
| R-10 | Relevant records with different wording are retrieved | EC11; Edge 12 | `research/retrieval.py:TAG_RULES` | none → `test_ec11_*` | NOT IMPLEMENTED | PARTIALLY IMPLEMENTED | Rules added for "temporarily", "discontinue", "decrease", "change debit amount", "modify/edit". No semantic retrieval; recall not measurable without labels | Recall test needs labelled set (§6) |
| R-11 | Conflicting evidence surfaced | EC13, EC29; Edge 11 | `research/answer.py:limitations`, `SYSTEM_PROMPT` | none → `test_ec13_ec29_*` | NOT IMPLEMENTED | PARTIALLY IMPLEMENTED | Computed note lists behaviour mix; prompt asks the model to say when records disagree (model side untested) | — |
| R-12 | Source context does not change meaning unnoticed | EC14; Edge 13 | `research/retrieval.py:searchable(include_context=False)`; `record_block` sends thread context to the model | none → `test_ec14_*` | NOT IMPLEMENTED (thread title words counted as the reply's own) | PARTIALLY IMPLEMENTED | Market-crash question: 3 replies had 0 of the question's words ("react", "market", "crash") in their own text and matched only via their thread title (e.g. "Do some research about nifty alpha 50 index."). They are no longer strong evidence | Remaining: other-app / hypothetical context needs human review |
| R-13 | Old evidence not presented as current | EC15; Edge 14 | `research/answer.py:limitations` | none → `test_ec10_ec15_*` | NOT IMPLEMENTED (year range shown only) | IMPLEMENTED AND VERIFIED (note) | 134 of 300 public rows were published 2019–2022; 181 before 2025 (`research.recent_from_year`) | Done |
| R-14 | Citations point to real records; quotes come from records | EC16; Edge 18 | `research/answer.py:validate_points`; `app/ui.py:record_card` (quotes from stored rows) | `test_answer_keeps_only_cited_points` → + `test_ec16_ec17_*` | IMPLEMENTED AND VERIFIED (citation range) | IMPLEMENTED AND VERIFIED (citation range + verbatim quotes in model text) | Before: a point could put invented words in quotation marks and keep a valid R-number | Done. Remaining: whether a cited record *supports* a paraphrase is not checkable in code |
| R-15 | No unsupported claims or invented statistics in answers | EC17; Edge 18 | `research/answer.py:unsupported` (quotes, percentages) | none → `test_ec16_ec17_*` | NOT IMPLEMENTED (prompt instruction only) | PARTIALLY IMPLEMENTED (deterministic checks VERIFIED) | — | Semantic support needs labelled evaluation |
| R-16 | No claim that an intervention improves continuation | EC18, EC23; Edge 6, 15; Eval §8 | `research/answer.py:IMPACT_CLAIM`, `SYSTEM_PROMPT`; opportunities page labels intervention/experiment "qualitative judgements" | none → `test_ec18_ec19_ec23_*` | PARTIALLY IMPLEMENTED (labels, prompt) | IMPLEMENTED AND VERIFIED for answer text (regex); opportunity copy is human-written | Points/summaries predicting effects are removed and listed as removed | — |
| R-17 | Recommendations not based on complaints that do not show demand | EC19; Edge 15 | `opportunities.yaml` (human-authored); `research/opportunities.py:validation_gaps` | none → `test_ec3_*` | PARTIALLY IMPLEMENTED | PARTIALLY IMPLEMENTED | Intervention text is a draft written by Claude Code on 2026-10-26 (header of `opportunities.yaml`), not reviewed | D-2: product team review of `opportunities.yaml` |
| R-18 | Priority score justified; volume ≠ impact | EC20; Edge 16 | `research/opportunities.py:PRIORITY_FORMULA` | partial → `test_ec20_*` | PARTIALLY IMPLEMENTED (formula shown) | IMPLEMENTED AND VERIFIED (statement) | Formula weights record count; no link to continuation data | D-6: whether to keep ranking by volume |
| R-19 | Public complaints not treated as representative | EC22; Edge 8 | `research/answer.py:limitations`; `METRIC_DEFINITIONS["scope"]` | none → `test_ec22_*` | IMPLEMENTED BUT NOT VERIFIED | IMPLEMENTED AND VERIFIED | — | — |
| R-20 | Abstain below the evidence threshold | EC24, EC25; Edge 19 | `research/answer.py:answer_question`, `INSUFFICIENT_MESSAGE` | `test_insufficient_evidence_skips_the_model` → + `test_ec24_ec25_*` | PARTIALLY IMPLEMENTED: gate works, but Edge 19's own probe passed it with 3 irrelevant records | IMPLEMENTED AND VERIFIED (deterministic gate) | "Why do first-time investors discontinue SIPs after 12 months?": 3 → 1 strong match; no model call | Wording mismatch: D-1 |
| R-21 | Only approved, in-scope Golden Dataset records used | EC26 | `research/store.py:is_public`; `research/retrieval.py:search(public_only=True)`; `app/data.py` reads only `data/export/` | `test_public_rows_exclude_*` → + `test_ec26_*` | IMPLEMENTED AND VERIFIED | IMPLEMENTED AND VERIFIED | Rejected, pending, YouTube and no-provenance rows never reach answers | — |
| R-22 | Reproducible counts and citations | EC27; Edge 20 | `research/retrieval.py:search` (sorted by score, record_id); `app/data.py:answer` cache per question and dataset version | none → `test_ec27_*` | IMPLEMENTED BUT NOT VERIFIED | IMPLEMENTED AND VERIFIED (retrieval); generation not tested | Answer text from the LLM can vary; evidence set cannot | — |
| R-23 | Empty, malformed, duplicated, incomplete data handled | EC28 | `research/store.py:load_golden`, `build_database`; `research/opportunities.py:build` | none → `test_ec28_*` | PARTIALLY IMPLEMENTED (malformed line → raw `JSONDecodeError`) | IMPLEMENTED AND VERIFIED | Malformed line now raises `ValueError` naming the line; it is not skipped silently | — |
| R-24 | Secrets not exposed in UI, logs or errors | EC30 | `research/answer.py` (error shows exception type only); `.gitignore`; `app/data.py:_secret` | none → `test_ec30_*` | IMPLEMENTED BUT NOT VERIFIED | IMPLEMENTED AND VERIFIED | Tracked-file scan for Groq, Apify and Google key patterns: none found | — |
| R-25 | 20-record independently labelled evaluation | Eval §11; Edge §3 | — | — | NOT IMPLEMENTED | NOT IMPLEMENTED (template created) | No labelled set exists anywhere in the repo or data | `docs/ai_eval_ground_truth_template.md` |
| R-26 | Human corrections recorded | Eval §7 | `data/review/golden_sample_300.xlsx` notes; evidence log §7.2 | — | NOT IMPLEMENTED | NOT IMPLEMENTED | Evidence log §7.2: "no tag values were changed in the workbook, so no corrections are recorded" | D-3 |

## 4. Documentation versus code: inconsistencies found

| # | Document says | Code or data shows | Type |
|---|---|---|---|
| G-1 | Edge 19 and the audit brief: "Insufficient evidence in the Golden Dataset to answer this question reliably." | `research/answer.py:INSUFFICIENT_MESSAGE` = "The Golden Dataset does not contain enough evidence to answer this question reliably." | Wording only; the abstention behaviour is equivalent and is verified (R-20). **Not changed: decision D-1** |
| G-2 | `README.md` status table, `docs/golden_dataset_policy.md` "Current state", `docs/implementation_plan.md` Stage 7, `docs/limitations.md` "Golden Dataset": all 300 rows bulk-approved | Evidence log §7.2 (2026-10-27) and the data: 300 rows recorded as individually reviewed by the project owner | Documentation is stale. Not edited here; listed for the owner |
| G-3 | `docs/evidence_validation.md` "What is not validated": "no individually reviewed Golden rows exist yet" | Same as G-2 | Stale. The point that tag accuracy is unmeasured still holds |
| G-4 | Eval Case A/B tables: "Human-reviewed records 66 of 66", "43 of 43" | True as review status. But per §7.2 no tags were corrected, and the records the Eval document itself flags as mis-tagged (Cases 1–3) are among the approved rows with their original tags | "Human-reviewed" means approved as-is; it is not independent ground truth |
| G-5 | Eval Case B: 43 records, priority 63.0 | Reproduced exactly on `main`. On this branch: 39 records, priority 58.0 (4 mandate/AutoPay records held out) | Change caused by fix R-02; recorded as an addendum in the Eval document, not by rewriting Case B |
| G-6 | `data/processed/research.db` (local, gitignored) | Built before §7.2; shows 0 individually reviewed, so labels read "(unverified)". The dashboard does not use it (it reads `data/export/`, which is current) | Local stale index; rebuild with `python -m research.build` when convenient |
| G-7 | `docs/project_brief.md`: "No source is approved for collection", "No data has been collected yet" | Collection ran (evidence log §1c, §5a, §6a) | Stale brief; out of scope for this audit |
| G-8 | `docs/architecture.md`: "No vector/semantic search" | Accurate | — |

## 5. Decisions needed from the product owner

- **D-1 — insufficient-evidence wording (G-1).** Which text is the intended user-facing copy? The code was left as it is. If the document's wording is chosen, change `INSUFFICIENT_MESSAGE`; the tests import the constant, so no test text changes.
- **D-2 — opportunity definitions.** `research/opportunities.yaml` is a draft by Claude Code, including the new `hold_out` and `breakdown` rules. It needs product review before scores are used to prioritise.
- **D-3 — tag corrections.** The review recorded no corrections. Known mis-tags include `a140a1f6` (AutoPay setup tagged flexible_sip), `a7c2a38b` (cancel-with-profit tagged flexible_sip and trigger support) and `5a343cb7` (tenure inferred). They should be corrected in `data/review/golden_sample_300.xlsx` by a reviewer, then promoted with `python -m pipeline.export golden`. Claude Code did not edit the dataset.
- **D-4 — codebook.** Add a value or field separating explicit pause/skip/edit requests from cancellation friction, so this no longer rests on keyword rules.
- **D-5 — evidence strength.** Decide whether short (under 5-word) or repaired quotes should count towards "Strong".
- **D-6 — priority.** Keep ranking by evidence volume (now stated on the page), or add a manually scored impact/effort input.
- **D-7 — segment filter.** Questions naming first-time or beginner investors now answer only from records tagged `tenure=new_under_1y`; in the current data they usually abstain. Confirm this is the desired behaviour.

## 6. Evaluation evidence available today

| Category | Count | Source |
|---|---|---|
| Test cases designed (Edge document) | 20 | `docs/edge_cases_and_failure_modes.md` |
| Edge cases in the audit brief | 30 | — |
| Automated tests executed / passed / failed (final) | 162 / 162 / 0 | `pytest tests/`; 24 of them new in `tests/test_ai_eval_edge_cases.py` |
| Tests blocked | Every check of LLM answer quality: live calls are not allowed | §7 of the test report |
| Human-reviewed (approved) Golden rows | 300 (status by owner statement, §7.2) | `data/export/golden_public.jsonl` |
| Independently labelled ground-truth records | **0** | — |
| Human corrections recorded | **0** | Evidence log §7.2 |
| AI-generated classifications | 300 rows × 15 fields (gpt-oss-120b, tag-v4) | — |
| Inter-model agreement (existing, not ground truth) | 30 items: behaviour 80%, lapse type 90%, trigger 57% | `docs/limitations.md`; evidence log |
| Unverified hypotheses | 10 opportunity definitions; the Eval document's causal links to 12-month continuation | `opportunities.yaml`; Eval §8 |

No accuracy, precision, recall or agreement-with-human figure is reported. There is no labelled ground truth to compute them against.
