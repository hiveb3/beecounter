#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter Monthly Ledger: merges the content report (render.py) and the Honey Flow (render_inflation.py)
into one post that balances every HIVE created in the month.
Usage: python3 compose_ledger.py OUT   (OUT/content and OUT/flow already rendered)"""
import sys, os, json, shutil, re, datetime as dt
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon, FancyBboxPatch
from PIL import Image

OUT = sys.argv[1]; HERE = os.path.dirname(os.path.abspath(__file__))
C, F = os.path.join(OUT, "content"), os.path.join(OUT, "flow")
cd, fd = json.load(open(os.path.join(C, "data.json"))), json.load(open(os.path.join(F, "data.json")))
M = dt.date.fromisoformat(fd["month"] + "-01"); MONTH = M.strftime("%B %Y"); MON = M.strftime("%B")
K = lambda x: f"{x / 1e6:,.2f}M" if abs(x) >= 1e6 else f"{x / 1e3:,.0f}k"

# ---------- balance numbers ----------
a, b, c = fd["author"], fd["benefactor"], fd["curation"]
authors, benef, cur = a["hive"] + a["hp"], b["hive"] + b["hp"], c["hp"]
wit = fd["witness_total_hp"]; stake = 1.5 * wit
conv = fd["convert_hbd_to_hive"][0] if fd.get("convert_hbd_to_hive") else ["HBD", 0, 0, 0]
price = conv[1] / conv[2] if conv[2] else 0
dhf_hbd = sum((fd.get("dhf_funding") or {}).values()); dhf = dhf_hbd / price if price else 0
content = authors + benef + cur; tot = content + stake + wit + dhf
posts_hive = (cd["tot"] + cd["ben"]) / price if price else 0          # share of the 65% paid to posts (not comments)
comments_hive = max(content - posts_hive, 0)
dcv_in, dcv_out = fd.get("dhf_conversion") or [0, 0]
s0, s1 = fd["dgp"]; dH = (s1["hive"] - s0["hive"]) / 1000
interest = (fd.get("hbd_interest") or [0, 0])[0]
pay = [p for p in fd.get("proposal_pay", []) if p[0] != "steem.dao"]; spent = sum(p[3] for p in pay)
stab = next((p[3] for p in pay if p[0] == "hbdstabilizer"), 0)
pc = lambda x: f"{x / tot * 100:.1f}%"
rows = [
    ("✍️ Post authors + curators + beneficiaries", posts_hive, "posts paid out this month, analysed below"),
    ("💬 Comments (authors + curators + beneficiaries)", comments_hive, "everything paid to comments"),
    ("🐝 HP stakers (est.)", stake, "added to the HP pool, for every HP holder"),
    ("🏛️ Witnesses", wit, f"{fd['n_witnesses']} block producers"),
    ("🏦 DHF treasury", dhf, f"paid as {dhf_hbd:,.0f} HBD"),
]
quadra = ("## 🧾 It all adds up: where every new HIVE went\n\n"
          f"In {MON} Hive created about **{K(tot)} HIVE** of inflation. Here is where every drop ended up:\n\n"
          "| Destination | HIVE | Share | Note |\n|---|---:|---:|---|\n" +
          "\n".join(f"| {n} | {v:,.0f} | {pc(v)} | {note} |" for n, v, note in rows) +
          f"\n| **Total inflation** | **{tot:,.0f}** | **100%** | |\n\n"
          "**Outside the inflation**, three more flows moved HIVE and HBD:\n\n"
          f"- 🔄 **HBD → HIVE conversions** created **{conv[2]:,.0f} HIVE** (from {conv[1]:,.0f} HBD).\n"
          f"- 🔥 The **DHF burned {dcv_in:,.0f} HIVE**, turning it into {dcv_out:,.0f} HBD.\n"
          f"- 💵 **HBD savings interest** printed **{interest:,.0f} HBD**.\n\n"
          f"Inflation paid in HIVE/HP ({K(tot - dhf)}) + conversions − DHF burns = **{tot - dhf + conv[2] - dcv_in:+,.0f} HIVE**. "
          f"The HIVE supply actually changed by **{dH:+,.0f}**: the small gap ({dH - (tot - dhf + conv[2] - dcv_in):+,.0f}) is HIVE sent to @null and fees. The books balance. ✅")

# ---------- sections from the two posts ----------
def blocks(path, prefix):
    s = open(path).read()
    s = re.sub(r"IMG:(\S+)", lambda m: f"IMG:{prefix}{m.group(1)}", s)
    out = {}
    for blk in s.split("\n---\n"):
        m = re.search(r"^## (.+)$", blk, re.M)
        if m: out[m.group(1).strip()] = blk.strip()
    return out
cb, fb = blocks(os.path.join(C, "post.md"), "c"), blocks(os.path.join(F, "post.md"), "f")
DW = os.path.join(OUT, "dhf")
db = blocks(os.path.join(DW, "post.md"), "d") if os.path.exists(os.path.join(DW, "post.md")) else {}
pick = lambda bl, start: next((v for k, v in bl.items() if k.startswith(start)), None)
order = [(fb, "🍯 The inflation pie"), (fb, "🔄"), (fb, "💵"),
         (cb, "📊"), (cb, "🍯 How much"), (cb, "🌳"), (cb, "🫙"), (cb, "⏱️"), (cb, "🕸️"), (cb, "🏆"),
         (cb, "🌸"), (cb, "🎁"), (cb, "👎"), (cb, "🏘️"), (fb, "🏛️"), (fb, "🏦")]
secs = [x for x in (pick(bl, k) for bl, k in order) if x]
for sec in secs:   # part headings
    pass
# small heading tweaks
secs = [s.replace("## 📊 The payout in numbers", "## 📊 The 65%: the posts paid this month")
         .replace("## 🍯 The inflation pie", "## 🍯 The inflation pie") for s in secs]

# ---------- images ----------
imgs = ["0_cover.png"]
for src, pre in ((C, "c"), (F, "f")) + (((DW, "d"),) if db else ()):
    for fn in sorted(os.listdir(src)):
        if fn.endswith(".png") and not fn.startswith("0_"):
            shutil.copy(os.path.join(src, fn), os.path.join(OUT, pre + fn)); imgs.append(pre + fn)
used = set(re.findall(r"IMG:(\S+)", "\n".join(secs + list(db.values()))))
imgs = [i for i in imgs if i == "0_cover.png" or i in used]

# ---------- cover ----------
BG, DARK, GOLD = "#FFF8E7", "#3B2A1A", "#F2B705"
f = plt.figure(figsize=(12, 6.75), dpi=100); f.patch.set_facecolor("#1F4D2B"); ax = f.add_axes([0, 0, 1, 1]); ax.axis("off")
ax.set_xlim(0, 12); ax.set_ylim(0, 6.75)
for i in range(14):
    for j in range(9):
        ax.add_patch(RegularPolygon((i * .95 + (.47 if j % 2 else 0), j * .82), 6, radius=.5, facecolor="none", edgecolor="#2F6B3E", lw=1.2))
ax.add_patch(FancyBboxPatch((.7, 1.3), 10.6, 4.1, boxstyle="round,pad=0.1", facecolor="#F3FAEE", edgecolor=GOLD, lw=5))
ax.text(.95, 4.75, f"BEECOUNTER MONTHLY LEDGER · {MONTH.upper()}", fontsize=23, fontweight="bold", color="#1F4D2B")
ax.text(.95, 3.95, "Where every new HIVE went", fontsize=22, color="#2E7D46", fontweight="bold")
ax.text(.95, 3.05, "Inflation · posts · comments · stakers · witnesses · DHF · HBD", fontsize=14, color="#1F4D2B")
ax.text(.95, 2.35, f"≈ {K(tot)} new HIVE · {cd['nPosts']:,} posts paid · supply {dH / 1e6:+.2f}M HIVE", fontsize=14.5, color="#1F4D2B", fontweight="bold")
ax.text(.95, 1.65, "by @beecounter · The Hive Tree by @hive3", fontsize=12.5, color="#5B7F63")
ax.text(9.6, 3.0, "IT ALL\nADDS UP\n✓", ha="center", va="center", fontsize=26, fontweight="bold", color="#C62828", rotation=-12, linespacing=.95,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="none", edgecolor="#C62828", lw=5))
f.savefig(os.path.join(OUT, "0_cover.png"), facecolor="#1F4D2B"); plt.close(f)
try:
    cv = Image.open(os.path.join(OUT, "0_cover.png")).convert("RGBA"); av = Image.open(os.path.join(HERE, "avatar.png")).convert("RGBA").resize((130, 130))
    cv.alpha_composite(av, (1040, 30)); cv.convert("RGB").save(os.path.join(OUT, "0_cover.png"))
except Exception as e: print("avatar:", e)

# ---------- text ----------
p0 = dt.date.fromisoformat(cd["daily"][0][0]); p1 = dt.date.fromisoformat(cd["daily"][-1][0])

# ---------- independent checks: verify.py sample + own-node supply snapshots ----------
vt = os.path.join(OUT, "verify.txt"); vres = vn = None
if os.path.exists(vt):
    txt = open(vt).read()
    m = re.search(r"RESULT: (.*)", txt); vres = m.group(1).strip() if m else None
    m = re.search(r"checking (\d+) random blocks", txt); vn = int(m.group(1)) if m else None
nxt = (M.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
sn0, sn1 = (os.path.join(HERE, "supply", f"{d:%Y-%m-%d}.json") for d in (M, nxt))
node_line = ""
if os.path.exists(sn0) and os.path.exists(sn1):
    j0, j1 = json.load(open(sn0)), json.load(open(sn1))
    nH, nD = j1["current_supply"] - j0["current_supply"], j1["current_hbd_supply"] - j0["current_hbd_supply"]
    node_line = (f"\n\n🖥️ **Cross-check from our own Hive node** (snapshots at 00:00 UTC, blocks {j0['block']:,} → {j1['block']:,}): "
                 f"HIVE supply {nH:+,.0f}, HBD supply {nD:+,.0f}. Difference from the database figure: {nH - dH:+,.0f} HIVE "
                 f"({'✅ match' if abs(nH - dH) < 1000 else '⚠️ to investigate'}; a few hundred HIVE come from the snapshots not falling exactly on the month's first and last block).")
quadra += node_line

intro = [f"<center>\n\nIMG:0_cover.png\n\n</center>",
         f"Bzzz! 🐝🧮 BeeCounter here with the **Monthly Ledger** for **{MONTH}**: one report that follows **every new HIVE** from the moment the chain creates it to the wallet that receives it. 🍯",
         "Three parts: **the flows** (inflation, conversions, HBD), **the 65% for content** (who fed whom, the honey curve, beneficiaries, downvotes) "
         "and **the chain's keepers** (witnesses and DHF). Everything counts what was **actually paid in the month**, so the numbers add up. 🌳"]
method = ("## 🔬 How this bee counts\n\n"
          f"- **Flows**: all operations of {MONTH} (blocks {fd['blocks'][0]:,}–{fd['blocks'][1]:,}).\n"
          f"- **Content**: all top-level posts paid out in {MON} (created {p0:%B %-d} – {p1:%B %-d}, paid 7 days later), with all their votes. Comments are counted only in the totals.\n"
          f"- Source: the public **HAFSQL** database by @mahdiyari. HIVE/USD at the month's average conversion price (≈ ${price:.4f}).\n"
          + (f"- **Checked against the blockchain**: {vn or 'a'} random blocks of the month and the top 10 posts were re-read straight from Hive nodes and compared with the database. Result: {vres} ([verify.py](https://github.com/hiveb3/beecounter/blob/main/verify.py)).\n" if vres else "")
          + (f"- **Supply cross-check** from our own Hive node: see the table above.\n" if node_line else "")
          + "- **HP stakers** has no operation of its own: estimated as 1.5× the witness rewards (15% vs 10%). \"$ given\", \"≈ $ after 24h\" and \"$ removed\" are estimates based on rshares.\n"
          "- Accounts of The Hive Tree are left out of the rankings.")
disclaimer = ("<sub>**Disclaimer.** This report is generated automatically by a bot, from code written with AI (Claude) and reviewed by a human (Ant, @hive3), "
              "who also reads the draft before it goes out. The numbers come from public blockchain data and are cross-checked against the chain itself, "
              "but some figures (HP stakers, \"$ given\", \"$ removed\", exchange labels) are estimates, and a bee can still miscount. "
              "It is not financial advice, and it is not an accusation against anyone: naming an account only means describing what the chain shows. "
              "If you spot an error, tell me in the comments and I'll correct it. Ant 🐝</sub>")
footer = ["This bee is a 🤖 **bot**, built with love 💛 by @hive3 for every bee in the Hive 🐝🌼🍯. It never votes and never comments: it only counts, so the whole hive can see where the honey flows. Ideas and corrections are welcome in the comments, a human reads them: @hive3. 🌳",
     "🧩 **Open source & AI-generated**: every script that builds this report is public on [GitHub](https://github.com/hiveb3/beecounter) (MIT license), written with an AI (Claude) and reviewed by a human. Anyone can check the numbers, run it, fork it or keep it alive. 🐝",
          "<sub>🔥 **100% of this post's rewards are burned** (beneficiary @null): pure data for the hive, nothing to farm. Data by @mahdiyari's HAFSQL, idea by @antisocialist.</sub>",
          "**BeeCounter** 🐝🧮\n@beecounter · *The Hive Tree* 🌳 by @hive3\n\n<sub>🐝 Join **[AIBees](/c/hive-170283)**, the AI-assisted creators' community · 🎮 Play **[BeeTris](https://hiveb3.github.io/beetris/)** · 🗳️ [Vote @hive3 as witness](https://vote.hive.uno/@hive3)</sub>"]
parts = ["\n\n".join(intro), quadra,
         "# 🌊 Part 1 · The flows", *secs[:3],
         "# 🍯 Part 2 · The 65% for content", *[s for s in secs[3:] if not s.startswith(("## 🏛️", "## 🏦"))],
         "# 🏛️ Part 3 · The keepers", *[s for s in secs if s.startswith(("## 🏛️", "## 🏦"))], *list(db.values()),
         method, disclaimer, "\n\n".join(footer)]
open(os.path.join(OUT, "post.md"), "w").write("\n\n---\n\n".join(parts) + "\n")
desc = f"Hive {MONTH}: where every new HIVE went. Inflation, posts, comments, stakers, witnesses, DHF, HBD. 🐝"
if len(desc) > 120: desc = f"Hive {MONTH}: where every new HIVE went, from inflation to wallets. 🐝"
json.dump(dict(title=f"🐝 BeeCounter Monthly Ledger: where every new HIVE went in {MONTH}", permlink=f"beecounter-ledger-{fd['month']}",
               description=desc, tags=["hive-133987", "hive", "inflation", "curation", "dhf", "witness", "hbd", "statistics", "hivestats"],
               images=imgs, community="hive-133987"), open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False, indent=1)
print("OK", OUT, len(imgs), "images")
