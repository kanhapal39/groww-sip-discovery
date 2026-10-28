# AI Evaluation Documentation

## SIP Discovery Engine | Part 1: Evidence-Based Opportunity Discovery

**Project:** SIP Discovery Engine  
**Use case:** Identifying investor pain points that may affect SIP continuation  
**Evaluation type:** Qualitative evaluation of AI-generated themes and evidence-backed answers  
**Dataset:** Currently included Golden Dataset  
**Evaluation status:** Preliminary evaluation based on observed engine outputs

## 1. Objective

The objective of this evaluation is to assess whether the SIP Discovery Engine can identify meaningful investor problems from its Golden Dataset, support its findings with source evidence, and generate insights that can inform product opportunities.

The evaluation focuses on four questions:

1. Does the engine identify problems relevant to SIP investors?
2. Are the generated insights supported by the underlying records?
3. Does the engine distinguish direct evidence from inferred conclusions?
4. Can the outputs inform product opportunities linked to the North Star metric: 12-month SIP continuation for first-time investors?

The evaluation also examines whether human review is necessary to identify irrelevant matches, incorrect tags, and unsupported business conclusions.

## 2. System Under Evaluation

The SIP Discovery Engine processes investor-related records and organises them into a Golden Dataset for evidence-based analysis.

The observed workflow includes:

1. Records from configured public-source platforms are included in the dataset.
2. Records are tagged with investor behaviours, reported problems, emotions, and unmet needs.
3. Relevant records are retrieved using matching rules.
4. The engine groups evidence into themes and generates product-oriented summaries.
5. The output includes source references, record counts, evidence coverage, and limitations.
6. Human review is used to inspect records and evaluate whether they support the generated findings.

**Evaluation boundary:** This document evaluates the outputs shared from the running engine. It does not independently verify the complete collection pipeline, every record in the dataset, or the implementation of every system component.

## 3. Evaluation Method

The evaluation uses qualitative review of two opportunity outputs and one question-answering output shared from the engine.

### Evaluation dimensions

| **Dimension** | **Evaluation question** |
|---|---|
| Relevance | Does the record substantively relate to the stated problem? |
| Evidence fidelity | Does the displayed quote support the associated claim? |
| Classification quality | Are behaviours, triggers, and unmet needs correctly tagged? |
| Retrieval quality | Does the retrieval method include relevant evidence and exclude weak matches? |
| Traceability | Can a reviewer locate the source record and inspect its context? |
| Uncertainty handling | Does the output identify missing evidence and limitations? |
| Business relevance | Is the proposed connection to SIP continuation supported or only hypothesised? |

No formal accuracy, precision, recall, or agreement percentage is reported because an independently labelled evaluation set and complete item-level scoring results have not been provided.

## 4. Evaluation Case A: SIP Mandate and AutoPay Reliability

### AI-generated finding

The engine identified a problem theme around making SIP mandates and AutoPay reliable and transparent.

| **Output field** | **Observed result** |
|---|---|
| Priority score | 107.0 |
| Relevant records | 66 |
| Share of Golden Dataset | 22% |
| Records marked as reporting a lapse | 62% |
| Evidence strength | Strong |
| Source distribution | Google Play: 51; Reddit: 15 |
| Verbatim quotes | 59 |
| Human-reviewed records | 66 of 66 |

### Evaluation

The theme identifies a plausible problem area: investors may experience failed SIP instalments, mandate problems, or unclear payment status.

The output also identifies potential product interventions, including pre-debit checks, clearer failure explanations, and payment recovery options.

However, the evaluation must distinguish the reported problem from the proposed business impact.

**What the output supports:**

- Payment and mandate problems appear in the retrieved records.
- The theme has multiple supporting records across the two displayed source platforms.
- The output provides a basis for investigating payment reliability.

**What remains unverified:**

- Whether the displayed records are representative of the overall investor population.
- Whether payment failures cause investors to discontinue SIPs for 12 months.
- Whether the proposed interventions would improve instalment success or retention.
- Whether the reported-lapse percentage uses an appropriate and consistently applied denominator.

### Evaluation verdict

**Promising theme; business impact not yet established.**

The theme is suitable for further investigation, but its priority score and evidence-strength label should not be treated as proof of retention impact.

## 5. Evaluation Case B: Flexible SIP Controls

### AI-generated finding

The engine identified an opportunity to let investors pause, skip, or change a SIP instead of cancelling it.

| **Output field** | **Observed result** |
|---|---|
| Priority score | 63.0 |
| Relevant records | 43 |
| Share of Golden Dataset | 14% |
| Records marked as reporting a lapse | 47% |
| Evidence strength | Strong |
| Source distribution | Google Play: 37; Reddit: 6 |
| Verbatim quotes | 35 |
| Human-reviewed records | 43 of 43 |

The matching rule included records tagged with flexible-SIP unmet needs or SIP-management pain.

### Evidence reviewed

The displayed records contain examples such as:

“I want to pause my investment and suddenly app doesn't have sip pause options”

This directly supports a complaint about missing pause functionality.

Another record states:

“Auto-pay for mutual fund sip not working. 2. Cannot edit mutual fund sip amount and date”

This supports reported difficulty with AutoPay and changing SIP details, although it combines more than one problem.

A further record states:

“cancelling SIPs is really hard on this app”

This supports a complaint about cancellation friction, but does not establish that the investor would have continued investing if a pause option were available.

### Evaluation findings

**Strengths**

- The output identifies a plausible product usability problem.
- Several displayed quotes directly describe difficulty with SIP controls.
- The engine provides source references and item-level tags for further review.
- The proposed intervention can be expressed as a testable product hypothesis.

**Weaknesses identified during review**

- Some records concern payment reliability rather than flexible SIP management.
- Difficulty cancelling does not necessarily mean the investor wants to pause and continue later.
- A desire to pause due to a life event does not establish that an app's missing functionality caused cancellation.
- Some displayed quotes lack sufficient context to determine the user's underlying motivation.
- Broad tag-based matching can include records that are only loosely related to the opportunity.

### Evaluation verdict

**Relevant opportunity, with evidence-quality and causal-inference limitations.**

The displayed evidence supports the existence of complaints about SIP controls. It does not yet establish that adding pause, skip, or amount-change options will improve 12-month SIP continuation.

## 6. Evaluation Case C: Question Answering on First-Time SIP Setup

### Question asked

What problems do first-time SIP investors experience when setting up their first SIP?

### AI-generated answer

The engine identified three potential problem areas:

1. Uncertainty about selecting suitable mutual funds.
2. Payment-mandate and UPI AutoPay failures.
3. Limited flexibility to pause or edit SIPs after setup.

The displayed output reported nine retrieved records: three from Reddit and six from Google Play.

### Evaluation findings

The answer was structured clearly and included evidence references and limitations. However, the retrieved records did not consistently support all three conclusions.

| **Evidence issue** | **Example** | **Evaluation** |
|---|---|---|
| Weak relevance | A record simply says “You can start a SIP.” | Does not establish a setup problem. |
| Incomplete context | A record says the investor wishes they could start SIPs in international index funds. | Does not independently establish difficulty selecting funds during initial setup. |
| Potentially incorrect classification | A record about a failed AutoPay mandate is tagged as a flexible-SIP need. | Payment reliability and flexible controls should be distinguished. |
| Insufficient support | A record discusses cancelling after a reported profit. | Does not establish that missing flexibility caused cancellation. |
| Uncertain investor segment | Several records lack reliable evidence that the author is a first-time investor. | Findings cannot automatically be attributed to first-time investors. |

### Evaluation verdict

**Partially useful answer; retrieval relevance and segment attribution require improvement.**

The answer identifies plausible issues, but the small retrieved sample and weakly relevant records limit the reliability of its conclusions about first-time SIP setup.

The result should be treated as exploratory rather than as a validated description of first-time investors' experiences.

## 7. Human Review and Correction Requirements

Human review is essential because a record can match a retrieval rule without substantively supporting the generated conclusion.

The following cases illustrate why individual review is necessary.

### Case 1: Payment failure classified as a flexibility problem

**Observed record:** “not able to set up auto pay”

**Potential classification issue:** The record directly describes an AutoPay setup problem, but it does not establish a need to pause, skip, or modify a SIP.

**Required human action:** Review the full record and classify it under payment or mandate reliability unless additional context supports the flexible-controls theme.

### Case 2: Cancellation treated as evidence for a pause alternative

**Observed record:** “cancelling SIPs is really hard on this app”

**Potential inference error:** The complaint establishes cancellation friction, but not that the investor would prefer to pause rather than cancel.

**Required human action:** Retain it as evidence of cancellation friction. Do not treat it as direct evidence that a pause option would prevent cancellation.

### Case 3: A reported investment outcome interpreted as a flexibility problem

**Observed record:** “I started sip and then cancel it with profit of 9 percent”

**Potential inference error:** The record mentions cancellation, but does not establish why the investor cancelled or whether missing SIP controls were involved.

**Required human action:** Exclude it from direct evidence for the flexible-controls opportunity unless the full context supports that connection.

**Reporting note:** These are illustrative evaluation cases based on the displayed records. They should not be reported as completed AI corrections unless a reviewer actually changed the labels or removed the records and that action was recorded.

## 8. Relationship to the North Star Metric

### North Star

**12-month SIP continuation rate for first-time investors.**

The evaluation identifies two opportunities that could plausibly relate to this metric.

| **Opportunity** | **Potential mechanism** | **Current evidence status** |
|---|---|---|
| Improve mandate and AutoPay reliability | Reduce failed instalments and make payment recovery easier. | Reported payment problems are visible; retention impact is unproven. |
| Offer flexible SIP controls | Allow investors to adjust contributions or pause temporarily instead of cancelling. | Reported control problems are visible; effect on cancellation and retention is unproven. |

These opportunities should not be prioritised solely by their AI-generated scores.

A more reliable prioritisation process would consider:

- Relevance and quality of the underlying evidence.
- Strength of the connection to the North Star.
- Number of unique, substantively relevant records.
- Product analytics available to validate the problem.
- Implementation effort and potential unintended consequences.

## 9. Recommended Next Evaluation

The next evaluation should test whether the flexible-controls theme is genuinely connected to cancellation and continuation.

The engine should distinguish:

1. Explicit statements that an investor cancelled because a pause or modification option was unavailable.
2. Statements about wanting to pause or reduce contributions due to temporary financial constraints.
3. Complaints about editing SIP amounts or dates.
4. Cancellation and AutoPay problems without evidence of a flexible-controls need.

For each category, the reviewer should verify the source context, count unique relevant records, and distinguish explicitly stated behaviour from inferred motivation.

### Suggested product analytics

If available, investigate:

- SIP cancellation rate.
- Cancellation attempts preceded by pause or modification attempts.
- Pause-to-resume rate.
- Successful subsequent instalments after a pause or amount change.
- 90-day continuation among comparable investor cohorts.
- 12-month continuation among first-time investor cohorts.

These measures can help test whether flexible controls are associated with continued investing. A controlled experiment would be needed to estimate the intervention's causal effect.

## 10. Limitations

This evaluation has several limitations:

- It reviews selected outputs rather than the entire Golden Dataset.
- The displayed record counts do not establish population-level prevalence.
- Public reviews and discussions may overrepresent people experiencing problems.
- Some records have incomplete quotes or uncertain context.
- Investor tenure is missing or uncertain for many records.
- Tag-based matching may retrieve records that do not substantively support a theme.
- The reported priority scores have not been independently validated against business outcomes.
- No independently labelled test set, formal model-agreement score, or measured intervention outcome has been supplied.
- This document does not independently verify source permissions, retention compliance, or whether all included source material is approved for the intended processing.

## 11. Conclusion

The preliminary evaluation shows that the SIP Discovery Engine can surface plausible product problems and organise them into actionable themes. Its outputs provide a useful starting point for product discovery.

However, the evaluation also reveals risks from weak retrieval matches, uncertain classifications, and unsupported links between reported problems and business outcomes.

The main improvement needed is to ensure that **every record counted as evidence substantively supports the specific problem being investigated**.

For the next iteration, the evaluation should use an independently labelled set of 20 records, compare the engine's classifications with human judgements, record disagreements and corrections, and report measured results rather than assumed accuracy.

Until that evaluation is completed, the identified opportunities should be treated as hypotheses for further investigation, not as proven drivers of 12-month SIP continuation.

---

## 12. Addendum: Implementation Audit (2026-10-28)

*Added after the original document, which is the project owner's Word file converted to Markdown. Sections 1–11 above are unchanged and describe the engine as observed before this audit. Details are in `docs/ai_eval_implementation_audit.md` and `docs/ai_eval_test_report.md`.*

### 12.1 What was verified, and how

- The figures in Cases A and B were reproduced exactly from `data/export/golden_public.jsonl` by running the engine's own deterministic code, with no model call:
  - Mandate/AutoPay: 66 records, 22%, 62% lapse (41 ÷ 66), priority 107.0, Google Play 51 / Reddit 15, 59 verbatim quotes.
  - Flexible SIP: 43 records, 47% lapse, priority 63.0, Google Play 37 / Reddit 6.
- Case C's retrieval was reproduced: 9 records, 6 from Google Play and 3 from Reddit.
  - 6 of the 9 matched only on the question words "time", "experience", "setting" and "up". "Up" also matched "upi" and "upstox".
  - The other 3 matched because "first" was mapped to the `start_sip` tag.
  - This explains the weak relevance reported in the Case C table.
- The records cited in §7 carry the tags described there. "not able to set up auto pay" is tagged `in_app_pain=mandate_autopay` and `unmet_need=flexible_sip`.

### 12.2 Code changes and their effect (new results, not historical)

| Finding in this document | Change | Effect on current data | Test |
|---|---|---|---|
| §7 Case 1: payment failure counted as flexibility | Flexible-SIP opportunity holds out records tagged `in_app_pain=mandate_autopay` and lists them for review | Flexible SIP: **43 → 39 records, priority 63.0 → 58.0**. The tags themselves were not changed | `test_ec2_*` |
| §7 Case 2 and §9: cancellation vs pause | Keyword breakdown shown on the opportunity | Of 39 records: 10 mention pausing/skipping, 10 editing amount or date, 10 only cancelling/stopping, 9 none of these | `test_ec3_*` |
| §7 Case 3: cancel-with-profit | Not excluded: the record is tagged `in_app_pain=sip_management` | Still counted in Flexible SIP, in the "cancelling or stopping only" group. Needs a reviewer's tag correction | — |
| Case C: weak relevance and first-time attribution | Generic words ignored; short words match whole words only; ≥ 2 matched words for text-only matches; "first-time"/"beginner" questions use only records tagged as new investors | The Case C question now finds 2 records and **abstains**. No model was run, so there is no new answer to compare | `test_ec1_*`, `test_ec5_*` |
| §8: link to 12-month continuation | Answer points or summaries that predict a product change's effect are removed and listed as removed | Not run against the live model | `test_ec18_*` |

### 12.3 Claims in this document that need careful wording

| Where | Current wording | Suggested accurate wording |
|---|---|---|
| Case A and B tables | "Human-reviewed records: 66 of 66" / "43 of 43" | "Approved by the project owner: 66 of 66. No tag corrections were recorded (evidence log §7.2); these are not independent labels." |
| Case A and B tables | "Evidence strength: Strong" | "Evidence strength: Strong by the engine's fixed rule (≥ 30 records, ≥ 2 platforms, ≥ 10 exact quotes); not a measure of relevance or impact." |
| Case B table | 43 records, priority 63.0 | Keep as the historical observation. Add: "39 records and priority 58.0 after mandate/AutoPay records were held out (2026-10-28); 38 records and priority 56.0 after the D-3 tag corrections the same day." |
| §2, item 6 | "Human review is used to inspect records…" | Accurate as a process. No correction from that review has been recorded yet |

### 12.4 Still not done

- **The 20-record independently labelled set (§11) does not exist.** A template with every row PENDING is in `docs/ai_eval_ground_truth_template.md`. No accuracy, precision, recall or agreement figure has been computed, and none should be quoted. *(Superseded later the same day for classification; see §12.5.)*
- No answer from the live model was generated or re-evaluated during this audit. The answer prompt changed to `answer-v2` and has not been run.
- The three records in §7 remain in the Golden Dataset with their original tags. Correcting them is a reviewer's decision.
- The opportunities in §8 remain hypotheses; nothing measured their effect on 12-month SIP continuation.

### 12.5 Labelled 20-record set (2026-10-28)

The project owner labelled 20 random records with the engine's tags hidden, then adjudicated the 66 field values where they and the engine differed. They accepted Claude Code's suggested value on every one, after reviewing each row. Against the final labels the engine was correct on:

| Field | Correct (n = 20) |
|---|---|
| behavior | 17 |
| in_app_pain | 10 |
| unmet_need | 9 |
| tenure | 20 |
| Opportunity theme | 10 |

The main error is under-tagging: pain and need are often `unclear` when the text states them, so those records match no opportunity. The set is small, excludes the known problem records, and its final labels were not independent of AI judgement. The figures describe these 20 records only. Retrieval and answer quality were not part of this check. Details: `docs/ai_eval_ground_truth_template.md` §6 and `docs/ai_eval_test_report.md` §9.

### 12.6 Tag corrections for §7 (2026-10-28)

The records in §7 were corrected on the project owner's decision (D-3), along with other known mis-tagged records: 26 changes on 16 records in all. The AutoPay setup failure now has `unmet_need=easy_mandate_control`. The cancel-with-profit record now has a deliberate lapse, `in_app_pain=redemption_withdrawal` and no support trigger. Seven unsupported new-investor tags were removed and two stated ones added (10 → 5). Flexible SIP is now 38 records with priority 56.0. Details: `docs/ai_eval_test_report.md` §10.

### 12.7 Further corrections and checks (2026-10-28)

On the project owner's decisions the same day:
- The adjudicated labels for the 20-record set were applied (19 changes on 11 records), and the 4 records judged not relevant were removed, leaving 296 rows. Mandate reliability is now 68 records and Flexible SIP 40.
- Answers now drop statements about investor groups that neither the question nor the cited records mention, and flag frequency words such as "mainly" and "often".
- 115 more records stating that the writer is a new investor were tagged and await review. They are not in the Golden Dataset.

Details: `docs/ai_eval_test_report.md` §11.
