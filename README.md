# 🐝 BeeCounter

**Open source Hive statistics bot** by [@hive3](https://peakd.com/@hive3) · *The Hive Tree* 🌳

BeeCounter counts the honey on [Hive](https://hive.io): who fed whom, how rewards are spread, where every new HIVE goes. It publishes its reports as [@beecounter](https://peakd.com/@beecounter).

> 🧩 **Open source (MIT) and AI-generated.** This code was written with an AI (Claude, by Anthropic) and reviewed by a human. Everything is public so anyone can check the numbers, run the bot, fork it or keep it alive if its maintainer can't.

## 🍯 Reports

| Report | When | What it shows |
|---|---|---|
| **Monthly Ledger** | 2nd of the month, 04:00 UTC | where every new HIVE went: inflation split (content, HP stakers, witnesses, DHF), HBD↔HIVE conversions, HBD interest, DHF spending and where the funded proposals' money goes (DHF Watch), plus the full content analysis of the posts paid in the month: payout distribution, honey curve, top voters, vote map, beneficiaries, downvotes, communities |

BeeCounter publishes **one report a month** (no daily posts). Bot rules: **one post per report, no votes, no comments**, and **100% of the rewards are burned** (beneficiary `@null`).

## 🔬 Data

All data comes from the public **[HAFSQL](https://hafsql.mahdiyari.info)** database by @mahdiyari (user/password `hafsql_public`), so no public API node is hammered. Images are uploaded to `images.hive.blog`.

**Checked against the blockchain, every month:**
- `verify.py` re-reads random blocks of the month and the top posts straight from Hive nodes and compares them with HAFSQL; the result is written in the post.
- `supply_snapshot.py` saves the HIVE/HBD supply from our **own Hive node** every day at 00:00 UTC; the Ledger compares the change between the 1st of two months with the database figure.

## 📦 Files

| File | Role |
|---|---|
| `collect.py` | posts created in a date range + all their votes → statistics JSON |
| `inflation.py` | operations of a month (rewards, witnesses, DHF, HBD, conversions) → JSON |
| `render.py` | charts + Markdown for the content reports |
| `render_inflation.py` | charts + Markdown for the money flows |
| `dhf_watch.py`, `render_dhf.py` | DHF Watch: where the funded proposals' money flows |
| `compose_ledger.py` | merges everything into the Monthly Ledger |
| `verify.py` | sample check of HAFSQL against the blockchain |
| `supply_snapshot.py`, `install_snapshot_timer.sh` | daily supply snapshot from your own hived node |
| `publish.js` | uploads images and broadcasts the post (`@hiveio/dhive`) |
| `monthly.sh` | the monthly job run by the systemd timer |
| `approve.sh` | publishes a draft after a human check |
| `notify.sh` | sends the draft preview (HTML) to a phone via [ntfy](https://ntfy.sh) |
| `lib.sh`, `secure.sh` | load / store the posting key encrypted with `systemd-creds` |
| `setup.sh`, `update_timers.sh` | installation helpers |

## 🛠️ Install (Ubuntu 24.04)

```bash
git clone https://github.com/hiveb3/beecounter /root/beecounter && cd /root/beecounter
bash setup.sh          # Python + Node dependencies
bash secure.sh         # paste the bot's POSTING key: stored encrypted, timers installed
systemctl disable --now beecounter-daily.timer 2>/dev/null   # monthly only
bash install_snapshot_timer.sh   # optional: needs your own hived node (default http://127.0.0.1:8091)
echo "AUTO_PUBLISH=0" >> .env                                  # 0 = drafts only, 1 = publish automatically
echo "NTFY_TOPIC=beecounter-$(openssl rand -hex 8)" >> .env    # optional phone notifications
./monthly.sh 2026-10   # test: creates a draft in out/ledger-2026-10/
```

Change the account name in `publish.js` (`ACCOUNT`) if you run your own copy. Use **only a posting key**, never the active or owner key. An optional `avatar.png` (512×512) is placed on the covers.

## 📜 License

MIT, see `LICENSE`. Built with love 💛 for every bee in the Hive. 🐝🌼🍯
