# AI Evaluation — 20-Record Ground-Truth Set

**Status (2026-10-28): classification labels COMPLETE and adjudicated (§2, §3, §6). Retrieval and answer checks (§4) NOT STARTED.**

*History: this file was created as an empty template on 2026-10-28 with every row PENDING. The labelling rules in §1 are unchanged.*

The AI Evaluation document (§11) calls for "an independently labelled set of 20 records" to compare against the engine. No such set exists in the repository or in `data/`. This template defines how to build one so the results can support real metrics. It contains no labels, and none may be filled in by an AI.

## 1. Rules for a valid set

1. **Independent labelling.** The labeller sees only the record text, source link and thread context, never the engine's tags, `reason` or answers. Hide those columns before labelling.
2. **Labeller.** Record a person's name and the date. Labels by Claude Code or any other model are not ground truth.
3. **Selection.** Draw 20 random records, not hand-picked ones:
   - Draw from `data/export/golden_public.jsonl` with a fixed, recorded seed.
   - Record the selection command and seed below before anyone labels.
   - Evaluate the records already cited as failures in the AI Evaluation document (record ID prefixes `a140a1f6`, `e45241db`, `a7c2a38b`, `fafe30aa`, `5a343cb7`) **separately**, as known-failure cases. Including them in the 20 would bias the metrics.
4. **Compare after labelling.** Fill the "Engine output" columns only after every label is final. Then compute agreement per field, never one combined accuracy.
5. **Record disagreements and corrections.** If the comparison leads to a tag correction, make it in the review workbook and promote it with `python -m pipeline.export golden`. Log it in `docs/evidence_log_notes.md` (AGENTS.md rule 7).

**Sample drawn 2026-10-28:**

```
python -m research.ground_truth sample --size 20 --seed 20261028 --exclude a140a1f6,0b1dfb99,c43684df,14d55029,a7c2a38b,e45241db,fafe30aa,af1bc5ab,5a343cb7,602cf3cd,3e6b0142,3b8e232b,67dec2e7,0b020206,b302ef12,55c5855a,266e1942,4f94b6b3,226d8804,a08aa8f0,27ca76cd,a2f5f709
```

- **Pool:** the 300 rows in `data/export/golden_public.jsonl`.
- **Excluded:** 22 records. These are the known-failure records plus every record in the tag-correction proposal shown to the project owner on 2026-10-28; the owner saw their AI tags, so labelling them would not be independent.
- **Output:** `data/review/ground_truth_20.xlsx` (gitignored). Its `about` sheet repeats the seed and command. `python -m research.ground_truth compare` computes the agreement figures in §5.

Labeller: the project owner · Labelling date: 2026-10-28

**How the labels were made (two steps):**

1. **Independent labels.** The project owner labelled all 20 records in `data/review/ground_truth_20.xlsx`, with the engine's tags hidden (rule 1).
2. **Adjudication.** The owner's labels were compared with the engine's (`python -m research.ground_truth compare`). They differed on 66 field values across 19 records. For each one, `data/review/ground_truth_20_adjudication.xlsx` showed the record text, both values with their codebook definitions, and a suggestion with a reason written by Claude Code. The owner chose the final value for every row. All 66 choices matched Claude Code's suggestion (32 the engine's tag, 22 the owner's label, 12 a third value). The owner states they reviewed each row and agree (recorded 2026-10-28).

**What this means for independence.** Step 1 is independent of the engine. The final labels in step 2 were chosen by the owner, but the owner saw the engine's tags and accepted an AI's suggestion on every disputed value. They are therefore **not fully independent of AI judgement** (see rule 2). Both sets of figures are reported in §6.

The final labels are in `data/review/ground_truth_20_final.csv` (gitignored), with a `<field>_source` column for each field: `agreed` (owner and engine matched), `AI`, `mine` (the owner's first label) or `other`.

## 2. Final labels

The last column says where each final value came from: `agreed` (owner and engine matched in step 1), `labeller` (the owner's first label), `AI` (the engine's tag) or `other` (a third value).

Allowed values for the labelled columns are in `codebook.yaml` (v3). Use `unclear` when the text gives nothing.

| # | record_id | Source | Relevant? | behavior | in_app_pain | unmet_need | tenure | Theme | Where each final value came from (behavior / pain / need / tenure / theme) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `195c9e77` | reddit | yes | `pause_sip` | `mandate_autopay` | `unclear` | `unclear` | `fee_transparency` | AI / agreed / labeller / agreed / labeller |
| 2 | `61403f24` | play_store | yes | `unclear` | `mandate_autopay` | `easy_mandate_control` | `unclear` | `mandate_reliability` | AI / labeller / labeller / AI / other |
| 3 | `13c617d3` | reddit | yes | `continue_sip` | `unclear` | `unclear` | `unclear` | `none` | other / AI / AI / agreed / AI |
| 4 | `e64dc6f5` | play_store | yes | `unclear` | `sip_management` | `reliable_app` | `unclear` | `flexible_sip` | AI / labeller / other / agreed / labeller |
| 5 | `fa76a587` | play_store | yes | `unclear` | `portfolio_display` | `clear_returns_view` | `unclear` | `returns_clarity` | AI / other / labeller / agreed / labeller |
| 6 | `404cb625` | play_store | yes | `stop_sip` | `sip_management` | `responsive_support` | `unclear` | `responsive_support` | agreed / labeller / agreed / agreed / agreed |
| 7 | `7082789b` | play_store | yes | `unclear` | `sip_management` | `flexible_sip` | `unclear` | `flexible_sip` | AI / labeller / labeller / agreed / labeller |
| 8 | `020df9f9` | play_store | no | `other` | `portfolio_display` | `reliable_app` | `unclear` | `portfolio_tracking` | agreed / other / labeller / agreed / other |
| 9 | `d2ff3587` | play_store | no | `other` | `redemption_withdrawal` | `fast_redemption` | `unclear` | `app_reliability` | agreed / other / AI / agreed / agreed |
| 10 | `6652a87d` | play_store | yes | `continue_sip` | `sip_management` | `other` | `unclear` | `flexible_sip` | other / AI / other / AI / AI |
| 11 | `61962818` | reddit | yes | `continue_sip` | `none` | `unclear` | `one_to_three_years` | `none` | AI / AI / agreed / agreed / AI |
| 12 | `111e7d0b` | reddit | yes | `continue_sip` | `none` | `unclear` | `unclear` | `none` | agreed / AI / AI / agreed / AI |
| 13 | `009c1dbe` | play_store | no | `unclear` | `unclear` | `unclear` | `unclear` | `none` | agreed / agreed / agreed / agreed / agreed |
| 14 | `be63c39c` | reddit | yes | `unclear` | `unclear` | `unclear` | `unclear` | `none` | AI / agreed / AI / AI / agreed |
| 15 | `a0ad7656` | reddit | yes | `unclear` | `unclear` | `unclear` | `unclear` | `none` | AI / AI / AI / agreed / AI |
| 16 | `5d5fe1e4` | play_store | yes | `pause_sip` | `mandate_autopay` | `responsive_support` | `unclear` | `responsive_support` | AI / AI / labeller / agreed / labeller |
| 17 | `61795856` | play_store | yes | `stop_sip` | `app_bug` | `reliable_app` | `unclear` | `app_reliability` | other / labeller / labeller / agreed / labeller |
| 18 | `d3a3a2f7` | play_store | no | `unclear` | `portfolio_display` | `external_tracking` | `unclear` | `portfolio_tracking` | agreed / labeller / labeller / agreed / labeller |
| 19 | `278362ef` | play_store | yes | `continue_sip` | `mandate_autopay` | `easy_mandate_control` | `unclear` | `mandate_reliability` | agreed / labeller / other / agreed / other |
| 20 | `5ff1c271` | reddit | yes | `unclear` | `unclear` | `unclear` | `unclear` | `none` | AI / AI / AI / agreed / AI |

## 3. Engine output compared with the final labels

*Updated 2026-10-28:* on the owner's decision, the confirmed errors below were corrected in the Golden Dataset (19 changes on 11 records), and the 4 records judged not relevant were rejected (evidence log §8.6). The table shows the engine's tags as they were when scored. These 20 records can no longer be used to re-test the original tags.

| # | record_id | Engine behavior | Engine in_app_pain | Engine unmet_need | Engine tenure | Engine opportunities matched | Fields agreeing / 5 | Engine wrong on | Correction made? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `195c9e77` | `pause_sip` | `mandate_autopay` | `easy_mandate_control` | `unclear` | `mandate_reliability` | 3 | unmet_need, theme | Yes (2026-10-28) |
| 2 | `61403f24` | `unclear` | `unclear` | `unclear` | `unclear` | none | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 3 | `13c617d3` | `unclear` | `unclear` | `unclear` | `unclear` | none | 4 | behavior | Yes (2026-10-28) |
| 4 | `e64dc6f5` | `unclear` | `unclear` | `unclear` | `unclear` | none | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 5 | `fa76a587` | `unclear` | `none` | `unclear` | `unclear` | none | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 6 | `404cb625` | `stop_sip` | `redemption_withdrawal` | `responsive_support` | `unclear` | `redemption_speed`, `responsive_support` | 4 | in_app_pain | Yes (2026-10-28) |
| 7 | `7082789b` | `unclear` | `unclear` | `unclear` | `unclear` | none | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 8 | `020df9f9` | `other` | `unclear` | `unclear` | `unclear` | none | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 9 | `d2ff3587` | `other` | `app_bug` | `fast_redemption` | `unclear` | `redemption_speed`, `app_reliability` | 4 | in_app_pain | Yes (2026-10-28) |
| 10 | `6652a87d` | `stop_sip` | `sip_management` | `flexible_sip` | `unclear` | `flexible_sip` | 3 | behavior, unmet_need | Yes (2026-10-28) |
| 11 | `61962818` | `continue_sip` | `none` | `unclear` | `one_to_three_years` | none | 5 | — | — |
| 12 | `111e7d0b` | `continue_sip` | `none` | `unclear` | `unclear` | none | 5 | — | — |
| 13 | `009c1dbe` | `unclear` | `unclear` | `unclear` | `unclear` | none | 5 | — | — |
| 14 | `be63c39c` | `unclear` | `unclear` | `unclear` | `unclear` | none | 5 | — | — |
| 15 | `a0ad7656` | `unclear` | `unclear` | `unclear` | `unclear` | none | 5 | — | — |
| 16 | `5d5fe1e4` | `pause_sip` | `mandate_autopay` | `easy_mandate_control` | `unclear` | `mandate_reliability` | 3 | unmet_need, theme | Yes (2026-10-28) |
| 17 | `61795856` | `pause_sip` | `mandate_autopay` | `unclear` | `unclear` | `mandate_reliability` | 1 | behavior, in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 18 | `d3a3a2f7` | `unclear` | `app_bug` | `reliable_app` | `unclear` | `app_reliability` | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 19 | `278362ef` | `continue_sip` | `sip_management` | `flexible_sip` | `unclear` | `flexible_sip` | 2 | in_app_pain, unmet_need, theme | Yes (2026-10-28) |
| 20 | `5ff1c271` | `unclear` | `unclear` | `unclear` | `unclear` | none | 5 | — | — |

## 4. Retrieval and answer checks (filled after labelling)

Write 5 questions before looking at engine output. For each, the labeller marks which of the 20 records are relevant. Then run the engine and record the result.

| Question | Records labelled relevant (ids) | Records the engine used as evidence | Relevant and retrieved | Evidence not relevant | Status (answered/insufficient) | Points removed by validation | Unsupported claims found by reviewer | Citation errors |
|---|---|---|---|---|---|---|---|---|
| PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Answering a question calls the Groq model, which uses quota. Get approval first and record it in `docs/evidence_log_notes.md` (AGENTS.md rule 6).

## 5. Metrics to report (only once §2–§4 are complete)

Report each separately, with its denominator:

- **Classification agreement per field:** matching labels ÷ 20, for each of behavior, in_app_pain, unmet_need and tenure.
- **Theme assignment agreement:** matching opportunity ÷ 20.
- **Retrieval precision per question:** relevant and retrieved ÷ retrieved.
- **Retrieval recall per question:** relevant and retrieved ÷ labelled relevant within the 20. With 20 records this is indicative only.
- **Answer support:** points the reviewer judges supported ÷ points shown.
- **Citation errors:** count.
- **Abstention correctness:** questions where the status matches the reviewer's judgement of sufficiency ÷ questions.

With n = 20, report counts, not just percentages, and do not generalise beyond these records.

## 6. Results (2026-10-28)

All 20 records were scored; there is one value per field per record. Counts are out of 20. The range in brackets is a 95% Wilson interval, given to show how little 20 records can establish.

### 6.1 Classification agreement per field

| Field | Engine vs owner's independent labels (step 1) | Engine vs final adjudicated labels (step 2) | Owner's step-1 labels vs final |
|---|---|---|---|
| behavior | 7 | **17** (64–95%) | 7 |
| in_app_pain | 3 | **10** (30–70%) | 10 |
| unmet_need | 3 | **9** (26–66%) | 11 |
| tenure | 17 | **20** (84–100%) | 17 |
| Theme (opportunity matched) | 4 | **10** (30–70%) | 11 |

Relevance: the owner judged **16 relevant, 4 not relevant** (`020df9f9`, `d2ff3587`, `009c1dbe`, `d3a3a2f7`). All 4 are in the Golden Dataset, so the relevance filter and review passed them. The engine has no per-record relevance label to compare.

**Why step 1 and step 2 differ so much.** Most step-1 disagreements were differences in labelling rules, not engine errors. The owner labelled some Reddit replies from the thread question, and labelled missed instalments as `continue_sip`; the codebook says to tag the record's own words and to tag an unchosen missed instalment as `pause_sip`. Adjudication applied the codebook rules.

### 6.2 What kind of errors the engine makes (against the final labels)

- **behavior (3 wrong):** `13c617d3` (unclear; the reply reports paying SIPs manually), `6652a87d` (stop_sip; the text says the SIP did not stop), `61795856` (pause_sip; the writer says they stopped).
- **in_app_pain (10 wrong):** 5 are `unclear` or `none` where the text names a problem (`61403f24`, `e64dc6f5`, `fa76a587`, `7082789b`, `020df9f9`). 5 name the wrong problem (`404cb625`, `d2ff3587`, `61795856`, `d3a3a2f7`, `278362ef`).
- **unmet_need (11 wrong):** 6 are `unclear` where a need is stated (`61403f24`, `e64dc6f5`, `fa76a587`, `7082789b`, `020df9f9`, `61795856`). 4 name the wrong need (`6652a87d`, `5d5fe1e4`, `d3a3a2f7`, `278362ef`). 1 states a need the text does not (`195c9e77`).
- **Theme (10 wrong):** these follow from the tag errors, because opportunities are matched on tags. 5 records with a real problem match no opportunity; 5 match the wrong one.

The main pattern: **the engine under-tags.** It often returns `unclear` for pain and need when the text states them.

### 6.3 Effect on the opportunity counts (these 20 records only)

- **Flexible SIP:** `7082789b` ("modify and pause options disabled") and `e64dc6f5` (resume always fails) belong to it but are not counted. `278362ef` (an AutoPay setup failure) is counted but does not belong. `278362ef` is tagged `in_app_pain=sip_management`, so the mandate hold-out rule (R-02) does not catch it.
- **Mandate reliability:** `61403f24` and `278362ef` belong but are not counted. `195c9e77`, `5d5fe1e4` and `61795856` are counted; the final labels place them under fee transparency, support and app reliability.

This shows that errors exist in both directions. It does not estimate how many of the full counts are wrong: 20 records are too few, and the opportunity counts were not re-computed.

### 6.4 Not done

- **§4 retrieval and answer checks:** not started. They need 5 questions written before running the engine, plus approval for the model calls.
- **Corrections:** *updated 2026-10-28:* applied on the owner's decision (19 changes on 11 records; 4 records rejected). Opportunities are still matched by rules, so 6 records match an extra or different opportunity from the adjudicated theme; e.g. `195c9e77` still matches mandate_reliability (fee_transparency adjudicated) and `404cb625` (wants to stop a SIP) now matches flexible_sip (see D-4).
- **Generalising:** with n = 20 and a sample that excluded 22 known problem records, these figures describe these 20 records only.
