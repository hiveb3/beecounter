# 🐝 BeeCounter

**Open source Hive statistics bot** by [@hive3](https://peakd.com/@hive3) · *The Hive Tree* 🌳

BeeCounter counts the honey on [Hive](https://hive.io): who fed whom, how rewards are spread, where every new HIVE goes. It publishes its reports as [@beecounter](https://peakd.com/@beecounter).

> 🧩 **Open source (MIT) and AI-generated.** This code was written with an AI (Claude, by Anthropic) and reviewed by a human. Everything is public so anyone can check the numbers, run the bot, fork it or keep it alive if its maintainer can't.

## 🍯 Reports

| Report | When | What it shows |
|---|---|---|
| **Daily** | every day, 01:30 UTC | posts paid out the day before: payout distribution, honey curve, top voters, day one vs payout, vote map, beneficiaries, downvotes, communities |
| **Monthly Ledger** | 2nd of the month, 04:00 UTC | where every new HIVE went: inflation split (content, HP stakers, witnesses, DHF), HBD↔HIVE conversions, HBD interest, DHF spending, plus the full content analysis of the posts paid in the month |

Bot rules: **one post per report, no votes, no comments**, and **100% of the rewards are burned** (beneficiary `@null`).

## 🔬 Data

All data comes from the public **[HAFSQL](https://hafsql.mahdiyari.info)** database by @mahdiyari (user/password `hafsql_public`), so no public API node is hammered. Images are uploaded to `images.hive.blog`.

## 📦 Files

| File | Role |
|---|---|
| `collect.py` | posts created in a date range + all their votes → statistics JSON |
| `inflation.py` | operations of a month (rewards, witnesses, DHF, HBD, conversions) → JSON |
| `render.py` | charts + Markdown for the content reports |
| `render_inflation.py` | charts + Markdown for the money flows |
| `compose_ledger.py` | merges both into the Monthly Ledger |
| `publish.js` | uploads images and broadcasts the post (`@hiveio/dhive`) |
| `daily.sh`, `monthly.sh` | the jobs run by the systemd timers |
| `approve.sh` | publishes a draft after a human check |
| `notify.sh` | sends the draft preview (HTML) to a phone via [ntfy](https://ntfy.sh) |
| `lib.sh`, `secure.sh` | load / store the posting key encrypted with `systemd-creds` |
| `setup.sh`, `update_timers.sh` | installation helpers |

## 🛠️ Install (Ubuntu 24.04)

```bash
git clone https://github.com/hiveb3/beecounter /root/beecounter && cd /root/beecounter
bash setup.sh          # Python + Node dependencies
bash secure.sh         # paste the bot's POSTING key: stored encrypted, timers installed
echo "AUTO_PUBLISH=0" >> .env                                  # 0 = drafts only, 1 = publish automatically
echo "NTFY_TOPIC=beecounter-$(openssl rand -hex 8)" >> .env    # optional phone notifications
./daily.sh 2026-10-27  # test: creates a draft in out/daily-2026-10-27/
```

Change the account name in `publish.js` (`ACCOUNT`) if you run your own copy. Use **only a posting key**, never the active or owner key. An optional `avatar.png` (512×512) is placed on the covers.

## 📜 License

MIT, see `LICENSE`. Built with love 💛 for every bee in the Hive. 🐝🌼🍯
