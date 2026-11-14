# Case File #001: on-chain forensic audit of the @hive3 account cluster

This repository contains the public data behind *"Case File #001: The Arithmetic of Pressure"*, an on-chain audit of the votes, trails and reputation changes around the @hive3 account cluster, 12 Oct to 14 Nov 2026.

- `REPORT.md`: the full report
- `data/*.csv`: the tables used in the report
- `sql/queries.sql`: every query exactly as it was run, with the time it was run and the number of rows returned
- `charts/`: the two charts in the report (SVG)
- `SHA256SUMS.txt`: SHA-256 checksum of every file in this repository

**Source:** all the data come from the public Hive blockchain, read from HAFSQL (`hafsql-sql.mahdiyari.info`, database `haf_block_log`, public read-only login `hafsql_public` / `hafsql_public`). Anyone can rerun the queries in `sql/queries.sql` and compare the results.

**Note:** results run later can differ slightly, because votes and reputations keep changing on-chain. A few comment rows that only mention unrelated third-party accounts are not included.

**Check the files:** run `sha256sum -c SHA256SUMS.txt`.

Data extraction and drafting were AI-assisted; a human reviewed and verified the results.
