# Limitations

## Sources

- **Integrated and tested:** Google Play reviews (5 apps), YouTube comments (6 videos), Reddit posts and comments (3 subreddits). **Not integrated:** Apple App Store, TradingQ&A.
- **Terms of service:** Google Play is read with an unofficial library and Reddit via a third-party scraper (Apify). The project owner accepted both risks (`docs/source_access_plan.md` §1c, §6a). Reddit's restrictions on AI use apply and are part of that accepted risk.
- **YouTube:** official API; comments may be kept at most 30 days; not sent to AI models; not in the Golden Dataset.

## Sampling and selection bias

- Play Store: newest 30,000 reviews per app, so recent years dominate and apps reach different years back.
- Reddit: keyword searches and a title-keyword shortlist, deliberately skewed to stopping, pausing and payment problems.
- Public reviews over-represent people with problems. Nothing here measures how common a behaviour is among investors.
- Golden Dataset: 300 rows balanced across source × behaviour; not a random sample.

## Classification

- Tags are LLM output against a draft codebook (v3) that has not been reviewed by a human.
- In the 30-item inter-model check (tag-v4) the models agreed 80% on behaviour, 90% on lapse type and 57% on trigger.
- Segment fields (income, age, money source, influencer) are almost always unclear in public posts; segments will use proxies validated through interviews.
- The relevance filter has processed only part of the Play Store data; many records are not yet labelled.

## Golden Dataset

All 300 rows were bulk-approved without row-by-row review. Findings are labelled "(unverified)".

## Research assistant

- Retrieval is keyword and tag based; relevant records using different wording can be missed.
- Answers depend on Groq availability and free-tier limits; when unavailable, the matching evidence is still shown.
- About 1,800 tokens per new question (cached per question and dataset version).

## Data quality reporting

Play Store and YouTube collectors do not persist run logs, so their collection failures are not counted. Reddit dates from the actor are sometimes the scrape time; those are stored as unknown.
