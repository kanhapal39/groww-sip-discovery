# Source Access Plan — SIP Discovery Engine

Status: Prepared for review. No data had been collected before 2026-10-26. **Exception:** the user explicitly approved a capped Google Play reviews pilot on 2026-10-26 (see section 1c), accepting the terms-of-service risk.

**All other source approvals remain PENDING until each source's documented requirements are met and the user explicitly approves it.** Automated scraping is not recommended as a workaround; the Google Play pilot in section 1c is a user-accepted exception.

This document evaluates the feasibility of collecting permitted public discussions about SIP investor behaviour in India from five sources. Each source is assessed for official API access, terms of service compliance, authentication, rate limits, cost, available fields, limitations, bias, and manual fallback.

## 1. Google Play Store reviews

### Official access for developer-owned apps

**Google Play Developer API** — `reviews.list` endpoint
- URL: `https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{packageName}/reviews`
- Method: GET
- Authorization scope: `https://www.googleapis.com/auth/androidpublisher` (OAuth)
- Reference: https://developers.google.com/android-publisher/api-ref/rest/v3/reviews/list

This API returns reviews **only for apps owned by the authenticated developer account** (Google Play Console). It requires a Google Play Developer account ($25 one-time fee) and app ownership.

### Official access for third-party apps

**No official API or export method exists.** Multiple official and third-party sources confirm:

- Google does not offer a public API for store listings, search results, or reviews of third-party apps.
- The Google Play Developer API (`reviews.list`, `reviews.get`) is scoped exclusively to apps owned by the authenticated developer account.
- Reference: https://developers.google.com/android-publisher/api-ref/rest/v3/reviews/list
- Reference: https://developers.google.com/android-publisher/terms

### Terms of service and access restrictions (Google)

- **Google Terms of Service** prohibit automated access to Google services in violation of machine-readable instructions (e.g., `robots.txt`). Reference: https://policies.google.com/terms?hl=en-US
- Google Play Store web pages and internal endpoints are subject to these restrictions. Automated scraping of third-party app reviews may violate Google's ToS.
- Google actively blocks scraping through rate limits, CAPTCHAs, and shifting internal API surfaces.

### Authentication

- Developer-owned apps: OAuth 2.0 with Google Cloud service account or OAuth client.
- Third-party apps: No authenticated or unauthenticated official access method exists.

### Rate limits and cost

- Developer-owned apps: No documented per-call cost; subject to Google Cloud quotas.
- Third-party apps: No official rate limits or pricing, because no official access method exists.

### Available fields

- Developer-owned apps: `reviewId`, `authorName`, `comments[]` (review text, last modified timestamp, developer reply).
- Third-party apps: No fields available through any official method.

### Known limitations and bias

- **Google Play reviews are inaccessible for third-party investment apps** (e.g., Zerodha, Groww, Upstox, Angel One) through any official, permitted, free method.
- Reviews are app-store-specific; may not capture broader SIP behaviour discussions outside the app context.
- Third-party scraping tools exist (e.g., google-play-scraper, Apify actors) but these scrape public web pages/internal APIs unofficially. They are not supported by documented terms or permissions and can be blocked or changed by Google at any time. **Scraping is not recommended as a workaround.**

### Manual import fallback

- Manual copy-paste of individual reviews from Google Play Store web pages is technically possible but does not scale (suitable only for tens of records, not thousands).
- Manual copy-paste may violate Google's ToS if automated or performed at scale.
- Manual entries must carry: source URL, collection timestamp, stable record ID, and verbatim text.

### Status

**Unavailable for third-party investment apps we do not manage** — The official Google Play Developer API (`reviews.list`) only returns reviews for apps managed by the authenticated developer account. No official API, no permitted free automated method, and Google's Terms of Service restrict automated access. Only usable if we own the investment app (which we do not, per user decision). Not a viable source for third-party SIP discussions.

---

## 1b. Groww Google Play Store listing (com.nextbillion.groww) — specific assessment

### Source under investigation

- **App:** Groww (investment/trading app by Nextbillion Technology Pvt Ltd)
- **Package ID:** com.nextbillion.groww
- **Listing URL:** https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN
- **Objective:** Determine whether public Groww reviews can be collected for SIP investor behaviour research at ₹0 budget.

### Official access for Groww reviews

**Google Play Developer API** — `reviews.list` endpoint
- URL: `https://androidpublisher.googleapis.com/androidpublisher/v3/applications/com.nextbillion.groww/reviews`
- Method: GET
- Authorization scope: `https://www.googleapis.com/auth/androidpublisher` (OAuth)
- Reference: https://developers.google.com/android-publisher/api-ref/rest/v3/reviews/list

This API requires the `androidpublisher` OAuth scope and authenticates against a Google Play Developer account. It returns reviews **only for apps owned by the authenticated developer account**. Groww is owned by Nextbillion Technology Pvt Ltd, not by us. Therefore, this API cannot access Groww reviews.

### Can the official review API access reviews for an app we do not own?

**No.** Official Google documentation confirms:

- The `reviews.list` endpoint accepts a `packageName` path parameter, but the API is scoped to apps owned by the authenticated developer account via the `androidpublisher` OAuth scope.
- Google Play Developer API Terms of Service (last modified March 15, 2022) state: "You will only use the Publishing API for your own activities related to your distribution of products under the Google Play Developer Distribution Agreement. You will not utilize a third party's Developer Account to access the Publishing API."
- Reference: https://developers.google.com/android-publisher/terms
- Reference: https://developers.google.com/android-publisher/api-ref/rest/v3/reviews/list

### Is there any official, free, documented method for third-party Groww reviews?

**No.** Multiple official sources confirm:

- Google does not offer a public API for store listings, search results, or reviews of third-party apps.
- No unauthenticated or unauthenticated-official endpoint exists for reading third-party app reviews.
- Third-party scraping tools (e.g., google-play-scraper, Apify actors) scrape public web pages or internal APIs unofficially. They are **not** supported by documented terms or permissions and can be blocked or changed by Google at any time. They are also excluded by the ₹0 budget constraint (paid services/proxies).

### Terms of service and access restrictions (Google)

- **Google Terms of Service** prohibit automated access to Google services in violation of machine-readable instructions (e.g., `robots.txt`). Reference: https://policies.google.com/terms?hl=en-US
- Google Play Store web pages and internal endpoints are subject to these restrictions. Automated scraping of Groww reviews may violate Google's ToS.
- Google actively blocks scraping through rate limits, CAPTCHAs, and shifting internal API surfaces.

### Authentication

- Developer-owned apps: OAuth 2.0 with Google Cloud service account or OAuth client + Google Play Developer account ($25 one-time fee) + app ownership.
- Groww (third-party app): No authenticated or unauthenticated official access method exists.

### Rate limits and cost

- Developer-owned apps: No documented per-call cost; subject to Google Cloud quotas.
- Groww (third-party app): No official rate limits or pricing exist, because no official access method exists.

### Available fields

- Developer-owned apps: `reviewId`, `authorName`, `comments[]` (review text, last modified timestamp, developer reply).
- Groww (third-party app): No fields available through any official method.

### Known limitations and bias

- **Groww reviews are inaccessible for SIP investor behaviour research** through any official, permitted, free method.
- Reviews are app-store-specific; may not capture broader SIP behaviour discussions outside the app context.
- No geographic or demographic filtering beyond what the Play Console provides (and only for owned apps).

### Manual import fallback for Groww

- Manual copy-paste of individual Groww reviews from the Google Play Store web page is technically possible but does not scale (suitable only for tens of records, not thousands).
- Manual copy-paste may violate Google's ToS if automated or performed at scale.
- Manual entries must carry: source URL (https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN), collection timestamp, stable record ID, and verbatim text.
- Manual fallback does not scale and is suitable only for small validation sets (tens of records, not thousands).

### Status

**Unavailable for third-party investment apps we do not manage** (NO-GO) — No official API, no permitted free automated method, and Google's Terms of Service restrict automated access. Groww is a third-party app we do not manage. Collecting Groww reviews at ₹0 through a permitted method is not possible.

### GO / NO-GO recommendation

**NO-GO** for Groww Google Play Store reviews at ₹0 budget.

Reasoning:
1. The official Google Play Developer API (`reviews.list`) only returns reviews for apps owned by the authenticated developer account. We do not own Groww (com.nextbillion.groww).
2. No official, free, documented method exists for collecting third-party app reviews.
3. Unofficial scraping methods may violate Google's Terms of Service and are not recommended as a workaround, regardless of budget.
4. Manual copy-paste is the only remaining option but does not scale and may violate Google's ToS if performed systematically.

---

## 1c. USER DECISION — Google Play reviews pilot (2026-10-26)

The user has explicitly chosen to override the "unavailable / scraping not recommended" assessment above for a **capped pilot only**. This is a deliberate decision by the project owner, not a finding that collection is permitted.

- **Method:** Unofficial `google-play-scraper` Python library reading public Play Store review pages. This is **not** an official API and is **not** authorized by Google's documented terms.
- **Accepted risk:** Google's Terms of Service restrict automated access; the method may break or be blocked at any time. The user accepts this terms-of-service risk for the pilot.
- **Scope:** Public reviews of third-party investment apps listed in `config.yaml` (`collection.play_store.apps`), language `en`, country `in`, newest first.
- **Caps:** Maximum 200 reviews per app, one run, with a pause between apps. No retries, no proxies, no CAPTCHA circumvention.
- **Fields stored:** review text, star rating, review date, app ID, review ID, plus provenance (record ID, source URL, collection timestamp). **Reviewer names, profile images and developer replies are not stored.**
- **Storage:** `data/raw/` and `data/processed/` only (gitignored). Not to enter the permanent Golden Dataset or be sent to an external AI provider without a further explicit decision.
- **Not covered by this decision:** Any other source, scale-up beyond the pilot caps, or production collection. All other approvals remain PENDING.
- **Update 2026-10-26 (user decisions):** cap raised to 30,000 reviews per app (`docs/evidence_log_notes.md` §3.3). The user directed that clean Play Store review text be sent to Groq (`openai/gpt-oss-20b`) for relevance filtering (§4.2). Groq's data-retention and training terms have not been reviewed in this project.

---

## 2. Apple App Store reviews

### Access method

Official: **App Store Connect API** — Customer Reviews resource
- Reference: https://developer.apple.com/documentation/appstoreconnectapi/customer-reviews
- Alternative (public, no reviews): iTunes Search API / Lookup API — returns app metadata only, not reviews.
  - Reference: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html

### Terms of service and access restrictions

- Customer Reviews API returns reviews **only for apps owned by the authenticated App Store Connect account** (Apple Developer Program).
- Cannot retrieve reviews of third-party apps.
- iTunes Search API terms: promotional content may be used only to promote store content, not for entertainment or research purposes.

### Authentication

- App Store Connect API key (generated in App Store Connect).
- Requires Apple Developer Program membership ($99/year) and ownership of the target app.

### Rate limits and cost

- No documented per-call cost; subject to Apple's API rate limits.
- Apple Developer Program membership required.

### Available fields

- Customer review text, rating, timestamp, territory (for apps we own).
- iTunes Search/App Store Lookup: app name, developer, version, rating count, average rating (no individual review text).

### Known limitations and bias

- Only usable for apps we publish. Not usable for third-party investment apps.
- iTunes Search API does not expose individual review text, so it cannot support SIP behaviour research.

### Manual import fallback

- Manual copy-paste from App Store web pages is possible but does not scale and may violate Apple's ToS if automated.

### Status

**Requires review** — Only applicable if we own the investment app in question. Not a viable source for third-party SIP discussions without app ownership.

---

## 3. Reddit — detailed assessment

### Source under investigation

- **Platform:** Reddit
- **Objective:** Determine whether public Reddit posts/comments about SIP investor behaviour in India can be collected for research at ₹0 budget.
- **Candidate subreddits:** r/IndiaInvestments, r/IndianStreetBets, r/personalfinanceindia, etc.

### Official access method

**Reddit Data API**
- OAuth 2.0 authentication required for all access; unauthenticated requests are blocked
- Reference: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
- Developer Platform documentation: https://developers.reddit.com/docs/

### Terms of service and access restrictions (verified from official docs)

**Reddit Data API Terms:**
- https://redditinc.com/policies/data-api-terms

**Reddit Developer Terms:**
- https://www.redditinc.com/policies/developer-terms

**Developer Platform & Accessing Reddit Data (Reddit Help, updated May 28, 2026):**
- https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data

Key findings from official Reddit documentation:

1. **Commercial use is prohibited without explicit written permission and a contract:**
   > "You cannot use any Reddit developer tools and services for commercial purposes without first getting our permission."
   > Commercial purposes include: "Services, research, or data access for fees", "Subscription services", "Publishing content from Reddit on monetized websites or apps with ads", "Selling access to models trained on Reddit data"
   > "If you're interested in using Reddit data to power, augment, or enhance your product or service for any commercial purposes, you'll need our permission, and we'll require a contract."

2. **Free tier is non-commercial only:**
   > Free access is for "Moderators, Developers and General Non-Commercial Uses"
   > Commercial use requires reaching out through Reddit's contact form for enterprise/commercial access

3. **Research use:**
   > "No. The only official and authorized avenue for performing research using Reddit data is through the Reddit For Researchers (RFR) program."
   > "Using developer tools, APIs, or unauthorized third-party tools for academic research is a violation of our policies."
   > RFR program: https://support.reddithelp.com/hc/articles/49381918834964/
   > Application: https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164&tf_42139884615700=api_request_type_researcher_clone

4. **AI/ML training restriction:**
   > "You may not use content on Reddit as an input for any model training without explicit consent from Reddit."
   > "Commercial use of any model trained with Reddit data is prohibited without explicit approval."
   > This is critical for our project: we plan to feed Reddit data into an NVIDIA LLM for tagging/classification.

5. **Data deletion requirement:**
   > Must remove any user content that has been deleted from Reddit (within ~48 hours recommended).

6. **Rate limits:**
   - Free tier: 100 queries per minute (QPM) per OAuth client ID, averaged over 10-minute windows
   - Both Data API and Ads API subject to rate limits

### Authentication

- OAuth 2.0 access token via a registered Reddit application (client ID + client secret)
- User-Agent header required: `<platform>:<app ID>:<version string> (by /u/<username>)`
- Reference: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki

### Rate limits and cost

- Free tier: 100 QPM per OAuth client ID
- Commercial use: Requires written permission and contract; pricing not publicly disclosed (reported ~$12,000/month minimum by third-party sources, not officially confirmed by Reddit)
- Self-service registration: Available via ticket submission; new OAuth tokens may require manual approval

### Available fields

- Posts: title, body (selftext), subreddit, author, timestamp (UTC), permalink URL, score, upvote ratio, comment count
- Comments: body, author, timestamp, parent ID, permalink URL

### Known limitations and bias

- **Commercial use restriction:** Our platform is described as a commercial research product; Reddit free tier explicitly excludes commercial use
- **AI/ML restriction:** Feeding Reddit data into an NVIDIA LLM for tagging is explicitly prohibited without explicit consent from Reddit
- **Research restriction:** Only official research avenue is RFR program; using Data API for research is a violation unless approved through RFR
- **OAuth approval:** Self-service registration exists but new tokens may require manual approval (timeline uncertain)
- **Demographic bias:** Reddit users skew younger and more tech-savvy; may not represent all Indian SIP investors
- **Deleted content:** Must remove deleted user content within ~48 hours
- **Subreddit fragmentation:** SIP discussions spread across multiple subreddits

### Manual import fallback

- Manual copy-paste of individual Reddit posts/comments is possible but does not scale and may violate Reddit's ToS if automated.

### Status

**BLOCKED** — Reddit's official documentation explicitly states:
1. Commercial use requires written permission and a contract (our product is commercial)
2. Using Reddit data as input for model training (NVIDIA LLM tagging) is prohibited without explicit consent
3. The only authorized research avenue is the Reddit For Researchers program, which is for academic research, not commercial product development

**BLOCKED pending explicit authorization from Reddit and clarification of commercial use, research use, AI processing, and data retention.** Cannot proceed until all four are resolved in writing.

---


---

## 4. TradingQ&A (Zerodha community forum)

### Access method

- Platform: Discourse (https://www.discourse.org/)
- Discourse has an official API, but requires API key authentication from the forum administrator.
- No public, unauthenticated API documented for TradingQ&A specifically.
- Site: https://tradingqna.com/
- Community guidelines: https://tradingqna.com/guidelines
- Terms of service discussion: https://tradingqna.com/t/terms-and-conditions-of-trading-q-a/144922

### Terms of service and access restrictions

- TradingQ&A is a public forum owned by Zerodha Broking Ltd. (SEBI-registered stock broker).
- Community guidelines require civil conduct; no explicit automated collection policy found in the reviewed pages.
- No official data export or API access documented for third parties.
- Zerodha support page confirms TradingQ&A is "free, open, and community-driven" (https://support.zerodha.com/category/trading-and-markets/trading-faqs/general/articles/what-is-tradingqna), but "open" does not imply permission to scrape.

### Authentication

- Discourse API key would need to be issued by TradingQ&A/Zerodha administrators. Not publicly available.

### Rate limits and cost

- No documented rate limits or pricing. Unknown.

### Available fields (Discourse standard, if API access were granted)

- Topic title, topic body (post content), category, tags, author, created/updated timestamps, post URL, reply count, like count.

### Known limitations and bias

- No verified API access method; automated collection may violate the site's implicit terms.
- India-focused, Zerodha-associated; may skew toward Zerodha users and Indian retail investors.
- SIP discussions likely present but volume unknown.

### Manual import fallback

- Manual copy-paste of individual topics/posts is possible but does not scale.

### Status

**Unavailable** — No verified public API or documented export method. Automated collection cannot be confirmed as permitted. Manual fallback does not scale.

---

## 5. YouTube — detailed assessment

### Source under investigation

- **Platform:** YouTube
- **Objective:** Determine whether public YouTube comments on SIP-relevant videos can be collected for Indian SIP investor behaviour research at ₹0 budget.
- **Candidate videos:** Manually selected public videos discussing SIPs, mutual funds, and Indian investing (video IDs known in advance).

### Official access method

**YouTube Data API v3** — `commentThreads.list` endpoint
- URL: `https://www.googleapis.com/youtube/v3/commentThreads`
- Method: GET
- Authentication: Google Cloud API key (for public comments) or OAuth 2.0 token (for private/moderator operations)
- Quota cost: 1 unit per call
- Max results per page: 100
- Pagination: `nextPageToken` for subsequent pages
- Reference: https://developers.google.com/youtube/v3/docs/commentThreads/list

**Video discovery** (finding SIP-relevant videos)
- `search.list` endpoint: 1 quota unit per call
- Default daily limit: 100 calls/day (separate quota bucket)
- Reference: https://developers.google.com/youtube/v3/docs/search/list
- **Alternative:** Manual video selection (no API call needed if video IDs are known in advance)

### Quota allocation (verified from official docs)

| Endpoint | Quota cost per call | Default daily limit | Notes |
|----------|-------------------|-------------------|-------|
| `commentThreads.list` | 1 unit | Part of 10,000 units/day combined pool | Max 100 results/page |
| `comments.list` | 1 unit | Part of 10,000 units/day combined pool | Individual comments |
| `search.list` | 1 unit | 100 calls/day (separate bucket) | Video discovery |
| `videos.list` | 1 unit | Part of 10,000 units/day combined pool | Video metadata |
| **Combined pool (all except search.list and videos.insert)** | — | **10,000 units/day** | Resets at midnight PT |

- Source: https://developers.google.com/youtube/v3/getting-started
- Source: https://developers.google.com/youtube/v3/determine_quota_cost

**₹0 pilot quota math (10 videos, 200 comments):**
- 10 × `commentThreads.list` calls (1 page each, 20 comments default) = 10 units
- Or to get 200 comments: 10 videos × 2 pages (100 max per page) = 20 units
- Plus optional `search.list` for discovery: up to 100 calls = 100 units
- Total well within 10,000 units/day free quota

### Authentication

- Public data (comments on public videos): Google Cloud API key
- No OAuth required for read-only public comment access
- Requires a Google Cloud project with YouTube Data API v3 enabled
- Reference: https://developers.google.com/youtube/v3/getting-started

### Terms of service and access restrictions

**YouTube API Services Terms of Service:**
- Governs all API access: https://developers.google.com/youtube/terms/api-services-terms-of-service
- Section 15 (Usage and Quotas): YouTube may set quotas; must not exceed or circumvent them
- Section 24.3 (Effect of Termination): Upon termination, must delete all API Data (including comments) in possession or control
- Section 16.1 (Ownership): YouTube retains all rights to API Data; developer retains rights only to their own API Client
- Section 7 (User Privacy): Must comply with privacy laws; must have a published privacy policy if collecting user data

**YouTube Terms of Service:**
- https://www.youtube.com/t/terms
- Section 3 (Permissions and Restrictions): Prohibits automated access via robots/scrapers except (a) public search engines per robots.txt, or (b) with YouTube's prior written permission. **Official API access is the authorized method and does not require separate written permission.**
- Section 4 (collect/harvest personal data): Prohibits collecting information that might identify a person unless permitted. Comments include author display name and channel ID — these are public API fields provided by YouTube.

**Commercial use and external AI processing — requires policy verification:**
- The YouTube API Services Terms of Service reviewed so far do not explicitly prohibit commercial use, but **no reviewed document explicitly permits our proposed commercial research use**. Absence of a prohibition is not confirmation of permission.
- Sending YouTube API Data (comment text) to an external AI provider (NVIDIA LLM) for relevance filtering and tagging has **not been verified** against the YouTube API Services Terms or Developer Policies.
- Both points must be verified against the current official YouTube API Services Terms of Service and YouTube API Services Developer Policies before collection.
- No separate commercial contract is known to be required for API access (unlike Reddit), but this is not a substitute for the verification above.

### CRITICAL ISSUE — API data retention (checked against official policies, 2026-10-26)

- **Source:** YouTube API Services Developer Policies, https://developers.google.com/youtube/terms/developer-policies (page last updated 2026-10-15), and YouTube API Services Terms of Service, https://developers.google.com/youtube/terms/api-services-terms-of-service (page last updated 2026-09-14).
- **Classification:** Comments fetched with an API key (no User Credentials) are **Non-Authorized Data** (Developer Policies §IV, Definitions).
- **§III.E.4.d:** API Clients may "temporarily store limited amounts of Non-Authorized Data", for "not longer than 30 calendar days", after which the data must be deleted or refreshed.
- **§III.E.4.e / §III.E.4.f:** Stored API Data must be kept "consistent with the current data", and user-facing presentations must show the most updated API Data.
- **§III.E.4.h:** API Clients must not "replace API Data with similar, independently calculated data" or use API Data to create new or derived data or metrics; own metrics shown alongside API Data need a clear disclosure that they are not from YouTube.
- **§III.E.2:** Aggregation is limited to channels under the same content owner, and API Data must not be aggregated to gain insights into YouTube's business.
- **ToS §16.1 / §24.3:** YouTube retains ownership of API Data and derivative works; all API Data must be deleted on termination.
- **Open question:** Whether SIP behaviour tags, theme counts, or other research findings are "derived data or metrics" under §III.E.4.h has **not** been determined and requires legal/policy review.
- **Verification note:** Clauses were read via a summarizing fetch tool; the user should confirm the exact wording directly on the official pages.
- **Why it is critical:** YouTube comments could not be stored indefinitely in `data/raw/`, `data/processed/`, `data/export/`, `data/review/`, or `data/manual/` without periodic refresh (re-fetching from the API) or deletion.
- **Required action before collection:** Verify the retention, refresh, and deletion requirements against the current official YouTube API Services Terms of Service and YouTube API Services Developer Policies, and record the exact clause references and wording in this document.
- The 30-day limit applies to comment text. The §III.E.4.h derived-data question is unresolved. YouTube collection approval remains **PENDING**.

### Golden Dataset implications for YouTube data

- The permanent Golden Dataset (`data/manual/`) **must not retain YouTube API Data** (including comment text) unless its storage and retention comply with the applicable YouTube API Services Terms and Developer Policies.
- Under §III.E.4.d, YouTube comment text cannot enter a permanent Golden Dataset as stored text; it must be deleted or refreshed within 30 calendar days. Any compliant alternative (for example, retaining only non-API-Data fields, or periodic refresh with deletion of records no longer available) must be verified against the policies and approved before implementation.
- Data-retention handling for YouTube records must be designed and approved before Stage 3 collection begins.

### Privacy policy and external AI-processing assessment (required before collection)

Before any YouTube collection, the following must be assessed and documented:

1. **Privacy policy:** Whether a published privacy policy is required for this product under YouTube API ToS Section 7 and applicable privacy law, and what it must disclose (data collected, purpose, retention, deletion, third-party processors).
2. **External AI processing:** Whether sending comment text to NVIDIA's API is permitted under the YouTube API Services Terms and Developer Policies, and under NVIDIA's own data-handling terms (retention, training use, data location).
3. **Disclosure:** Whether the privacy policy must name NVIDIA (or any other provider) as a processor of YouTube API Data.
4. **Retention alignment:** Whether NVIDIA's retention of submitted data is compatible with YouTube's retention and deletion requirements.

### Can comments be collected for manually selected videos without search.list?

**Yes.** `commentThreads.list` accepts a `videoId` parameter. If video IDs are known in advance (manually curated), no `search.list` call is needed. This avoids consuming the separate search quota bucket.

### Available fields (commentThreads.list)

- Comment text (`snippet.topLevelComment.snippet.textDisplay` or `textOriginal`)
- Author display name (`snippet.topLevelComment.snippet.authorDisplayName`)
- Author channel ID (`snippet.topLevelComment.snippet.authorChannelId.value`)
- Published/updated timestamps (`snippet.topLevelComment.snippet.publishedAt`, `updatedAt`)
- Video ID (`snippet.videoId`)
- Parent comment ID (for replies, `snippet.topLevelComment.snippet.parentId`)
- Like count (`snippet.topLevelComment.snippet.likeCount`)
- `nextPageToken` for pagination

### Known limitations and bias

- **Comment availability:** Only public comments on public videos. Videos with comments disabled return `commentsDisabled` (403 error).
- **Disabled comments:** Many investment/finance YouTube channels disable comments; this creates selection bias toward channels that allow comments.
- **Selection bias:** Comments only from manually selected videos; may not represent all Indian SIP investors.
- **Language coverage:** Comments may be in English, Hindi, or other Indian regional languages. Language detection needed for analysis.
- **Representativeness:** YouTube commenters skew toward engaged viewers; silent majority of SIP investors not represented.
- **Pagination:** Max 100 comments per call; multiple pages needed for more comments (each page costs 1 unit).
- **Deletion:** YouTube API ToS Section 24.3 requires deletion of all API Data upon termination of access.

### ₹0 pilot plan (proposed, not executed)

| Parameter | Value |
|-----------|-------|
| Max videos | 10 (manually selected SIP-relevant YouTube videos) |
| Max comments | 200 (approximately 20 per video, or 2 pages of 100 for a few videos) |
| Quota used | ~20-30 units (well within 10,000 units/day free tier) |
| API key needed | Yes (Google Cloud project + YouTube Data API v3 enabled) |
| OAuth needed | No (public comments only) |
| Cost | ₹0 |

### Account setup and user actions required before collection

1. Create a Google Account (if not already available)
2. Create a project in Google Cloud Console (console.cloud.google.com)
3. Enable YouTube Data API v3 for the project
4. Create API key credentials (API key for public data access)
5. Review YouTube API Services Terms of Service and Developer Policies, including verification of commercial use, external AI processing, the 30-day retention limit (§III.E.4.d), and the derived-data question (§III.E.4.h) (see CRITICAL ISSUE above)
6. Complete the privacy policy and external AI-processing assessment (see above) and prepare a privacy policy if required
7. Manually curate a list of 10 SIP-relevant YouTube video IDs
8. Document the video selection rationale (for provenance and audit)

### Status

**CONDITIONAL GO — approval PENDING** — Official free API available with generous quota; manual video selection avoids search quota. Commercial use and external AI processing require policy verification. Comment text may be stored for no longer than 30 calendar days (Developer Policies §III.E.4.d), so it cannot be held in a permanent Golden Dataset; whether derived research findings are restricted (§III.E.4.h) is unresolved. Requires verification of these items, the privacy/AI-processing assessment, user approval, and Google Cloud project setup.

---

## 5a. USER DECISION — YouTube comments pilot (2026-10-26)

The user explicitly approved a capped YouTube pilot and supplied the API key (stored in `.env`, gitignored). This is a decision by the project owner. It does **not** resolve the open policy questions in §5.

- **Method:** Official YouTube Data API v3, `videos.list` (titles) and `commentThreads.list` (top-level comments), API key only. No scraping, no `search.list`.
- **Videos:** 6 public videos chosen manually by the user (listed in `config.yaml` `collection.youtube.videos`). The user first said 5 and then sent 6 links; all 6 are used.
- **Caps:** At most 200 top-level comments in total, split evenly across the videos. Hard stop at **4,000 quota units (40% of the default 10,000 units/day)**, enforced in code (`collect/youtube.py` `QuotaBudget`).
- **Fields stored:** comment text, comment ID, video ID, video title, like count, reply count, published/updated timestamps, plus provenance (record ID, source URL, collection timestamp). **Author display name, channel ID and profile image are not stored.**
- **Retention:** Each record carries `delete_after` = collection date + 30 days (Developer Policies §III.E.4.d). Records must be deleted or refreshed by that date. YouTube comment text must not enter the permanent Golden Dataset.
- **Still unresolved (not covered by this decision):** commercial use, sending comment text to NVIDIA or any external AI provider, whether research findings are "derived data" (§III.E.4.h), and the privacy-policy requirement. No YouTube data may be sent to an LLM until these are resolved.

---


---

## 6. Apify Reddit actors (paid third-party option)

### Access method

Apify Store hosts multiple Reddit scraper actors:

| Actor | Developer | Pricing (per 1,000 results) | Model |
|-------|-----------|----------------------------|-------|
| apify/reddit-scraper | Apify | from $2.50 | Pay-per-event |
| trudax/reddit-scraper | Trudax | from $0.10 | Pay-per-event + platform usage |
| comchat/reddit-api-scraper | comchat | $5.00 | Pay-per-event |
| practicaltools/apify-reddit-api | practicaltools | from $2.00 | Pay-per-event |
| automation-lab/reddit-scraper | automation-lab | from $0.60 | Pay-per-event |

- Reference: https://apify.com/store (Reddit scraper category)
- Apify pricing model: https://apify.com/pricing

### Terms of service and access restrictions

- Apify actors scrape Reddit's public web; they do not use the official Reddit Data API.
- Use of these actors for Reddit data collection is still subject to Reddit's Data API Terms and Developer Terms (OAuth required, commercial use restrictions, deleted-content removal).
- Apify platform usage is billed separately from Actor event fees (compute units).

### Authentication

- No Reddit API key required (actors scrape public web pages).
- Apify account required; Apify API token for programmatic runs.

### Rate limits and cost

- Pay-per-event pricing varies by actor ($0.10–$6.00 per 1,000 results).
- Apify platform compute usage billed separately (Free plan: $0.2/CU; Starter plan: $49/month).
- Maximum charge per run can be capped via `maxTotalChargeUsd`.
- **Actual pricing for a specific actor run cannot be verified without checking each actor's live pricing page and running a test.** Costs are uncertain pending user review.

### Known limitations and bias

- Third-party scrapers may break if Reddit changes its page structure.
- Same Reddit demographic biases apply.
- Commercial use of Reddit data via third-party scrapers remains subject to Reddit's commercial use restrictions.

### Manual import fallback

- Not applicable (this is already an automated third-party tool).

### Status

**Not recommended** — These actors scrape Reddit's public web rather than using the official Data API, and scraping is not recommended as a workaround. Use would remain subject to Reddit's terms (see Reddit BLOCKED status). No actor will be started and no credits consumed.

---

## 6a. USER DECISION — Reddit via Apify pilot (2026-10-26)

The user explicitly chose to collect Reddit data through an Apify actor despite the BLOCKED status in §3 and the "not recommended" status in §6, accepting the terms-of-service risk. This is a decision by the project owner, not a finding that collection is permitted.

- **Tool:** Apify actor `automation-lab/reddit-scraper` (pay per event). Prices read from the Apify API on 2026-10-26 for the FREE plan: post $1.15 per 1,000, comment $0.575 per 1,000, $0.003 per run start. Chosen as the cheapest listed actor that supports subreddit search, posts-only runs and comments for thread URLs.
- **Method:** scrapes Reddit's public web through a third party. Not Reddit's official Data API.
- **Budget:** hard cap of $3.50 total across all runs, enforced in code (`collect/reddit_apify.py` ledger check before each run, plus Apify `maxTotalChargeUsd`).
- **Scope:** r/IndiaInvestments, r/mutualfunds, r/personalfinanceindia; 2021 onward; a 30-item test, then ~150 posts (posts only), then up to 15 comments per shortlisted thread, after a separate user approval.
- **Privacy:** every username is removed before anything is written, including from titles, text and links. Author fields are never stored.
- **Storage:** `data/raw/` only (gitignored).
- **AI processing:** the user directed that Reddit text be filtered and tagged with Groq models. Reddit's restrictions on AI/ML use (§3) still apply and are part of the accepted risk.

## Summary of source statuses

| Source | Status | Official API? | Commercial use permitted? | Upfront cost | Ongoing cost | Free quota/limits |
|--------|--------|---------------|---------------------------|--------------|--------------|-------------------|
| Google Play Store reviews (developer-owned apps) | Requires review | Yes (`reviews.list`) | N/A (app ownership required) | $25 (Play Console) | None documented | No per-call cost |
| Google Play Store reviews (third-party apps we do not manage — including Groww) | **Unavailable** via official API; **capped pilot approved by user 2026-10-26 (risk accepted, §1c)** | Official API unavailable for apps we do not manage | Not applicable | N/A | N/A | N/A |
| Apple App Store reviews (developer-owned apps) | Requires review | Yes (App Store Connect API) | N/A (app ownership required) | $99/year | None documented | No per-call cost |
| Apple App Store reviews (third-party apps) | **Unavailable** | No official API | Not applicable | N/A | N/A | N/A |
| **YouTube** | **CONDITIONAL GO (approval PENDING)** | Yes (Data API v3) | Requires policy verification (not explicitly prohibited; not explicitly permitted) | $0 | None | 10,000 units/day; search.list: 100 calls/day |
| **Reddit** | **BLOCKED** | Yes (OAuth) | No (free tier = non-commercial only; commercial requires written contract) | $0 | Undisclosed (commercial) | 100 QPM (free, non-commercial only) |
| TradingQ&A | Unavailable | No verified public API | Unknown | Unknown | Unknown | Unknown |
| Apify Reddit actors | **Not recommended** (scraping workaround) | No (third-party scraper) | Subject to Reddit's terms | $0 (account) | Pay-per-event ($0.10–$6.00/1,000 results) | N/A |

## Compliance considerations

1. **No source is approved for collection.** All sources require explicit review and approval before any data is collected.
2. **Publicly visible content is not automatically permitted for automated collection.** Each source's terms of service must be reviewed and respected.
3. **Google Play and Apple App Store review APIs are only usable for apps we own.** They cannot retrieve reviews of third-party investment apps where SIP discussions occur.
4. **The official Google Play reviews API is unavailable for third-party investment apps we do not manage (including Groww / com.nextbillion.groww)** — no official API, no permitted free automated method, and Google's Terms of Service restrict automated access. Groww is a third-party app we do not own.
5. **Reddit is BLOCKED** — Reddit's official documentation explicitly states:
   - Commercial use requires written permission and a contract (our product is a commercial research platform)
   - Using Reddit data as input for model training (NVIDIA LLM tagging) is prohibited without explicit consent from Reddit
   - The only authorized research avenue is the Reddit For Researchers (RFR) program, which is for academic research, not commercial product development
   - **BLOCKED pending explicit authorization from Reddit and clarification of commercial use, research use, AI processing, and data retention.**
6. **YouTube is CONDITIONAL GO (approval PENDING)** — Official free API available; commercial use requires policy verification (not explicitly prohibited, not explicitly permitted); requires compliance with all terms including data deletion upon termination (Section 24.3), privacy policy (Section 7), and attribution requirements. Developer Policies §III.E.4.d limits stored comment text to 30 calendar days (delete or refresh); §III.E.4.h derived-data implications must be resolved before collection.
7. **Deleted content must be removed** (Reddit specifically requires this; YouTube ToS Section 24.3 requires deletion of all API Data upon termination).
8. **Provenance must be preserved** on every collected record (source URL, collection timestamp, stable record ID) per AGENTS.md rule 1.
9. **₹0 budget constraint**: No paid services, scraping actors, or credit-consuming runs are permitted. This excludes Apify Reddit actors and any other paid third-party tool.
10. **External NVIDIA API processing:** Whether YouTube comment data may be sent to the NVIDIA LLM for tagging requires policy verification against the YouTube API Services Terms and Developer Policies. Feeding Reddit data into an LLM is explicitly prohibited by Reddit's terms without explicit consent.

## Comparison table: YouTube vs Reddit

| Criteria | YouTube Data API v3 | Reddit Data API |
|----------|-------------------|-----------------|
| Official access method | Google Cloud API key + YouTube Data API v3 | OAuth 2.0 + Reddit Data API |
| Account/approval requirements | Google Cloud project; enable YouTube Data API v3; create API key | Reddit developer account; register OAuth app; submit ticket for access |
| Commercial research use permitted | Requires policy verification (not explicitly prohibited; not explicitly permitted) | No (free tier = non-commercial only; commercial requires written contract) |
| Upfront cost | $0 | $0 |
| Ongoing cost | None documented | Undisclosed (commercial requires contract) |
| Free quota/access limits | 10,000 units/day combined; commentThreads.list: 1 unit/call; search.list: 100 calls/day separate bucket | 100 QPM (free, non-commercial only) |
| Expected effort to find SIP discussions | Low (manual video selection; no search needed if video IDs known) | Medium (multiple subreddits; SIP discussions fragmented) |
| Data storage/deletion restrictions | Must delete all API Data upon termination (ToS §24.3); privacy policy required (§7); Non-Authorized Data stored ≤30 calendar days, then deleted or refreshed (Developer Policies §III.E.4.d) — **critical** | Must delete deleted user content within ~48 hours |
| External NVIDIA API processing allowed | Requires policy verification | No (explicitly prohibited: model training on Reddit data requires explicit consent) |
| Main compliance risks | Unverified data retention limits; unverified commercial use and external AI processing; comment disablement (403); language coverage; selection bias | Commercial use prohibition; AI/ML training prohibition; OAuth approval uncertainty |
| Final status | **CONDITIONAL GO (approval PENDING)** | **BLOCKED** |

## Proposed pilot limits (subject to approval)

If a source is approved, the pilot collection should be limited to:

- **YouTube**: Maximum 10 videos and 200 comments, manually selected SIP-relevant videos, within default quota (10,000 units/day; ~20-30 units used for 10 videos × 20 comments). Requires Google Cloud project setup and API key.
- **Reddit**: BLOCKED — not available for pilot collection under current terms (commercial use + AI/ML training restrictions).
- **Google Play / Apple App Store (third-party apps — including Groww)**: Not viable — no official API or permitted free automated method exists for third-party app reviews. Groww (com.nextbillion.groww) is specifically assessed as NO-GO at ₹0 budget.
- **Google Play / Apple App Store (developer-owned apps)**: Not applicable — we do not own investment apps (per user decision).
- **TradingQ&A**: Not recommended for pilot due to no verified API access.
- **Apify Reddit**: Not recommended — excluded by ₹0 budget and requires paid service.

---

## Minimal comment fields specification

The following fields are the **minimum necessary** for SIP investor behaviour research. Each field is justified:

| Field | Source | Why needed | Provenance requirement |
|-------|--------|------------|------------------------|
| `comment_text` | `snippet.topLevelComment.snippet.textOriginal` | Core content for SIP behavior tagging | Verbatim, never invented |
| `video_id` | `snippet.videoId` | Links comment to source video; enables deduplication | Required |
| `source_url` | Constructed: `https://www.youtube.com/watch?v=<video_id>` | Permanent link to source | Required per AGENTS.md rule 1 |
| `collected_at` | System timestamp at collection time | When the record was acquired | Required per AGENTS.md rule 1 |
| `record_id` | Stable UUID generated at collection | Unique identifier for the record | Required per AGENTS.md rule 1 |

### Fields intentionally NOT collected

- **Author display name** (`authorDisplayName`): Not needed for SIP behavior tagging; collecting personal identifiers increases privacy risk and is discouraged by YouTube ToS Section 4.
- **Author channel ID** (`authorChannelId`): Not needed for SIP behavior tagging; same privacy concerns as above.
- **Like count**: Not needed for behavior tagging; engagement metrics don't answer the research questions.
- **Published/updated timestamps**: Not needed for the core research questions; collection timestamp is sufficient.

All collected records must preserve: source URL, collection timestamp (ISO-8601), stable record ID. No fabricated fields.

---

## Pilot workflow (step-by-step)

The following workflow applies **only after** the user explicitly approves YouTube for pilot collection:

1. **Setup**: User creates Google Cloud project, enables YouTube Data API v3, creates API key (see Google Cloud Console steps below).
2. **Video selection**: User manually selects up to 10 SIP-relevant YouTube video IDs and records them in `data/manual/youtube_video_ids.txt`.
3. **Collection**: Collector reads video IDs from the file, calls `commentThreads.list` for each video, collects up to 200 comments total.
4. **Storage**: Raw comments stored in `data/raw/` with full provenance (source URL, collection timestamp, record ID).
5. **Cleaning**: Text normalized, min/max length enforced (10-5000 chars), duplicates removed by source URL.
6. **Relevance filtering**: Comments filtered for SIP relevance (threshold TBD).
7. **Tagging**: SIP behavior tags applied per `codebook.yaml` (start/continue/pause/reduce/stop).
8. **Validation**: Tag fields validated against codebook constraints; provenance verified.
9. **Export**: Validated records exported to `data/export/` for review.
10. **Human review**: Reviewers approve/reject/request revision per record. Approved records enter Golden Dataset (`data/manual/`).

---

## Quota safeguards

| Safeguard | Description |
|-----------|-------------|
| Max videos | 10 (hard limit in collector) |
| Max comments per video | 20 (1 page of `commentThreads.list` with maxResults=20) |
| Max total comments | 200 (hard limit across all videos) |
| Quota units per pilot | ~10-30 units (well within 10,000 units/day free tier) |
| No `search.list` | Video IDs manually selected; no video discovery API calls |
| Usage tracking | The YouTube Data API does not provide an endpoint to query remaining quota. The collector tracks its own usage (units consumed per call, logged with timestamps) and stops before a configured local budget is reached. Actual usage can be cross-checked manually in the Google Cloud Console. |
| Comments disabled | If a video has comments disabled (403 `commentsDisabled`), skip that video, log the video ID and error, and continue with the next video |
| Stop on error | Stop collection immediately on authentication errors (invalid, missing, or restricted API key) or exhausted quota (403 `quotaExceeded` / `dailyLimitExceeded`) |
| Request pacing | Collector spaces requests to avoid bursts |

---

## Confirmed terms vs unresolved questions

### Confirmed (from official documentation)

- YouTube Data API v3 `commentThreads.list` is officially documented and publicly available
- API key authentication is sufficient for public comment access (no OAuth required)
- 10,000 units/day free quota; `commentThreads.list` costs 1 unit per call
- Manual video IDs can be used without `search.list`
- Commercial use is not explicitly prohibited by the YouTube API Services ToS sections reviewed (this does **not** confirm it is permitted — see unresolved items)
- API Data ownership remains with YouTube; developer has no ownership rights (§16.1)
- Upon termination, all API Data must be deleted (§24.3)

### Unresolved / requires user decision

- **CRITICAL:** How to comply with the 30-day delete/refresh limit on comment text (Developer Policies §III.E.4.d), and whether SIP tags or aggregated findings count as derived data or metrics under §III.E.4.h
- Whether the permanent Golden Dataset can retain any YouTube API Data under the applicable terms
- Whether our proposed commercial use is permitted (requires policy verification)
- Whether sending YouTube comment data to an external AI provider (NVIDIA) is permitted (requires policy verification)
- Whether YouTube API ToS compliance is acceptable for this commercial research product
- Whether the user will create a Google Cloud project and API key
- Whether 10 videos × 200 comments is sufficient for meaningful research
- Whether a privacy policy is needed (YouTube ToS §7 requires one if handling user data), and what it must disclose about external AI processing — must be assessed before collection
- Whether comment language coverage (English/Hindi/regional languages) is adequate
- Whether selection bias (manually selected videos) is acceptable for the research goals

---

## Google Cloud Console setup steps (user performs manually)

The following steps are performed by the user. No code changes or API calls are made by the project.

1. **Create a Google Account** (if not already available) at https://accounts.google.com/
2. **Create a Google Cloud project**:
   - Go to https://console.cloud.google.com/
   - Click the project dropdown → "New Project"
   - Enter a project name (e.g., "sip-discovery-engine") and click "Create"
3. **Enable YouTube Data API v3**:
   - In the Cloud Console, go to "APIs & Services" → "Library"
   - Search for "YouTube Data API v3" and click on it
   - Click "Enable"
4. **Create API key credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create credentials" → "API key"
   - Copy the generated API key (it will not be shown again)
   - **Do not paste this key into any source file or commit it to Git**
5. **Restrict the API key** (recommended for security):
   - In the Credentials page, click on the newly created API key
   - Under "Key restriction", select "API key restrictions" → "YouTube Data API v3"
   - Optionally add HTTP referrer restrictions for additional security
   - Click "Save"
6. **Store the API key securely**:
   - Create a `.env` file in the project root (gitignored)
   - Add: `YOUTUBE_API_KEY=your_api_key_here`
   - Never commit `.env` to Git
   - The collector will read this key from the environment variable at runtime

### Why API key restriction matters

- Unrestricted API keys can be abused if exposed, leading to quota exhaustion or unauthorized charges
- Restricting to "YouTube Data API v3" ensures the key only works for that specific API
- The `.env` file is gitignored (see `.gitignore`) and never committed to version control
- The `config.yaml` file does not contain any API key values — only the provider name, model ID, and base URL


## Alternative research approaches (require evaluation)

The following approaches are proposed as alternatives or complements to API-based collection. **None is approved.** Each requires evaluation of cost, licensing or consent terms, privacy obligations, permitted AI processing, retention limits, and provenance before use.

| Approach | Description | Must be evaluated before use |
|----------|-------------|------------------------------|
| Licensed datasets | Obtain SIP/investor discussion or survey data from a provider under a written licence | Licence scope (commercial use, AI processing, retention, redistribution); cost vs ₹0 budget; provenance and collection method of the provider's data |
| Voluntary investor surveys | Collect structured and open-ended responses directly from investors who choose to participate | Informed consent wording; privacy policy and data-protection obligations (including India's DPDP Act); consent to AI processing; retention and deletion; sampling bias |
| Consent-based interviews | Conduct interviews with investors who give explicit consent to recording, transcription, and analysis | Written consent covering storage, AI processing, and quotation; anonymisation; retention and deletion; interviewer bias; effort per interview |

Data from these approaches must carry the same provenance fields (source reference, collection timestamp, stable record ID) and must not be fabricated or paraphrased as verbatim evidence.

## Manual fallback procedures

If automated access is not approved for any source:

1. Manually copy individual public posts/reviews/comments into `data/manual/` as Golden Dataset candidates.
2. Each manual entry must carry: source URL, collection timestamp, stable record ID, and the verbatim text.
3. Manual entries are human-labeled by default and can enter the Golden Dataset directly upon reviewer approval.
4. Manual fallback does not scale and is suitable only for small validation sets (tens of records, not thousands).

## Next decision required

Given the findings above, the viable source options within the ₹0 budget are:

1. **YouTube** (CONDITIONAL GO — approval PENDING) — Official free API available; manual video selection avoids search quota. Commercial use and external AI processing require policy verification; comment text cannot be stored beyond 30 days (§III.E.4.d) and the derived-data question (§III.E.4.h) is unresolved. Requires these verifications, the privacy/AI-processing assessment, Google Cloud project setup, API key creation, and user approval.
2. **Reddit** (BLOCKED) — Not available for pilot collection under current terms. Reddit explicitly prohibits commercial use without written contract and prohibits using Reddit data for model training without explicit consent. **BLOCKED pending explicit authorization from Reddit and clarification of commercial use, research use, AI processing, and data retention.**
3. **Alternative research approaches** — licensed datasets, voluntary investor surveys, or consent-based interviews (see "Alternative research approaches"); each requires evaluation and approval.
4. **No source** — if none of the above is acceptable, no collection can proceed within the ₹0 budget.

Google Play Store reviews of third-party investment apps — including Groww (com.nextbillion.groww) — are **not a viable source** under any condition within the current constraints (the official API is unavailable for apps we do not manage, and scraping is not recommended as a workaround). Groww is specifically assessed as **unavailable (NO-GO)**.

You must decide:
- Whether YouTube's Data API v3 terms, quota limits, and data deletion requirements (ToS §24.3 and the Developer Policies §III.E.4.d 30-day limit) are acceptable for this product, given that comment text cannot be retained beyond 30 days (§III.E.4.d).
- Whether to evaluate licensed datasets, voluntary surveys, or consent-based interviews.
- Whether to approve YouTube for pilot collection (max 10 videos, 200 comments), or to proceed with no automated collection and rely solely on manual fallback (tens of records maximum).

YouTube approval remains PENDING until the retention requirement, commercial use, and external AI processing are verified and the privacy assessment is complete. Only after those items are resolved and you approve YouTube can Stage 3 (pilot collection) begin within the explicit limits above. Reddit remains BLOCKED pending explicit authorization from Reddit and clarification of commercial use, research use, AI processing, and data retention.
