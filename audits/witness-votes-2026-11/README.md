# Witness votes and account activity on Hive (19 Nov 2026)

Public data behind the BeeCounter report and the bz3 case file on witness votes and inactive accounts.

- `data/stake_by_activity.csv`: how much of the stake behind valid witness votes belongs to accounts that have been silent for 6 months, 1, 2 or 5 years
- `data/witness_ranking_top150.csv`: on-chain rank of the top 150 witnesses and the rank each would have if that silent stake were left out
- `sql/queries.sql`: every query exactly as it was run, with time and row count
- `SHA256SUMS.txt`: checksum of every file (`sha256sum -c SHA256SUMS.txt`)

**Source:** public Hive blockchain, read from HAFSQL (`hafsql-sql.mahdiyari.info`, database `haf_block_log`, public read-only login `hafsql_public` / `hafsql_public`) and the public Hive API. Snapshot: block 111,809,727, 19 Nov 2026 21:23 UTC.

**Check:** the vote totals rebuilt from HAFSQL match the on-chain totals within about 1% for every top-20 witness (the gap comes from delayed votes after recent power-ups, which are not modelled).

**Limits:** "activity" is measured from posts, comments, content votes, account updates and governance actions. Wallet-only actions (transfers, power-ups) are not counted, so a few wallet-only users may be labelled silent.

Data extraction and drafting were AI-assisted; a human reviewed the results. Open source (MIT).
