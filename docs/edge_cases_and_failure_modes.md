# SIP Discovery Engine: AI Failure Modes and Edge-Case Evaluation

## 1. Objective

The objective of this evaluation is to identify situations where the SIP Discovery Engine may produce incorrect, misleading, incomplete, or unsupported insights.

The engine should retrieve relevant investor evidence, classify it accurately, distinguish direct evidence from inference, and generate conclusions that are traceable to the Golden Dataset.

The following edge cases describe potential failure modes to test. They are **test scenarios, not claims that every failure has already occurred**. Where an example comes from the observed engine output, it is identified accordingly.

## 2. Edge Cases and Potential Failure Modes

### Edge Case 1: Keyword Match Without Actual Relevance

**Scenario:** A record contains the word "SIP" but does not describe the problem being investigated.

**Example from observed output:**

"You can start a SIP"

**Expected behaviour:** The engine should not treat this as evidence that investors struggle with flexible SIP controls.

**Failure condition:** The record is retrieved and counted as supporting evidence despite not describing the problem.

**Evaluation:** Check whether the record substantively supports the question, rather than merely sharing keywords.

### Edge Case 2: Incorrect Classification of Payment Problems

**Scenario:** A user reports that AutoPay is not working, but the engine classifies the record as evidence of missing pause or modification functionality.

**Example from observed output:**

"not able to set up auto pay"

**Expected behaviour:** Classify this primarily as a payment or mandate setup problem unless additional context establishes a separate need for flexible controls.

**Failure condition:** The engine conflates payment reliability with SIP flexibility.

**Evaluation:** Compare the human-assigned problem category with the AI-generated category.

### Edge Case 3: Confusing Cancellation With a Desire to Pause

**Scenario:** A user reports difficulty cancelling an SIP.

**Example from observed output:**

"cancelling SIPs is really hard on this app"

**Expected behaviour:** Recognise cancellation friction without assuming the investor would prefer to pause or modify the SIP.

**Failure condition:** The engine concludes that a pause option could have prevented cancellation without supporting evidence.

**Evaluation:** Check whether the output separates the observed complaint from the proposed product hypothesis.

### Edge Case 4: Inferring Motivation From Incomplete Evidence

**Scenario:** A record reports that an investor cancelled an SIP but does not explain why.

**Example from observed output:**

"I started sip and then cancel it with profit of 9 percent"

**Expected behaviour:** Report that cancellation occurred, while marking the underlying motivation as unknown.

**Failure condition:** The engine attributes cancellation to missing flexibility, financial stress, market conditions, or another cause without evidence.

**Evaluation:** Check whether the answer invents a reason not present in the source.

### Edge Case 5: Incorrect Investor Tenure Classification

**Scenario:** The engine labels an investor as a first-time investor based on limited or contradictory context.

**Expected behaviour:** Use "first-time investor" or "new investor" only when supported by explicit evidence and a defined labelling rule.

**Failure condition:** The engine treats all investors discussing SIP setup as first-time investors.

**Evaluation:** Compare tenure labels with the full source context. Record unknown tenure as unknown rather than guessing.

### Edge Case 6: Unsupported Causal Claims

**Scenario:** Several records mention missing SIP controls, and the engine concludes that these problems cause long-term SIP discontinuation.

**Expected behaviour:** Distinguish among:

- A directly reported problem.
- A user's explicitly stated reason for cancelling.
- A hypothesised effect on retention.
- A measured business outcome.

**Failure condition:** The engine presents a plausible relationship as a proven causal effect.

**Evaluation:** Verify whether the source explicitly states the relationship or whether it requires product analytics or experimentation.

### Edge Case 7: Duplicate Records Inflate Evidence Counts

**Scenario:** The same complaint appears multiple times, or duplicate records are imported from repeated collection runs.

**Expected behaviour:** Identify duplicates using stable source identifiers and appropriate deduplication rules.

**Failure condition:** Duplicate complaints inflate relevant-record counts, theme scores, or perceived evidence strength.

**Evaluation:** Check for duplicate source URLs, source IDs, and substantially identical text. Report unique records separately from raw occurrences.

### Edge Case 8: Misleading Evidence Percentages

**Scenario:** The engine reports that 47% of records report a lapse.

**Expected behaviour:** Clearly define the numerator, denominator, and rule used to classify a lapse.

**Failure condition:** The output implies that 47% of all SIP investors experience lapses when the percentage describes only a subset of public records.

**Evaluation:** Recalculate the percentage from its underlying records and confirm the denominator. Label it as a dataset statistic, not population prevalence.

### Edge Case 9: Weak Quotes Presented as Strong Evidence

**Scenario:** A retrieved record contains a short or incomplete quote that does not establish the full claim.

**Expected behaviour:** Show sufficient source context and avoid overstating what the quote proves.

**Failure condition:** A fragment is used to support a broader conclusion that is not evident from the original post or review.

**Evaluation:** Open the source and compare the quote with the full text. Record whether the evidence is direct, indirect, or insufficient.

### Edge Case 10: Incorrect or Overly Broad Tag-Based Retrieval

**Scenario:** The engine retrieves records because they contain tags such as `flexible_sip` or `sip_management`, even though their content is unrelated to the specific research question.

**Expected behaviour:** Use tags to support retrieval, then verify substantive relevance before counting the record as evidence.

**Failure condition:** Every record matching a tag is automatically treated as supporting the theme.

**Evaluation:** Sample retrieved records and calculate the proportion that genuinely support the target problem.

### Edge Case 11: Conflicting Evidence Is Ignored

**Scenario:** Some records describe difficulty pausing SIPs, while others show that investors intentionally cancel because their financial goals or investment preferences have changed.

**Expected behaviour:** Present both patterns and explain that not every cancellation is preventable.

**Failure condition:** The engine presents only evidence supporting the proposed intervention.

**Evaluation:** Search for contradictory records and check whether the final insight represents them fairly.

### Edge Case 12: Retrieval Misses Relevant Records

**Scenario:** Investors describe the same problem using different language, such as "reduce monthly contribution", "stop one instalment", "change debit amount", or "temporarily discontinue investment".

**Expected behaviour:** Retrieve semantically relevant records even when they do not use the exact expected tags or keywords.

**Failure condition:** Relevant evidence is missed because the retrieval method relies too heavily on exact tags or wording.

**Evaluation:** Create a human-labelled set of relevant records and measure how many are retrieved by the engine.

### Edge Case 13: Source Context Changes the Meaning

**Scenario:** A short quote appears to describe a missing feature, but the surrounding conversation reveals that the user is discussing a different app, a different investment product, or a hypothetical situation.

**Expected behaviour:** Use surrounding context when needed to determine what the record actually means.

**Failure condition:** The engine treats an isolated phrase as definitive evidence.

**Evaluation:** Inspect the full source and check product, behaviour, and context attribution.

### Edge Case 14: Stale or Outdated Evidence

**Scenario:** An older review reports that a pause option is unavailable, but the app may have introduced that functionality since the review was written.

**Expected behaviour:** Preserve the historical complaint while distinguishing it from the current product experience.

**Failure condition:** The engine presents an old complaint as proof that the feature is still missing.

**Evaluation:** Check source dates and, where relevant, verify current product functionality independently.

### Edge Case 15: Unsupported Product Recommendations

**Scenario:** The engine identifies cancellation friction and immediately recommends adding a pause option to the cancellation flow.

**Expected behaviour:** Present the intervention as a hypothesis and identify the evidence and analytics needed to validate it.

**Failure condition:** The engine presents a recommendation as proven or claims that it will improve retention without experimental evidence.

**Evaluation:** Check whether the recommendation includes a measurable hypothesis, relevant metrics, and validation requirements.

### Edge Case 16: Incorrect Prioritisation

**Scenario:** A theme receives a high priority score because many records match its tags, even though the evidence is weak or the connection to 12-month continuation is uncertain.

**Expected behaviour:** Explain how the priority score is calculated and distinguish evidence volume from business impact.

**Failure condition:** The engine treats the highest score as proof of the highest potential retention impact.

**Evaluation:** Inspect the scoring method, underlying records, and connection to the North Star metric.

### Edge Case 17: Unsupported Personalisation or Segment-Level Conclusions

**Scenario:** A few records from salaried investors aged 25–40 are used to claim that this demographic has the greatest need for flexible SIP controls.

**Expected behaviour:** Describe the characteristics of the observed records without generalising to the wider segment.

**Failure condition:** The engine makes demographic or investor-segment claims without adequate evidence.

**Evaluation:** Check the number of unique records, missing demographic data, and whether the source actually supports the segment classification.

### Edge Case 18: Hallucinated Citations or Evidence

**Scenario:** The generated answer includes a source link, quote, record ID, or statistic that does not exist in the retrieved dataset.

**Expected behaviour:** Every cited record, quote, and statistic must map to an actual source record.

**Failure condition:** A citation is fabricated, a quote is altered while being presented as verbatim, or a statistic cannot be reproduced.

**Evaluation:** Verify every cited record against the stored dataset and original source.

### Edge Case 19: Insufficient Evidence Is Not Acknowledged

**Scenario:** A user asks why first-time investors discontinue SIPs after 12 months, but the Golden Dataset contains only a few general complaints and no reliable 12-month continuation information.

**Expected behaviour:** Return the configured insufficient-evidence response:

"Insufficient evidence in the Golden Dataset to answer this question reliably."

**Failure condition:** The engine invents a definitive explanation or presents weakly related records as conclusive evidence.

**Evaluation:** Test questions for which the dataset has no relevant records or lacks the information required to answer reliably.

### Edge Case 20: AI Answer Changes Between Runs

**Scenario:** The same question is asked multiple times against the same dataset version, but the answer, counts, or citations change unexpectedly.

**Expected behaviour:** Evidence counts and citations should remain consistent for a fixed dataset and retrieval configuration. Generated summaries may vary if generation is nondeterministic, but they must remain grounded in the same evidence.

**Failure condition:** The engine returns different record counts, unsupported claims, or inconsistent citations without a corresponding change in the dataset or configuration.

**Evaluation:** Repeat the same query under the same settings and compare retrieved record IDs, counts, citations, and conclusions.

## 3. Suggested Evaluation Scorecard

Use the following scorecard to test each edge case.

| **Field** | **Description** |
|---|---|
| Test ID | Unique edge-case identifier |
| Test input | Question or record supplied to the engine |
| Expected behaviour | What a reliable system should do |
| Actual output | What the engine actually returned |
| Pass/Fail | Whether the expected behaviour was met |
| Severity | Critical / High / Medium / Low |
| Evidence | Relevant record IDs, quotes, or screenshots |
| Root cause | Retrieval / Classification / Generation / Data quality / Unknown |
| Corrective action | Specific change to investigate or implement |
| Retest result | Result after the fix is tested again |

### Suggested severity definitions

- **Critical:** Fabricated evidence, materially false claims, or failure to respect the insufficient-evidence rule.
- **High:** Incorrect classification or unsupported conclusions that materially change the product insight.
- **Medium:** Missing relevant evidence, misleading counts, or incomplete context.
- **Low:** Presentation issues that do not materially change the conclusion.

These severity levels are proposed for the evaluation and should be applied consistently.

## 4. Recommended Evaluation Sequence

Prioritise the following tests first:

1. **Relevance:** Does the retrieved record genuinely support the problem?
2. **Evidence fidelity:** Does the quote support the claim?
3. **Classification:** Are payment failures, cancellations, pauses, and modifications distinguished correctly?
4. **Causal inference:** Does the engine avoid claiming that a problem causes discontinuation without evidence?
5. **Insufficient evidence:** Does it abstain when the dataset cannot support an answer?
6. **Citation integrity:** Can every record, quote, and statistic be verified?
7. **Prioritisation:** Does the score reflect the configured scoring method rather than an assumed business outcome?

These tests address the most consequential risks visible in the current opportunity outputs.

## 5. Definition of Success

The engine should be considered reliable for this use case only after testing demonstrates that it:

- Retrieves substantively relevant evidence.
- Distinguishes direct evidence from inference.
- Correctly classifies investor behaviour and unmet needs.
- Produces reproducible counts and verifiable citations.
- Identifies conflicting evidence and missing information.
- Abstains when evidence is insufficient.
- Presents product recommendations as hypotheses unless their impact has been validated.

**Final note:** This catalogue defines how the engine can fail and how to test those failures. It does not claim that all 20 cases have been executed or that the engine has passed or failed each test. Actual results must be recorded after running the tests against the current system.
