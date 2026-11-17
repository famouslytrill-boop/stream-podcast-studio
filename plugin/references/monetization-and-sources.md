# Money model and dated primary sources

Checked November 16, 2026, America/New_York. Platform/account eligibility, audience and real EmberBanter receipts remain unverified. Rules can change: recheck before enrollment or publishing advice. Source dates below are check dates, not publication dates.

## Disjoint receipts, explicit assumptions

`Net receipts = members × net per member + views ÷ 1000 × ad-only net RPM + sponsor net + affiliate net + tips net + other net`.

`Operating result before tax = net receipts − fixed costs − variable costs`.

Use one currency and period throughout. Every amount is creator net after the relevant platform/processor fees and refunds, or account for those refunds once as a cost. Never count a payout twice just because it appears in two dashboards. Equipment depreciation, unpaid labor and tax are outside the simple result unless explicitly costed. Actual taxes require separate treatment.

YouTube aggregate RPM can include ads, Premium, memberships and Supers. Adding separate memberships/Supers to that aggregate can double-count. Compute an **ad-only** net rate using the same relevant view denominator, or add exported disjoint source totals. Advertiser CPM is not creator earnings. Premium can go into `other_net` if it is separately measured and not included elsewhere.

The bundled CLI uses the ad-only-rate schema shown in its example. Adding disjoint exported totals is an alternative manual calculation; it is not a second CLI input schema. An optional missing profit target leaves target fields unknown while complete receipts/costs still calculate.

Conditional total members for a profit target: `ceil(max(0, costs + target profit − nonmembership net) ÷ net per member)`. Other income/costs and the per-member net are held constant. If net per member is zero and a funding gap remains, the member target is undefined. Missing inputs stay unknown.

Synthetic example only: 20 members × $3 creator net = $60; 10,000 matching views × invented $2 ad-only net RPM = $20; tips $10; other receipts assumed $0; costs $25. Modeled receipts $90; operating result $65 before tax/unpaid labor. At those same invented inputs, a $500 result would need 165 total members (145 more). These are not current platform rates, a forecast, proof of eligibility or a promise of income.

## Staged monetization

| Stage | Work to prepare | Evidence needed |
| --- | --- | --- |
| Rehearsal | Deliver a watchable session and two worthwhile clips; use existing gear | Real mic/game/party audio, legible captions, no doubled sound. |
| Repeat viewing | Consistent series, optional audience choice, honest community rules | Comparable sessions and actual return-viewing data. |
| Native support | Explain a modest benefit you can sustain, such as a monthly topic vote | The account's actual feature eligibility, fees and payout status. Don't promise expensive fulfillment. |
| Affiliate/sponsor | Recommend only a product you can honestly discuss; prepare a small media sheet | Measured audience, genuine offer terms, clear disclosure and realistic deliverables. No outreach sent by this plan. |
| Merchandise | Test demand before inventory or paid designs | Real buyer interest, unit margin, fulfillment capacity and name clearance. |

U.S. endorsements: disclose material connections with the endorsement itself; for video, disclose within the video; repeat a live-stream disclosure periodically. Use plain language such as “Sponsored” or “I earn a commission from this link.” Disclose free products where relevant. No paid relationship is claimed here.

## Platform snapshot

| Platform | Verified public rule snapshot | What it does not establish |
| --- | --- | --- |
| YouTube | In expanded-YPP regions, early access generally needs 500 subscribers, three public uploads in 90 days and either 3,000 valid public watch hours in 12 months or 3 million valid Shorts views in 90 days. Advertising share uses 1,000 subscribers and either 4,000 hours or 10 million Shorts views, plus other requirements and review. | Channel acceptance, specific feature access or income. Shorts-feed watch time is not a substitute for the long-form watch-hour route. |
| Twitch | Monetization tools were expanded to eligible streamers before Affiliate, but cash payout still requires Affiliate/Partner status. The reduced Affiliate milestones include 25 followers, four streamed hours, four distinct stream days and at least three average concurrent viewers on four distinct days within the qualification window. | That the owner's account can receive a payout, or a fixed net amount per subscription. Check the account dashboard and current rules. |
| Spotify | The Partner Program lists hosting/market requirements, three episodes, 2,000 consumption hours and 1,000 audience in the last 30 days, with application/review. | A universal per-stream payout or the owner's eligibility. |

Recommendation: choose one live home after the real device rehearsal; reuse selected clips on YouTube Shorts plus one other short-form destination. Create a podcast only from a complete audio conversation. Trying to maintain every platform at launch is a workload hypothesis, not a growth requirement. No new account or feed has been activated.

## Primary-source register

| Topic | Official source | Checked |
| --- | --- | --- |
| Recommendation signals | https://support.google.com/youtube/answer/16559650?hl=en | 2026-11-16 |
| Recommendation personalization | https://support.google.com/youtube/answer/16533387?hl=en | 2026-11-16 |
| Upload cadence and timing | https://support.google.com/youtube/answer/141805?hl=en | 2026-11-16 |
| Multiple formats and audience behavior | https://support.google.com/youtube/answer/16559651?hl=en | 2026-11-16 |
| RPM, CPM and source overlap | https://support.google.com/youtube/answer/9314357?hl=en | 2026-11-16 |
| Expanded YPP thresholds | https://support.google.com/youtube/answer/13429240?hl=en | 2026-11-16 |
| Twitch tools versus payout | https://blog.twitch.tv/en/2026/05/13/monetization-for-all/ | 2026-11-16 |
| Spotify Partner Program | https://support.spotify.com/us/creators/article/spotify-partner-program/ | 2026-11-16 |
| Endorsement disclosures | https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers | 2026-11-16 |
| Comprehensive trademark searches | https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks | 2026-11-16 |

Do not turn this table into a claim that every linked rule applies to an uninspected account. No private creator analytics, sponsor contracts, account dashboards or domain registrations were accessed in this research pass.
