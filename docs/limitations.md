# Limitations

## Sources

- **Integrated and tested:** Google Play reviews (5 apps), YouTube comments (6 videos), Reddit posts and comments (3 subreddits). **Not integrated:** Apple App Store, TradingQ&A.
- **Terms of service:** Google Play is read with an unofficial library and Reddit via a third-party scraper (Apify). The project owner accepted both risks (`docs/source_access_plan.md` §1c, §6a). Reddit's restrictions on AI use apply and are part of that accepted risk.
- **YouTube:** official API; comments may be kept at most 30 days; not sent to AI models; not in the Golden Dataset.

## Sampling and selection bias

- Play Store: newest 30,000 reviews per app, so recent years dominate and apps reach different years back.
- Reddit: keyword searches and a title-keyword shortlist, deliberately skewed to stopping, pausing and payment problems.
- Public reviews over-represent people with problems. Nothing here measures how common a behaviour is among investors.
- Golden Dataset: 300 rows sampled across source × behaviour (296 after 4 were rejected as not relevant), plus 116 rows selected because the writer says they are new to investing (2026-10-28). Not a random sample; new investors are deliberately over-represented.

## Classification

- Tags are LLM output against a draft codebook (v3) that has not been reviewed by a human.
- On 20 owner-adjudicated records the engine's pain and need tags were right only 10 and 9 times; it often returns `unclear` when the text states the problem. Opportunity counts inherit these errors in both directions (`docs/ai_eval_test_report.md` §9).
- In the 30-item inter-model check (tag-v4) the models agreed 80% on behaviour, 90% on lapse type and 57% on trigger.
- Segment fields (income, age, money source, influencer) are almost always unclear in public posts; segments will use proxies validated through interviews.
- The relevance filter has processed only part of the Play Store data; many records are not yet labelled.

## Golden Dataset

All rows are recorded as individually reviewed by the project owner (evidence log §7.2). That review corrected no tags; 64 corrections on 39 records were applied later (D-3 and the 20-record labelled set, 2026-10-28). The other tags are the model's output, and the 20-record check suggests pain and need tags are often wrong (`docs/ai_eval_test_report.md` §9). The dataset is not independent ground truth.

94 rows carry the new-investor tenure tag: 5 from the original sample and 89 from the 116 bulk-approved D-8 rows, whose tags were not reviewed row by row. Most of those 89 are short app reviews with no SIP action or stated need.

**Beginner guidance has too little evidence to show.** Since 2026-10-28 (D-10) it counts only records tagged with a fund-choice need or pain, not every new investor. After 4 mis-tagged records were corrected, 3 remain, below the 5-record minimum. Questions about first-time investors therefore usually return the insufficient-evidence message.

## Research assistant

- Retrieval is keyword and tag based; relevant records using different wording can be missed. A matching tag alone still makes a record evidence.
- Answer points can cite records that only partly support them. In the 2026-10-28 live check, 8 of 17 points were partly or not supported, and 2 of 4 summaries claimed frequency or a segment the records did not show (`docs/ai_eval_test_report.md` §8). That check was by Claude Code, not by a person.
- Answers depend on Groq availability and free-tier limits; when unavailable, the matching evidence is still shown.
- About 1,800 tokens per new question (cached per question and dataset version).

## Data quality reporting

Play Store and YouTube collectors do not persist run logs, so their collection failures are not counted. Reddit dates from the actor are sometimes the scrape time; those are stored as unknown.
