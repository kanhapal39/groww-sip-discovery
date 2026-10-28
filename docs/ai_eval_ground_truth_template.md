# AI Evaluation — 20-Record Ground-Truth Set (template)

**Status: NOT STARTED. No record below has been labelled. Every row is PENDING.**

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

Selection command: `PENDING` · Seed: `PENDING` · Labeller: `PENDING` · Labelling date: `PENDING`

## 2. Labelling sheet (filled before comparison)

Allowed values for the labelled columns are in `codebook.yaml` (v3). Use `unclear` when the text gives nothing.

| # | record_id | Source link | Relevant to SIP behaviour? (yes/no) | behavior | in_app_pain | unmet_need | tenure | Problem theme (opportunity id or none) | Stated or inferred? | Labeller notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 2 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 3 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 4 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 5 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 6 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 7 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 8 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 9 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 10 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 11 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 12 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 13 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 14 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 15 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 16 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 17 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 18 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 19 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |
| 20 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | |

## 3. Comparison sheet (filled after labelling)

| # | record_id | Engine behavior | Engine in_app_pain | Engine unmet_need | Engine tenure | Engine opportunities matched | Fields agreeing / 5 | Disagreements | Correction made? (workbook row, date) |
|---|---|---|---|---|---|---|---|---|---|
| 1–20 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

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
