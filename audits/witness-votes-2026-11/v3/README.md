# v3: witness ranking vs. signed activity (19 Nov 2026, ~22:20 UTC)

Top 100 enabled witnesses, ranked again without the votes (direct and via proxy) of accounts that signed no operation themselves for 6 months, 1, 2, 3, 4 or 5 years.

- `witness_ranking_signed_activity_top100.csv`: full ranking for all 100 witnesses and every filter
- Script: [`witness-activity.js`](../../../witness-activity.js) (v3, signed-activity filter) in the repo root, run with `node witness-activity.js 100 hive3` (about 11 minutes on public HAFSQL)

Activity = last operation signed and paid by the account itself (`transacting_account_id = account_id` in HAF). Virtual operations, `claim_reward_balance`, `feed_publish` and Hive-Engine auto-claims are not counted. The base of votes does not apply the HF25 one-year expiry.

Data extraction and drafting were AI-assisted; a human reviewed the results.
