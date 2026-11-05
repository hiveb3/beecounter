#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter DHF Watch - turns the dhf_watch.py JSON into a chart and a Markdown section.
Usage: python3 render_dhf.py dhf_2026-10.json OUTDIR [HIVE_PRICE_USD]"""
import sys, os, json, datetime as dt
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC, OUT = sys.argv[1:3]; PRICE = float(sys.argv[3]) if len(sys.argv) > 3 else 0
os.makedirs(OUT, exist_ok=True)
d = json.load(open(SRC)); MON = dt.date.fromisoformat(d["month"] + "-01").strftime("%B")
EX = {"bdhivesteem": "Binance", "deepcrypto8": "Binance", "bitgethive": "Bitget", "user.dunamu": "Upbit", "huobi-pro": "HTX",
      "gateiodeposit": "Gate.io", "mxchive": "MEXC", "probitred": "ProBit", "blocktrades": "BlockTrades", "honey-swap": "Hive-Engine"}
EX.update(d.get("exchanges", {}))
BG, DARK, PURPLE, RED, SOFT = "#FFF8E7", "#3B2A1A", "#8E44AD", "#C62828", "#E8C77A"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": DARK, "axes.labelcolor": DARK, "xtick.color": DARK, "ytick.color": DARK})
usd = lambda amt, sym: amt if sym == "HBD" else amt * PRICE

P = d["proposals"]
for p in P: p["out"] = [x for x in p.get("out", []) if usd(x[2], x[1]) >= 1 or not PRICE]   # skip dust
rows = []
for p in P:
    out = p.get("out", [])
    ex = sum(usd(x[2], x[1]) for x in out if x[0] in EX)
    fund = sum(usd(x[2], x[1]) for x in out if x[0] == "hive.fund")
    other = sum(usd(x[2], x[1]) for x in out if x[0] not in EX and x[0] != "hive.fund")
    rows.append((p, ex, fund, other))

# chart: received vs outflows by kind (HBD-equivalent)
f, ax = plt.subplots(figsize=(10, 4.8), dpi=110); f.patch.set_facecolor(BG); ax.set_facecolor(BG)
for s in ("top", "right"): ax.spines[s].set_visible(False)
crows = [r for r in rows if r[0]["receiver"] != "hbdstabilizer"]   # the stabilizer is a market maker: shown in the text
rows_all, rows = rows, crows
names = ["@" + r[0]["receiver"] for r in rows][::-1]; y = range(len(rows))
rec = [r[0]["received"] for r in rows][::-1]
ax.barh([i + .2 for i in y], rec, height=.38, color=PURPLE, label="Received from the DHF (HBD)")
left = [0] * len(rows)
for k, col, lab in ((1, RED, "Sent to exchanges"), (2, "#2E7D46", "Sent back to the DHF (hive.fund)"), (3, SOFT, "Sent to other accounts")):
    v = [r[k] for r in rows][::-1]
    ax.barh([i - .2 for i in y], v, left=left, height=.38, color=col, label=lab); left = [a + b for a, b in zip(left, v)]
ax.set_yticks(list(y)); ax.set_yticklabels(names)
ax.set_xlabel("≈ USD value" if PRICE else "HBD (HIVE flows not converted)")
ax.set_title(f"DHF Watch · {MON}: money in vs. money moved out", fontsize=14, fontweight="bold", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
f.text(.99, .01, "@beecounter · data: HAFSQL · outflows include every source, not only DHF money · @hbdstabilizer in the text", ha="right", fontsize=7.5, color="#8a7350")
f.tight_layout(rect=(0, .03, 1, 1)); f.savefig(os.path.join(OUT, "1_dhf_watch.png"), facecolor=BG); plt.close(f)

# text
rows = rows_all
L = ["## 🔍 DHF Watch: what happened to the funded accounts",
     "<center>\n\nIMG:1_dhf_watch.png\n\n</center>",
     f"For every account paid by the DHF in {MON}, here is what that account did on-chain in the same month. "
     "**Important:** an account's outflows mix DHF money with every other income it has (curation, other projects, savings), "
     "and sending funds to an exchange is often how teams pay developers and servers off-chain. These are flows, not verdicts. 🐝"]
for p, ex, fund, other in rows:
    out = sorted(p.get("out", []), key=lambda x: -usd(x[2], x[1]))[:4]
    dest = ", ".join(f"@{x[0]}{' (' + EX[x[0]] + ')' if x[0] in EX else ''} {x[2]:,.0f} {x[1]}" for x in out) or "none"
    extra = []
    if p.get("converted_hbd_to_hive"): c = p["converted_hbd_to_hive"]; extra.append(f"converted {c[0]:,.0f} HBD into {c[1]:,.0f} HIVE")
    if p.get("powered_up_hive"): extra.append(f"powered up {p['powered_up_hive']:,.0f} HIVE")
    if p.get("to_savings"): extra.append("moved to savings " + ", ".join(f"{v:,.0f} {k}" for k, v in p["to_savings"].items()))
    if p.get("market_sold"): extra.append("sold on the internal market " + ", ".join(f"{v:,.0f} {k}" for k, v in p["market_sold"].items()))
    rep = "; ".join(f"@{a}: {v['posts_in_month']} posts (last: {v['last_post']})" for a, v in p["reporting"].items())
    L.append(f"**@{p['receiver']}** (proposal #{', #'.join(map(str, p['proposals']))}) received **{p['received']:,.0f} HBD**.\n\n"
             f"- Main outflows: {dest}.\n" + (f"- Also: {'; '.join(extra)}.\n" if extra else "") +
             f"- Updates posted on Hive in {MON}: {rep}. <sub>Updates may also live on other accounts or sites.</sub>")
L.append(f"<sub>Exchange accounts are recognised from a public list in the [code](https://github.com/hiveb3/beecounter/blob/main/dhf_watch.py): "
         "corrections are welcome.</sub>")
open(os.path.join(OUT, "post.md"), "w").write("\n\n".join(L) + "\n")
print("OK", OUT)
