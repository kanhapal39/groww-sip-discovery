# AI Evaluation — Edge-Case Test Report

**Date:** 2026-10-28 · **Branch:** `ai-eval-audit` · **Requirement mapping:** `docs/ai_eval_implementation_audit.md`

## 1. Summary

The engine's evidence pipeline was already sound in several places:
- It only uses approved, public Golden Dataset rows.
- It abstains below 3 matching records without calling a model.
- It drops answer points that cite no record.
- Quotes shown to users come from stored records.

The audit found these gaps:
- **Retrieval let unrelated records through.** Words like "experience" and "time", and "up" matching "upi", counted as relevance. So did thread titles.
- **Abstention probe missed.** The Edge document's own abstention question passed the evidence gate with 3 irrelevant records.
- **Unchecked answer text.** Quoted words, percentages and impact predictions inside the model's text were never checked.
- **Mis-tagged records counted.** An AutoPay setup failure counted as demand for flexible SIP controls.
- **Investor segments were never enforced.**

Each gap now has a fix and a regression test. All 162 tests pass. Checks that depend on what the LLM writes remain untested: live model calls were out of scope, and there is no labelled ground truth.

## 2. Test execution log

| Step | Command | Result |
|---|---|---|
| Baseline (`main` at `0d11e77`, before any change) | `.venv/bin/python -m pytest tests/ -q` | **138 passed** |
| New tests, first run | `.venv/bin/python -m pytest tests/test_ai_eval_edge_cases.py -q` | 22 passed, **2 failed** (EC11: "change debit amount" not mapped; EC14: thread-title-only records disappeared from search, which would also have changed the Evidence Explorer) |
| After fixing both | same | **24 passed** |
| Full suite | `.venv/bin/python -m pytest tests/ -q` | **162 passed** (138 existing + 24 new); no existing test changed |
| Local retrieval probe, before and after | script outside the repo; index built in a temp folder from `data/export/golden_public.jsonl`; deterministic retrieval and opportunity code only | See §4. No LLM call, no network, no project file written |

Environment: Python in `.venv` (macOS); no dependency was installed.

## 3. Results by edge case

Status before: **FAIL** = the behaviour was reproduced. **GAP** = no protection existed, but the failure was not observed in the data. **PASS** = already handled. **NOT TESTABLE** = needs a live model or labelled data.
Retest: the result of the named regression test on this branch.

Severity uses the brief's scale:
- **CRITICAL:** fabricated evidence, false claims, prohibited data access, or failure to abstain when required.
- **HIGH:** wrong classification, unsupported conclusions, broken citations, or use of unapproved evidence.
- **MEDIUM:** retrieval misses, misleading counts, missing context, or incomplete failure handling.
- **LOW:** presentation issues.

### A. Relevance and classification

| EC | Scenario / input | Expected | Actual before | Status before | Severity | Root cause | Fix | Regression test | Retest |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Eval Case C question: "What problems do first-time SIP investors experience when setting up their first SIP?" | Unrelated records are not evidence | 9 strong matches. 6 matched only on "time", "experience", "setting", "up" (e.g. UPI for an IPO, "Quick Order Retry…"); 3 matched `start_sip` because the question says "first" | FAIL | HIGH | Generic words were content terms; prefix matching for 2-letter terms; `\bfirst\b` → `start_sip` | Generic stopwords; whole-word match below 4 letters; ≥ 2 matched words for text-only matches; "first"/"new" no longer imply starting | `test_ec1_generic_words_do_not_establish_relevance`, `test_ec1_one_shared_keyword_is_not_a_strong_match` | PASS. Real data: 2 matches, so the question abstains. Still open: the suggested "starting a SIP" question still shows "You can start a SIP" through its tag (§4) |
| 2 | Observed record `a140a1f6` "not able to set up auto pay" (`in_app_pain=mandate_autopay`, `unmet_need=flexible_sip`) | Counted under payment reliability, not flexible SIP | Counted in both opportunities | FAIL | HIGH | Tagging error (approved as-is); "any tag matches" rule | `hold_out: {in_app_pain: [mandate_autopay]}` on flexible_sip; held-out records listed for review | `test_ec2_payment_failure_is_held_out_of_flexible_sip` | PASS. Real data: 4 records held out; flexible_sip 43 → 39, priority 63.0 → 58.0 |
| 3 | Observed "cancelling SIPs is really hard on this app" | Cancellation friction kept separate from pause demand | Counted as flexible-SIP evidence with no distinction | FAIL | HIGH | Codebook `sip_management` covers both pausing and stopping | Keyword breakdown and validation gap on the opportunity | `test_ec3_cancellation_is_reported_separately_from_pause_demand` | PASS (breakdown). Real data: 10 pause/skip, 10 edit, 10 cancel/stop only, 9 none |
| 4 | Observed "I started sip and then cancel it with profit of 9 percent" | Motivation marked unknown | Record tagged `trigger=support`, `is_hypothesis=False`; the model's behaviour cannot be tested offline | NOT TESTABLE (answer); FAIL (tag, observed) | HIGH | LLM tagging; no correction in review | Prompt rule: "Do not state why someone stopped… unless the record says why" (answer-v2) | none (needs live model) | NOT RETESTED |
| 5, 7, 21 | Segment questions ("first-time", "beginner") | Only segment-supported records; segment limitation stated | Segment words mapped to `start_sip` or ignored; records without tenure evidence used | FAIL | HIGH | No segment concept in retrieval | `SEGMENT_RULES`; `strong_matches` requires the segment tag; limitation note | `test_ec5_ec7_ec21_segment_questions_use_only_segment_tagged_records` | PASS. Remaining risk: tenure tags themselves are AI inferences (e.g. `5a343cb7`) |
| 6 | Implied vs stated tags | Shown separately | Shown in answers; absent on opportunities | GAP | MEDIUM | — | `implied` count per opportunity, shown on page | `test_ec6_implied_tags_are_counted_separately` | PASS. Real data: flexible_sip 13 of 39 implied |

### B. Retrieval and evidence quality

| EC | Scenario / input | Expected | Actual before | Status before | Severity | Root cause | Fix | Regression test | Retest |
|---|---|---|---|---|---|---|---|---|---|
| 8 | Same text under two IDs; same ID twice | Counted once | Not deduplicated after cleaning; index replaced repeated IDs but still added a second search entry | GAP (0 duplicate texts in real data) | MEDIUM | Guard only in `pipeline/clean.py` | `research.analysis.dedupe` in answers and opportunities; index keeps the first row per ID | `test_ec8_duplicates_do_not_inflate_counts` | PASS |
| 9 | "Report a lapse 47%" | Numerator, denominator, not prevalence | Hover help only; no "not prevalence" statement | GAP | MEDIUM | — | `METRIC_DEFINITIONS` shown on the page | `test_ec9_percentages_have_defined_denominators` | PASS. Real data: 66/300 = 22%; lapse 41/66 = 62% |
| 10 | Short quote ("You can start a SIP") | Flagged | 22 exact quotes under 5 words, unflagged | GAP | MEDIUM | — | Limitation note in answers | `test_ec10_ec15_short_quotes_and_old_evidence_are_flagged` | PASS (answers). Evidence strength still ignores length (decision D-5) |
| 11 | "temporarily discontinue", "reduce monthly contribution", "change debit amount" | Mapped to relevant tags | Partly unmapped | FAIL | MEDIUM | Rule-based retrieval; no semantic search | More tag rules | `test_ec11_alternative_wording_maps_to_tags` | PASS for these phrases. **Recall not measured** (no labelled set) |
| 12 | Broad tag retrieval | Tag alone not proof | Same as EC1 for "first" → `start_sip` | FAIL | HIGH | Over-broad tag rules | See EC1 | EC1 tests | PASS (rules). Tag-only matches are still accepted |
| 13, 29 | Records with different behaviours | Mix surfaced | Not mentioned | GAP | MEDIUM | — | "Mixed evidence" limitation; prompt rule | `test_ec13_ec29_mixed_evidence_is_reported` | PASS (note). Model side untested |
| 14 | Reddit reply matching only via its thread title | Not evidence by itself | Counted as the reply's own words. Real data: 3 replies on the market-crash question | FAIL | MEDIUM | `searchable()` included `context` | Relevance counts exclude context; context still ranks and still shows in the Explorer | `test_ec14_thread_context_alone_is_not_evidence` | PASS |
| 15 | Records from 2019–2022 | Flagged as possibly outdated | Year range only | GAP | MEDIUM | — | Limitation note using `research.recent_from_year` | `test_ec10_ec15_*` | PASS |
| 16 | Point cites R99, or quotes words not in its record | Point removed | R99 removed (existing test); invented quote inside a valid citation kept | GAP | CRITICAL | Quotes in model text were never checked | `unsupported()`: quoted spans of ≥ 3 words must appear in the cited records | `test_ec16_ec17_fabricated_quotes_and_numbers_are_removed` | PASS |
| 17 | "40% of investors…" from the model | Removed | Kept (prompt instruction only) | GAP | CRITICAL | No numeric check | Percentages must appear in the cited records | same | PASS. Semantic support of paraphrases: **not testable** in code |

### C. Insight generation and recommendations

| EC | Scenario / input | Expected | Actual before | Status before | Severity | Root cause | Fix | Regression test | Retest |
|---|---|---|---|---|---|---|---|---|---|
| 18, 19, 23 | Model writes "A pause option will improve 12-month SIP continuation" | Removed or marked a hypothesis | Shown if cited | GAP | HIGH | Prompt instruction only | `IMPACT_CLAIM` check on points and summary; removed statements listed on the page | `test_ec18_ec19_ec23_impact_claims_are_removed` | PASS. Opportunity interventions remain human-written "qualitative judgements" (D-2) |
| 20 | Priority read as impact | Volume ≠ impact stated | Formula shown, no statement | GAP | LOW | — | Formula text states it ranks evidence volume, not impact | `test_ec20_priority_is_described_as_evidence_volume` | PASS |
| 22 | Representativeness | Stated | Stated in answer limitations | PASS | — | — | — | `test_ec22_answers_state_sample_is_not_representative` | PASS |

### D. Safe failure and reliability

| EC | Scenario / input | Expected | Actual before | Status before | Severity | Root cause | Fix | Regression test | Retest |
|---|---|---|---|---|---|---|---|---|---|
| 24, 25 | Edge 19 probe: "Why do first-time investors discontinue SIPs after 12 months?" | Abstain without calling the model | Real data: 3 strong matches (all `start_sip` via "first"), so the gate passed and the model would be called. Whether the model would then have abstained was not tested | FAIL (deterministic gate) | CRITICAL | EC1/EC5 root causes | EC1 and EC5 fixes | `test_ec24_ec25_abstains_on_the_edge_case_doc_question`, `test_ec25_answer_with_every_point_removed_abstains` | PASS. Real data: 1 match, abstains |
| 25 (wording) | Message text | Edge 19 text vs code text | Different wording, same meaning | Doc/code inconsistency | LOW | — | **Not changed** (decision D-1) | existing tests use the constant | — |
| 26 | Rejected, pending, YouTube and no-provenance rows | Never evidence | Excluded | PASS | — | — | — | `test_ec26_unapproved_and_out_of_scope_records_are_never_evidence` | PASS |
| 27 | Same question twice | Same evidence and order | Deterministic sort | PASS (now tested) | — | — | — | `test_ec27_retrieval_is_deterministic` | PASS. LLM wording can vary: **not tested** |
| 28 | Empty index, missing index, rows without fields, malformed JSONL | No crash; malformed data reported clearly | Malformed line → raw `JSONDecodeError` | GAP | MEDIUM | — | `load_golden` raises `ValueError` with the line number; never skips | `test_ec28_empty_missing_and_incomplete_datasets`, `test_ec28_malformed_golden_file_fails_loudly` | PASS |
| 30 | Provider error containing a key; tracked files | No key in output or repo | Error shows exception type only | PASS (now tested) | — | — | — | `test_ec30_model_errors_do_not_leak_secrets`, `test_ec30_no_credentials_in_tracked_files` | PASS |

## 4. Real-data probe: before vs after

Deterministic retrieval only, over the 300 public Golden rows. "Strong" = records passing the evidence gate (at most 12 are sent to the model; 3 are required).

| Question | Strong before | Strong after | Evidence shown, kept from before |
|---|---|---|---|
| Why do investors pause or stop their SIPs? *(suggested)* | 40 | 40 | 12 of 12 |
| Why do AutoPay payments fail? *(suggested)* | 40 | 40 | 11 of 12 |
| What do investors say about returns in the first year? *(suggested)* | 29 | 32 | 3 of 12 — see note |
| How do investors react to a market crash? *(suggested)* | 12 | 9 | 9 of 12 (3 thread-title-only replies removed) |
| What problems do investors face when starting a SIP? *(suggested)* | 18 | 31 | 7 of 12 |
| Eval Case C question | 9 | 2 → abstains | 2 of 9 |
| Edge 19 probe (12-month discontinuation) | 3 → model called | 1 → abstains | 0 of 3 |
| "What about crypto staking yields?" (control) | 0 | 0 | — |
| "gold vs silver" (control) | 2 | 2 | — |

**Note on the returns question.** The evidence changed substantially:
- **Before:** mostly general Reddit discussion containing "returns" and "year", plus off-topic records ("international index funds", gold prices).
- **After:** mostly records tagged `returns_nav_confusion` (NAV allotment, profit display), including "Started my first SIPs, but one is already in the negative. I am a beginner".

This is a change in ranking, caused by removing the over-broad "first" → `start_sip` rule. It is **not shown to be an improvement**; judging that needs the labelled set.

**Note on the starting question.** Strong matches rose from 18 to 31, because "starting" now also matches "started". The 12 records shown still include several that describe no problem when starting:
- "You can start a SIP…", the Eval Case C example, which still passes through its `start_sip` tag.
- "1CR milestone…".
- "It feels like the economy isn't performing…".

Tag-only matches still count as strong, so **EC1/EC12 is only partly solved for this question**. The model's `sufficient` judgement and human review remain the guard.

## 5. Opportunity figures: before vs after (real data)

| Opportunity | n before | n after | Priority before | Priority after | Change |
|---|---|---|---|---|---|
| mandate_reliability | 66 | 66 | 107.0 | 107.0 | none |
| flexible_sip | 43 | 39 | 63.0 | 58.0 | 4 mandate/AutoPay records held out for review |
| all others | — | — | — | — | none |

Duplicates removed: 0.

## 6. Files changed

- `research/retrieval.py`: stopwords, prefix rule and stemming, tag rules, segment rules, context excluded from relevance counts.
- `research/answer.py`: segment-aware strong matches, dedupe, quote/percentage/impact checks, removed-statement list, new limitation notes, prompt answer-v2.
- `research/opportunities.py`, `research/opportunities.yaml`: dedupe, `hold_out`, `breakdown`, implied count, metric definitions.
- `research/analysis.py`: `text_key`, `dedupe`.
- `research/store.py`: strict JSONL loading; first row per record ID.
- `app/views/opportunities.py`, `app/views/overview.py`, `app/views/evidence.py`: show definitions, breakdown, held-out records and removed statements; Explorer keeps thread-title matches.
- `tests/test_ai_eval_edge_cases.py`: 24 tests.

## 7. Remaining blockers and limitations

1. **No ground truth.** No independently labelled records exist, so retrieval recall and precision, classification accuracy and answer support cannot be measured. Template: `docs/ai_eval_ground_truth_template.md`.
2. **Answer quality is untested.** No live LLM calls were made, so prompt answer-v2 has not been run. Model-dependent behaviour (EC4, EC13 and EC23 model side; EC17 paraphrase support; EC27 wording stability) is untested.
3. **Dashboard visuals unchecked.** The Opportunities and Overview changes are covered by the existing smoke tests (`tests/test_app.py`), but a person has not checked the layout.
4. **Tag errors remain in the data.** The known mis-tags are approved and uncorrected (decision D-3). The hold-out rule limits their effect on one opportunity only.
5. **Rule heuristics.** The impact-claim and quote checks are regular expressions. They can miss paraphrased predictions, and they could remove a legitimate statement that uses "would reduce … stop". Removed statements are shown on the page, so this is visible rather than silent.
6. **Retrieval is still keyword and tag based** (no semantic search). Tag-only matches still count as strong.
