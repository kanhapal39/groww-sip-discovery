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
| flexible_sip | 43 | 39 | 63.0 | 58.0 | 4 mandate/AutoPay records held out for review (see §10 for the figures after tag corrections) |
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

1. **Little ground truth.** *Updated 2026-10-28:* 20 records now carry owner-adjudicated labels (§9), so classification accuracy has a first, small measurement. Retrieval recall and precision and answer support are still unmeasured (§4 of `docs/ai_eval_ground_truth_template.md`).
2. **Answer quality is untested.** No live LLM calls were made, so prompt answer-v2 has not been run. Model-dependent behaviour (EC4, EC13 and EC23 model side; EC17 paraphrase support; EC27 wording stability) is untested.
3. **Dashboard visuals unchecked.** The Opportunities and Overview changes are covered by the existing smoke tests (`tests/test_app.py`), but a person has not checked the layout.
4. **Tag errors remain in the data.** *Updated 2026-10-28:* the 16 known mis-tagged records were corrected (D-3, §10). The 20-record check (§9) shows other tag errors remain; they are not corrected.
5. **Rule heuristics.** The impact-claim and quote checks are regular expressions. They can miss paraphrased predictions, and they could remove a legitimate statement that uses "would reduce … stop". Removed statements are shown on the page, so this is visible rather than silent.
6. **Retrieval is still keyword and tag based** (no semantic search). Tag-only matches still count as strong.

## 8. Live answer check (2026-10-28, approved by the project owner)

**What ran.** Each of the five suggested dashboard questions was asked once, through `research.answer.answer_question` with prompt `answer-v2` and the dashboard's model fallback. Raw results are in `data/processed/answer_eval_20261028.jsonl` (gitignored). Recorded usage: **8,537 tokens** for the 4 answered calls. The returns call's usage was not recorded (fixed below), so the true total is somewhat higher. Models: `openai/gpt-oss-120b` for questions 1–4; question 5 fell back to `openai/gpt-oss-20b` after a rate limit.

**Who judged support.** Claude Code read each point against the full text of the records it cites. **This is an AI review, not human ground truth.** The project owner should confirm or overrule it.

| Question | Status | Points | Supported | Partly supported | Not supported | Removed by code checks | Summary problem |
|---|---|---|---|---|---|---|---|
| Why do investors pause or stop their SIPs? | answered | 5 | 1 | 4 | 0 | 0 | "**mainly** because of…": a frequency claim the sample cannot support |
| Why do AutoPay payments fail? | answered | 4 | 3 | 1 | 0 | 0 | — |
| What do investors say about returns in the first year? | insufficient (model judged the 12 records off-topic) | — | — | — | — | 0 | — |
| How do investors react to a market crash? | answered | 3 | 2 | 1 | 0 | 0 | — |
| What problems do investors face when starting a SIP? | answered | 5 | 3 | 1 | 1 | 0 | "**New investors often** struggle…": the question did not ask about new investors and the records do not show frequency |
| **Total** | 4 answered, 1 abstained | **17** | **9** | **7** | **1** | **0** | **2 of 4** summaries overgeneralise |

**Citation problems** (a cited record does not support the point), 5 of 31 citations:
- **Q1 point 3, `1f63bed6`:** an IPO amount-block mandate, not a SIP mandate.
- **Q1 point 3, `99a2b9e0`:** an order-allotment delay, not a mandate failure.
- **Q1 point 4, `b445c5f5`:** about the SEBI overseas-investment limit, not market expectations.
- **Q1 point 5, `602cf3cd`:** advice to another person, not the writer's own stop.
- **Q5 point 2, `5a343cb7`:** "wish I could start Sip…" states no difficulty.

**Basis labels:**
- Q2 point 3 is marked `stated` but adds an inference ("indicating systemic issues").
- Q5 point 1 is marked `inferred` but adds "a common challenge".

**What worked:**
- Every point cited at least one record.
- No invented quotes or statistics.
- No impact predictions.
- One question abstained on the model's own judgement.
- The market-crash answer separated differing reactions (EC13).

**What the code checks cannot catch.** Partial support, generalisation ("mainly", "often", "common") and segment wording added by the model. These are EC17, EC21 and EC22 at generation level.

Two candidate fixes; neither is implemented, and both need the owner's go-ahead because they change what users see:
- **Segment check:** remove statements naming an investor segment the question did not ask about.
- **Frequency check:** flag frequency words in summaries.

**Bug found and fixed.** When the model judged the evidence insufficient, its token usage was dropped from the result, so quota use was under-reported. It is now returned (`test_model_saying_insufficient_is_respected`).

## 9. Classification accuracy on 20 labelled records (2026-10-28)

**What was done.** 20 random public records (seed 20261028; 22 known-problem records excluded) were labelled by the project owner with the engine's tags hidden. Disagreements were then adjudicated by the owner, who chose a final value for all 66 disputed field values. The owner accepted Claude Code's suggestion on every one and states they reviewed each row and agree. Method, per-record labels and caveats: `docs/ai_eval_ground_truth_template.md` §2–§6.

| Field | Engine correct vs final labels (n = 20) | 95% interval | Severity |
|---|---|---|---|
| behavior | 17 | 64–95% | LOW |
| in_app_pain | 10 | 30–70% | HIGH |
| unmet_need | 9 | 26–66% | HIGH |
| tenure | 20 | 84–100% | LOW (but only 1 record in the sample states a tenure) |
| Theme (opportunity matched) | 10 | 30–70% | HIGH |

Against the owner's step-1 labels, before adjudication, agreement was 7, 3, 3, 17 and 4. That gap is mostly labelling-rule differences (thread context, missed instalments), not engine errors.

**Findings:**
- **HIGH: pain and need are under-tagged.** In 5 of 10 pain errors and 6 of 11 need errors the engine said `unclear` (or `none`) although the text states the problem or need. Opportunity matching uses these tags, so those records drop out of every opportunity.
- **HIGH: theme errors run in both directions.** Flexible SIP misses `7082789b` and `e64dc6f5` and counts `278362ef`, an AutoPay setup failure tagged `sip_management` that the mandate hold-out rule does not catch. Mandate reliability misses `61403f24` and `278362ef` and counts 3 records whose final theme is fees, support or app reliability.
- **MEDIUM: 4 of 20 records were judged not relevant** to SIP behaviour by the owner, yet they are in the approved Golden Dataset.

**Limits:** n = 20; the final labels were not independent of AI judgement; known problem records were excluded from the sample; no figure here generalises to the 300 rows or to the opportunity counts. Nothing in the dataset was changed.

## 10. Tag corrections applied (D-3, 2026-10-28)

The project owner accepted 25 of the 26 proposed corrections. #23 (`b302ef12`, tenure) was left to Claude Code and set to `unclear` rather than `over_three_years`. The changes were written to `data/review/golden_sample_300.xlsx` with old → new values in each reviewer note, then promoted with `python -m pipeline.export golden` and `python -m research.build`. The public export changed in exactly 26 field values; record IDs and row count (300) are unchanged.

| Opportunity | n before | n after | Priority before | Priority after |
|---|---|---|---|---|
| flexible_sip | 39 (4 held out) | 38 (0 held out) | 58.0 | 56.0 |
| beginner_guidance | 16 | 11 | 22.0 | 12.0 |
| redemption_speed | 27 | 28 | 16.5 | 17.5 |
| responsive_support | 15 | 14 | 10.0 | 9.0 |
| all others | — | — | — | — (unchanged) |

New-investor tenure tags: 10 → 5. Retrieval probe (no model): "returns in the first year" 32 → 26 strong matches; "first-time investors discontinue after 12 months" 1 → 0. Other probe questions kept the same counts. All 165 tests pass.

The 20 labelled records (§9) were not touched by these corrections; they were excluded from the D-3 list.

## 11. Labelled-set corrections, D-9 checks and D-8 tagging (2026-10-28)

**Corrections from the labelled set (owner decision).** The 20-record final labels were applied to the Golden Dataset: 19 changes on 11 records. The other 5 confirmed errors were on records now rejected. The 4 records judged not relevant (`020df9f9`, `d2ff3587`, `009c1dbe`, `d3a3a2f7`) were rejected, leaving 296 public rows.

| Opportunity | n before | n after | Priority before | Priority after |
|---|---|---|---|---|
| mandate_reliability | 66 | 68 | 107.0 | 109.0 |
| flexible_sip | 38 | 40 | 56.0 | 58.0 |
| redemption_speed | 28 | 26 | 17.5 | 16.0 |
| responsive_support | 14 | 15 | 9.0 | 10.0 |
| returns_clarity | 7 | 8 | 8.0 | 9.0 |
| app_reliability | 27 | 27 | 19.0 | 19.5 |

**D-9: two answer checks (code, no model calls).** Tests: `test_ec21_investor_groups_need_a_basis_in_question_or_records`, `test_ec22_frequency_words_are_flagged_not_removed`. 167 tests pass.
- **Investor groups:** a point or summary naming a group (new or first-time, salaried, students, young, older, women, experienced…) is removed unless the question or its cited records mention that group.
- **Frequency words:** "mainly", "often", "common" and similar are flagged in the first limitation note; the text is kept.

Replaying the 4 saved answers from §8 offline (no model call):
- Flagged: Q1 summary ("mainly"), Q2 point 1 ("often"), Q5 summary ("often") and Q5 point 1 ("common").
- Removed: none. Q5's "New investors often struggle…" passed the group check because 2 of its 12 records are from self-described beginners ("I am a beginner", "I'm a novice investor"). The check catches groups with no basis at all; it cannot tell "two records" from "investors in general", which is what the frequency flag is for.

**D-8: new-investor candidates tagged (Groq, approved).** 123 cleaned records contain an explicit new-investor phrase. 5 are already in the Golden Dataset and 8 were already tagged. The remaining 115 were tagged with `openai/gpt-oss-120b` (tag-v4): 6 requests, **34,984 tokens**, 0 failures.

| Tenure tag given (115 newly tagged) | Count |
|---|---|
| new_under_1y | 89 |
| unclear | 21 |
| over_three_years | 4 |
| one_to_three_years | 1 |

108 of the 115 have behaviour `unclear` and 91 have in_app_pain `none`. Most are short app reviews ("I'm new to investing, nice app") that state a tenure but no SIP action or problem. `data/review/new_investor_candidates_20261028.xlsx` holds 116 rows (115 plus 1 tagged earlier), all **pending**. Nothing was added to the Golden Dataset.

## 12. New-investor rows added (D-8 approval, 2026-10-28)

The project owner approved all 116 tagged candidates with one instruction ("Approve"), without editing the workbook. They are recorded as **bulk-approved** (reviewer "project owner (bulk)"), so answers citing them say they were not reviewed row by row.

| | Before | After |
|---|---|---|
| Public Golden rows | 296 | 412 |
| tenure = new_under_1y | 5 | 94 |
| beginner_guidance | 11 (priority 12.0) | **100 (priority 101.0)** |
| mandate_reliability | 68 (109.0) | 72 (113.0) |
| app_reliability | 27 (19.5) | 41 (26.5) |
| responsive_support | 15 (10.0) | 25 (15.0) |
| redemption_speed | 26 (16.0) | 29 (17.5) |
| fee_transparency | 9 (6.5) | 11 (7.5) |

Retrieval probe (no model): the Case C question ("first-time SIP investors … setting up their first SIP") now has **6** strong matches, above the 3-record threshold, so it would be answered instead of abstaining. "Why do first-time investors discontinue SIPs after 12 months?" still has 0. All 167 tests pass.

**HIGH: beginner_guidance is inflated by its matching rule.** 89 of its 100 records match only on the tenure tag; only 7 state a fund-choice need or pain, and none of those 7 is a new row. It now ranks second by a measure of how many writers said they were new, not by evidence that new investors struggle to choose a fund. *Resolved the same day (D-10, option a):* tenure was removed from the rule, so beginner_guidance has 7 records, priority 7.0. The rows also skew the dataset: 116 of 412 were selected by phrase, not sampled.
