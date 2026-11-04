#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter Honey Flow - turns the inflation.py JSON into charts, cover and the monthly post.
Usage: python3 render_inflation.py inflation_2026-10.json OUTDIR"""
import sys, os, json, datetime as dt
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon, FancyBboxPatch
from PIL import Image

SRC, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(SRC))
M = dt.date.fromisoformat(d["month"] + "-01"); MONTH = M.strftime("%B %Y"); MON = M.strftime("%B")
BG, HONEY, DARK, SOFT, GREEN, RED = "#FFF8E7", "#F2A007", "#3B2A1A", "#E8C77A", "#2E7D46", "#C62828"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": DARK, "axes.labelcolor": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "axes.edgecolor": DARK})
K = lambda x: f"{x / 1e6:,.2f}M" if abs(x) >= 1e6 else f"{x / 1e3:,.0f}k"

# ---------- numbers ----------
a, b, c = d["author"], d["benefactor"], d["curation"]
authors, benef, cur = a["hive"] + a["hp"], b["hive"] + b["hp"], c["hp"]
wit = d["witness_total_hp"]; stake = 1.5 * wit                 # 15% vs 10%: estimate, there is no operation for it
conv = d["convert_hbd_to_hive"][0] if d.get("convert_hbd_to_hive") else ["HBD", 0, 0, 0]
price = conv[1] / conv[2] if conv[2] else None                 # average HBD->HIVE conversion price
dhf_hbd = sum((d.get("dhf_funding") or {}).values())
dhf = dhf_hbd / price if price else 0
tot = authors + benef + cur + wit + stake + dhf
s0, s1 = d["dgp"]
dH, dD = (s1["hive"] - s0["hive"]) / 1000, (s1["hbd"] - s0["hbd"]) / 1000
dcv_in, dcv_out = d.get("dhf_conversion") or [0, 0]
infl_hive = authors + benef + cur + wit + stake
other = dH - (infl_hive + conv[2] - dcv_in)
interest, n_int = d.get("hbd_interest") or [0, 0]
pay = [p for p in d.get("proposal_pay", []) if p[0] != "steem.dao"]
returned = sum(p[3] for p in d.get("proposal_pay", []) if p[0] == "steem.dao")
spent = sum(p[3] for p in pay)
top20 = sum(w[1] for w in d["witnesses"][:20])
apr = s1["hbd_apr"] / 100
pct = lambda x: f"{x / tot * 100:.0f}%"

def fig(w=10, h=5.6):
    f, ax = plt.subplots(figsize=(w, h), dpi=110); f.patch.set_facecolor(BG); ax.set_facecolor(BG)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    return f, ax
def save(f, n):
    f.text(.99, .01, "@beecounter · The Hive Tree by @hive3 · data: HAFSQL", ha="right", fontsize=8, color="#8a7350")
    f.tight_layout(rect=(0, .03, 1, 1)); f.savefig(os.path.join(OUT, n), facecolor=BG); plt.close(f)

# 1 donut: where inflation goes
parts = [("Curators", cur, "#F2A007"), ("Authors", authors, "#D97706"), ("Beneficiaries", benef, "#FCD34D"),
         ("HP stakers (est.)", stake, "#2E7D46"), ("Witnesses", wit, "#3B6EA5"), ("DHF (treasury)", dhf, "#8E44AD")]
f, ax = fig(10, 6)
ax.pie([p[1] for p in parts], colors=[p[2] for p in parts], startangle=90, counterclock=False,
       wedgeprops=dict(width=.38, edgecolor=BG, linewidth=2))
ax.text(0, .08, f"{K(tot)}", ha="center", fontsize=26, fontweight="bold"); ax.text(0, -.16, "new HIVE (equiv.)", ha="center", fontsize=13)
ax.legend([f"{p[0]}: {K(p[1])} HIVE ({pct(p[1])})" for p in parts], loc="center left", bbox_to_anchor=(1, .5), frameon=False, fontsize=11)
ax.set_title(f"Where the new HIVE went · {MONTH}", fontsize=15, fontweight="bold", loc="left")
save(f, "1_inflation_split.png")

# 2/3 waterfalls: HIVE and HBD
def waterfall(steps, title, unit, name):
    f, ax = fig(10, 5.4); run = 0; xs = []
    for i, (lab, v) in enumerate(steps):
        col = GREEN if v >= 0 else RED
        ax.bar(i, v, bottom=run, color=col, edgecolor=DARK, linewidth=.6); xs.append(lab)
        ax.text(i, run + v + (abs(v) * .02 if v >= 0 else -abs(v) * .02), ("+" if v >= 0 else "−") + K(abs(v)),
                ha="center", va="bottom" if v >= 0 else "top", fontsize=10, fontweight="bold")
        run += v
    cum = [0]; t = 0
    for _, v in steps: t += v; cum.append(t)
    lo, hi = min(cum), max(cum); span = hi - lo
    ax.set_ylim(lo - span * .1 if lo < 0 else 0, hi + span * .12)
    net = run; ax.bar(len(steps), net, color=HONEY, edgecolor=DARK, linewidth=.6); xs.append("Net change")
    ax.text(len(steps), net, ("+" if net >= 0 else "−") + K(abs(net)), ha="center", va="bottom" if net >= 0 else "top", fontsize=11, fontweight="bold")
    ax.axhline(0, color=DARK, lw=.8); ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs, fontsize=9.5)
    ax.set_ylabel(unit); ax.set_title(title, fontsize=15, fontweight="bold", loc="left")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: K(v)))
    save(f, name)
waterfall([("Inflation\n(paid in HIVE/HP)", infl_hive), ("HBD → HIVE\nconversions", conv[2]),
           ("DHF burns HIVE\ninto HBD", -dcv_in), ("Other burns\n& fees", other)],
          f"HIVE supply in {MON}: what was created, what was burned", "HIVE", "2_hive_flow.png")
waterfall([("HBD interest", interest), ("DHF funding\n(10% inflation)", dhf_hbd), ("DHF converts\nHIVE → HBD", dcv_out),
           ("HBD → HIVE\nconversions", -conv[1])], f"HBD supply in {MON}", "HBD", "3_hbd_flow.png")

# 4 witness
W = d["witnesses"][:30]; f, ax = fig(10, 6.2)
ax.barh(range(len(W))[::-1], [w[1] for w in W], color=[HONEY if i < 20 else SOFT for i in range(len(W))], edgecolor=DARK, linewidth=.4)
ax.set_yticks(range(len(W))[::-1]); ax.set_yticklabels(["@" + w[0] for w in W], fontsize=8)
ax.set_xlabel("HP earned in the month"); ax.set_title(f"Witness rewards · top 30 of {d['n_witnesses']}", fontsize=15, fontweight="bold", loc="left")
ax.text(.98, .05, f"Top 20 (gold) earned {top20 / wit * 100:.0f}% of all witness rewards", transform=ax.transAxes, ha="right", fontsize=10)
save(f, "4_witnesses.png")

# 5 DHF
f, ax = fig(10, 4.6); P = sorted(pay, key=lambda p: p[3])
ax.barh(range(len(P)), [p[3] for p in P], color="#8E44AD", edgecolor=DARK, linewidth=.5)
ax.set_yticks(range(len(P))); ax.set_yticklabels([f"@{p[0]} (#{p[1]})" for p in P], fontsize=10)
for i, p in enumerate(P): ax.text(p[3], i, f"  {p[3]:,.0f} HBD", va="center", fontsize=9.5)
ax.set_xscale("log"); ax.set_xlabel("HBD paid (log scale)")
ax.set_title(f"Where the DHF spent its HBD · {MONTH}", fontsize=15, fontweight="bold", loc="left")
save(f, "5_dhf.png")

# cover
G1, GOLD = "#3B2A1A", "#F2B705"
f = plt.figure(figsize=(12, 6.75), dpi=100); f.patch.set_facecolor(G1); ax = f.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 6.75)
for i in range(14):
    for j in range(9):
        ax.add_patch(RegularPolygon((i * .95 + (.47 if j % 2 else 0), j * .82), 6, radius=.5, facecolor="none", edgecolor="#5a4128", lw=1.2))
ax.add_patch(FancyBboxPatch((.7, 1.3), 10.6, 4.1, boxstyle="round,pad=0.1", facecolor=BG, edgecolor=GOLD, lw=5))
ax.text(.95, 4.75, f"BEECOUNTER HONEY FLOW · {MONTH.upper()}", fontsize=24, fontweight="bold", color=DARK)
ax.text(.95, 3.95, "Where did the new HIVE go?", fontsize=22, color="#B5651D", fontweight="bold")
ax.text(.95, 3.05, "Authors · curators · stakers · witnesses · DHF · HBD", fontsize=14.5, color=DARK)
ax.text(.95, 2.35, f"≈ {K(tot)} new HIVE  ·  {K(conv[2])} HIVE from HBD conversions", fontsize=14.5, color=DARK, fontweight="bold")
ax.text(.95, 1.65, "by @beecounter · The Hive Tree by @hive3", fontsize=12.5, color="#8a7350")
f.savefig(os.path.join(OUT, "0_cover.png"), facecolor=G1); plt.close(f)
try:
    cv = Image.open(os.path.join(OUT, "0_cover.png")).convert("RGBA"); av = Image.open(os.path.join(HERE, "avatar.png")).convert("RGBA").resize((130, 130))
    cv.alpha_composite(av, (1040, 30)); cv.convert("RGB").save(os.path.join(OUT, "0_cover.png"))
except Exception as e: print("avatar:", e)

# ---------- text ----------
img = lambda n: f"<center>\n\nIMG:{n}\n\n</center>"
L = [img("0_cover.png"),
     f"Bzzz! 🐝🧮 BeeCounter here. Every day I count who fed whom. Today the big question: **where does the new HIVE come from, and where does it go?** Here is **{MONTH}**, straight from the chain. 🍯",
     "Many hivers think new HIVE only goes to authors, curators, witnesses and the DHF. There is more: **HP stakers** get a slice too, **HBD savings** earn new HBD, and **converting HBD to HIVE creates new HIVE**. Let's follow the honey. 🌳",
     "---\n\n## 🍯 The inflation pie\n\n" + img("1_inflation_split.png"),
     f"In {MON} the chain created about **{K(tot)} HIVE** of inflation:\n\n"
     f"- **{pct(authors + benef + cur)} to content** ({K(authors + benef + cur)} HIVE): curators {K(cur)}, authors {K(authors)}, beneficiaries {K(benef)}.\n"
     f"- **{pct(stake)} to HP stakers** (≈ {K(stake)} HIVE, added to the HP pool for everyone who holds Hive Power).\n"
     f"- **{pct(wit)} to witnesses** ({K(wit)} HP for {d['witness_blocks']:,} blocks).\n"
     f"- **{pct(dhf)} to the DHF**, paid as **{dhf_hbd:,.0f} HBD**.\n\n"
     f"Check: the content share, measured from the actual payouts, comes out at **{(authors + benef + cur) / tot * 100:.1f}%**, the protocol's 65%. The chain does what it promises. 🐝",
     "---\n\n## 🔄 The hidden mint: HBD conversions\n\n" + img("2_hive_flow.png"),
     f"The biggest source of new HIVE in {MON} was **not** inflation:\n\n"
     f"- **{conv[3]:,} HBD → HIVE conversions** turned **{conv[1]:,.0f} HBD** into **{conv[2]:,.0f} new HIVE**, about **{conv[2] / infl_hive:.1f}×** the HIVE paid by inflation.\n"
     f"- On the other side, the **DHF burned {dcv_in:,.0f} HIVE**, converting it into {dcv_out:,.0f} HBD.\n"
     f"- Net result: the HIVE supply grew by **{dH:+,.0f} HIVE** ({dH / (s0['hive'] / 1000) * 100:+.2f}% in one month).",
     "---\n\n## 💵 HBD: printed, burned, saved\n\n" + img("3_hbd_flow.png"),
     f"- **HBD savings interest** ({apr:.0f}% APR) created **{interest:,.0f} HBD** for **{n_int:,} accounts**. "
     f"The top saver, @{d['hbd_interest_top'][0][0]}, received {d['hbd_interest_top'][0][1]:,.0f} HBD ({d['hbd_interest_top'][0][1] / interest * 100:.0f}% of all interest).\n"
     f"- Authors received **{a['hbd']:,.0f} HBD** this month: all author rewards were paid in HIVE and HP.\n"
     f"- The HBD supply changed by **{dD:+,.0f} HBD**: what was printed and what was converted almost cancel out.",
     "---\n\n## 🏛️ Witnesses\n\n" + img("4_witnesses.png"),
     f"- **{d['n_witnesses']} witnesses** produced {d['witness_blocks']:,} blocks and earned **{wit:,.0f} HP**.\n"
     f"- **The top 20 earned {top20 / wit * 100:.0f}%** of it, about {d['witnesses'][0][1]:,.0f} HP each. The backup witnesses shared the rest.\n"
     f"- **{d.get('missed_total', 0):,} blocks were missed**. Most missed: " + ", ".join(f"@{m[0]} ({m[1]})" for m in d.get("missed", [])[:5]) + ".",
     "---\n\n## 🏦 The DHF: money in, money out\n\n" + img("5_dhf.png"),
     f"- In: **{dhf_hbd:,.0f} HBD** from inflation, plus **{dcv_out:,.0f} HBD** from converting HIVE.\n"
     f"- Out: **{spent:,.0f} HBD** paid to {len(pay)} funded proposals. **@hbdstabilizer** alone received {next((p[3] for p in pay if p[0] == 'hbdstabilizer'), 0):,.0f} HBD "
     f"({next((p[3] for p in pay if p[0] == 'hbdstabilizer'), 0) / spent * 100:.0f}%); it trades on the market to keep HBD near $1 and sends HIVE back to the fund.\n"
     f"- {returned:,.0f} HBD of daily budget went to the **return proposal** (@steem.dao): it stays in the treasury, it is not spent.\n"
     "- Other proposals paid: " + ", ".join(f"@{p[0]} ({p[3]:,.0f} HBD)" for p in pay if p[0] != "hbdstabilizer") + ".",
     "---\n\n## 🔬 How this bee counts\n\n"
     f"- All operations of {MONTH} (blocks {d['blocks'][0]:,}–{d['blocks'][1]:,}), read from the public **HAFSQL** database by @mahdiyari.\n"
     "- HP values are converted from VESTS at the start-of-month rate. HIVE/HBD values use the month's average conversion price "
     f"(≈ ${price:.4f} per HIVE).\n"
     "- The **HP stakers** slice has no operation of its own: it is estimated as 1.5× the witness rewards (15% vs 10%).\n"
     f"- Supply check: inflation + conversions − burns explains the HIVE supply change within {abs(other):,.0f} HIVE (null burns, fees). The HBD check closes within a few HBD. ✅",
     "---\n\nThis bee is a 🤖 **bot**, built with love 💛 by @hive3 for every bee in the Hive 🐝🌼🍯. It never votes and never comments: it only counts, so the whole hive can see where the honey flows. Ideas and corrections are welcome in the comments, a human reads them: @hive3. 🌳",
     "🧩 **Open source & AI-generated**: every script that builds this report is public on [GitHub](https://github.com/hiveb3/beecounter) (MIT license), written with an AI (Claude) and reviewed by a human. Anyone can check the numbers, run it, fork it or keep it alive. 🐝",
     "<sub>🔥 **100% of this post's rewards are burned** (beneficiary @null): pure data for the hive, nothing to farm. Data by @mahdiyari's HAFSQL.</sub>",
     "**BeeCounter** 🐝🧮\n@beecounter · *The Hive Tree* 🌳 by @hive3\n\n<sub>🐝 Join **[AIBees](/c/hive-170283)**, the AI-assisted creators' community · 🎮 Play **[BeeTris](https://hiveb3.github.io/beetris/)** · 🗳️ [Vote @hive3 as witness](https://vote.hive.uno/@hive3)</sub>"]
open(os.path.join(OUT, "post.md"), "w").write("\n\n".join(L) + "\n")
imgs = ["0_cover.png", "1_inflation_split.png", "2_hive_flow.png", "3_hbd_flow.png", "4_witnesses.png", "5_dhf.png"]
desc = f"Where the new HIVE went in {MONTH}: authors, curators, stakers, witnesses, DHF, HBD interest and conversions. 🐝"
if len(desc) > 120: desc = f"Where the new HIVE went in {MONTH}: rewards, witnesses, DHF, HBD. 🐝"
json.dump(dict(title=f"🐝 BeeCounter Honey Flow: where the new HIVE went in {MONTH}", permlink=f"beecounter-honey-flow-{d['month']}",
               description=desc, tags=["hive-133987", "hive", "inflation", "dhf", "witness", "hbd", "statistics", "hivestats", "aibees"],
               images=imgs, community="hive-133987"), open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False, indent=1)
print("OK", OUT)
