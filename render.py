#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter - turns the collect.py JSON into charts, cover and Markdown post.
Usage: python3 render.py DATA.json OUTDIR FROM TO [NUMBER]
  FROM/TO = post creation days (UTC). If FROM==TO it is a daily report."""
import sys, os, json, math, random, datetime as dt, urllib.request
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, networkx as nx
from matplotlib.patches import RegularPolygon, FancyBboxPatch
from PIL import Image

SRC, OUT, FROM, TO = sys.argv[1:5]; NUM = sys.argv[5] if len(sys.argv) > 5 else ""
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(SRC)); os.makedirs(OUT, exist_ok=True)
DAILY = FROM == TO
f0, t0 = dt.date.fromisoformat(FROM), dt.date.fromisoformat(TO)
p0, p1 = f0 + dt.timedelta(days=7), t0 + dt.timedelta(days=7)
fmtd = lambda x: x.strftime("%B %-d")
PAID = f"{fmtd(p0)}, {p0.year}" if DAILY else f"{fmtd(p0)} – {fmtd(p1)}, {p1.year}"
CREATED = f"{fmtd(f0)}" if DAILY else f"{fmtd(f0)} – {fmtd(t0)}"
sh = lambda x: x.strftime("%b %-d")
PAIDS = f"{sh(p0)}, {p0.year}" if DAILY else f"{sh(p0)} – {sh(p1)}, {p1.year}"
CREATEDS = sh(f0) if DAILY else f"{sh(f0)} – {sh(t0)}"
MONTH = f0.strftime("%B %Y")
SELF = {"hive3", "beecounter"}            # The Hive Tree accounts: left out of rankings
random.seed(FROM + TO)
pick = lambda *xs: random.choice(xs)
money = lambda x: f"{x:,.2f}"
pct = lambda a, b: f"{a / b * 100:.0f}%" if b else "0%"
MIN_USD = float(os.environ.get("BEECOUNTER_MIN_USD", "1"))   # payout cutoff for the rankings (idea by @antisocialist)

# ---------- community names ----------
def community_titles(ids):
    out = {}
    for i in ids:
        try:
            req = urllib.request.Request("https://api.hive.blog", method="POST",
                  data=json.dumps({"jsonrpc": "2.0", "method": "bridge.get_community", "params": {"name": i}, "id": 1}).encode())
            r = json.load(urllib.request.urlopen(req, timeout=15)).get("result")
            out[i] = r["title"] if r else i
        except Exception:
            out[i] = i
    return out
CT = json.load(open(os.path.join(OUT, "communities.json"))) if os.path.exists(os.path.join(OUT, "communities.json")) else community_titles([c[0] for c in d["comm"][:6] if c[0].startswith("hive-")])
ctitle = lambda c: CT.get(c, c)

# ---------- chart style ----------
BG, HONEY, DARK, SOFT = "#FFF8E7", "#F2A007", "#3B2A1A", "#E8C77A"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": DARK, "axes.labelcolor": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "axes.edgecolor": DARK})
def fig(w=10, h=5.6):
    f, ax = plt.subplots(figsize=(w, h), dpi=110); f.patch.set_facecolor(BG); ax.set_facecolor(BG)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    return f, ax
def save(f, name):
    f.text(0.99, 0.01, "@beecounter · The Hive Tree by @hive3 · data: HAFSQL", ha="right", fontsize=8, color="#8a7350")
    f.tight_layout(rect=(0, .03, 1, 1)); f.savefig(os.path.join(OUT, name), facecolor=BG); plt.close(f)
IMGS = []

# 1 payout distribution
lab = ["< $0.02", "$0.02–0.50", "$0.50–1", "$1–2", "$2–5", "$5–10", "$10–25", "$25–50", "> $50"]
v = [b[1] for b in d["buckets"]]
f, ax = fig(); bars = ax.bar(lab, v, color=["#B5651D"] + [HONEY] * 8, edgecolor=DARK, linewidth=.6)
for b, x in zip(bars, v): ax.text(b.get_x() + b.get_width() / 2, x + max(v) * .01, f"{x:,}", ha="center", fontsize=9, fontweight="bold")
ax.set_title("How much did each post earn? (final payouts)", fontsize=15, fontweight="bold", loc="left")
ax.set_ylabel("posts"); ax.tick_params(axis="x", labelsize=8.5)
ax.text(.99, .95, f"{d['nPosts']:,} posts paid out {PAID}", transform=ax.transAxes, ha="right", va="top", fontsize=10)
save(f, "1_payout_distribution.png"); IMGS.append("1_payout_distribution.png")

# 2 top voters
tv = d["topVoters"][:15][::-1]
f, ax = fig(); ax.barh(range(len(tv)), [t[1] for t in tv], color=HONEY, edgecolor=DARK, linewidth=.6)
ax.set_yticks(range(len(tv))); ax.set_yticklabels(["@" + t[0] for t in tv], fontsize=10)
mx = max(t[1] for t in tv)
for i, t in enumerate(tv): ax.text(t[1] + mx * .01, i, f"${t[1]:,.0f} · {t[3]:,} authors", va="center", fontsize=9)
ax.set_xlim(0, mx * 1.3); ax.set_xlabel("≈ $ of final rewards given (estimate)")
ax.set_title("Who filled the jars? Top 15 voters", fontsize=15, fontweight="bold", loc="left")
save(f, "2_top_voters.png"); IMGS.append("2_top_voters.png")

# 3 honey curve
n = d["nAuthors"]; xs = [0] + [p[0] / n * 100 for p in d["cum"]]; ys = [0] + [p[1] for p in d["cum"]]
f, ax = fig(); ax.fill_between(xs, ys, color=SOFT, alpha=.7); ax.plot(xs, ys, color=HONEY, lw=3)
ax.plot([0, 100], [0, 100], ls="--", color="#8a7350", lw=1)
hx = d["half"] / n * 100; ax.plot([hx, hx], [0, 50], color=DARK, lw=1, ls=":"); ax.plot([0, hx], [50, 50], color=DARK, lw=1, ls=":")
ax.annotate(f"{d['half']:,} authors ({hx:.0f}%)\ntook half of the honey", xy=(hx, 50), xytext=(hx + 12, 30),
            fontsize=11, fontweight="bold", arrowprops=dict(arrowstyle="->", color=DARK))
ax.set_xlim(0, 100); ax.set_ylim(0, 102); ax.set_xlabel("% of authors (richest first)"); ax.set_ylabel("% of all rewards")
ax.set_title("The honey curve (final payouts)", fontsize=15, fontweight="bold", loc="left")
save(f, "3_honey_curve.png"); IMGS.append("3_honey_curve.png")

# 4 time: how much honey arrives within N hours
hc = [[0, 0.0]] + [[min(h + 1, 168), p] for h, p in d["hourCurve"]]
f, ax = fig(); ax.plot([h for h, _ in hc], [p for _, p in hc], color=HONEY, lw=3, marker="o", mec=DARK)
ax.fill_between([h for h, _ in hc], [p for _, p in hc], color=SOFT, alpha=.6)
for h, p in hc:
    if h in (1, 25, 73, 168): ax.annotate(f"{p:.0f}% after {h - 1 if h > 1 else 1}h" if h < 168 else "100% at payout", xy=(h, p), xytext=(h + 4, p - 9), fontsize=10, fontweight="bold")
ax.set_xticks([0, 24, 48, 72, 96, 120, 144, 168]); ax.set_xticklabels(["0", "day 1", "day 2", "day 3", "day 4", "day 5", "day 6", "day 7"])
ax.set_ylim(0, 105); ax.set_ylabel("% of the final upvote power")
ax.set_title("How fast does the honey arrive?", fontsize=15, fontweight="bold", loc="left")
save(f, "4_time_curve.png"); IMGS.append("4_time_curve.png")

# 5 vote map (radial layout)
E = [e for e in d["edges"][:46]]; G = nx.DiGraph()
for a, b, w in E: G.add_edge(a, b, w=w)
voters = {a for a, _, _ in E}; vl = sorted(voters, key=lambda u: -sum(G[u][x]["w"] for x in G.successors(u)))
pos = {u: (.38 * math.cos(2 * math.pi * i / len(vl)), .38 * math.sin(2 * math.pi * i / len(vl))) for i, u in enumerate(vl)}
au = [x for x in G.nodes if x not in voters]
ang = {x: math.atan2(sum(G[p][x]["w"] * pos[p][1] for p in G.predecessors(x)), sum(G[p][x]["w"] * pos[p][0] for p in G.predecessors(x))) for x in au}
au.sort(key=lambda x: ang[x])
for i, x in enumerate(au):
    t = 2 * math.pi * i / max(len(au), 1) + (ang[au[0]] if au else 0); pos[x] = (math.cos(t), .92 * math.sin(t))
f, ax = plt.subplots(figsize=(11, 8), dpi=110); f.patch.set_facecolor(BG); ax.set_facecolor(BG); ax.axis("off")
ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.1, 1.1); mw = max([e[2] for e in E] or [1])
nx.draw_networkx_edges(G, pos, ax=ax, width=[.6 + G[u][x]["w"] / mw * 5 for u, x in G.edges()], edge_color="#C9A45C",
                       arrows=True, arrowsize=9, alpha=.8, connectionstyle="arc3,rad=0.05", node_size=300)
out = {u: sum(G[u][x]["w"] for x in G.successors(u)) for u in voters}; mo = max(out.values() or [1])
nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=vl, node_color=HONEY, node_size=[300 + out[u] / mo * 1200 for u in vl], edgecolors=DARK)
nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=au, node_color="#FCE9B8", node_size=160, edgecolors="#8a7350")
nx.draw_networkx_labels(G, pos, ax=ax, labels={x: "@" + x for x in vl}, font_size=10, font_weight="bold")
nx.draw_networkx_labels(G, pos, ax=ax, labels={x: "@" + x for x in au}, font_size=7, font_color="#5a4630")
ax.set_title(f"Who votes whom: the {len(E)} strongest voter → author links", fontsize=15, fontweight="bold", loc="left", color=DARK)
f.text(.01, .01, "big honey dots = voters · small dots = authors · thicker line = more $", fontsize=9, color="#8a7350")
save(f, "5_vote_map.png"); IMGS.append("5_vote_map.png")

# 6 (monthly) day by day
if not DAILY:
    dd = d["daily"]; f, ax = fig(11, 5.2)
    ax.bar([x[0][5:] for x in dd], [x[2] for x in dd], color=HONEY, edgecolor=DARK, linewidth=.5)
    ax.set_ylabel("$ paid (authors + curators)"); ax.tick_params(axis="x", labelsize=7.5, rotation=60)
    ax.set_title("Honey paid, day by day (by creation date)", fontsize=15, fontweight="bold", loc="left")
    save(f, "6_daily.png"); IMGS.append("6_daily.png")

# ---------- cover ----------
G1, G2, GOLD = "#1F4D2B", "#2E7D46", "#F2B705"
f = plt.figure(figsize=(12, 6.75), dpi=100); f.patch.set_facecolor(G1); ax = f.add_axes([0, 0, 1, 1]); ax.axis("off")
ax.set_xlim(0, 12); ax.set_ylim(0, 6.75)
for i in range(14):
    for j in range(9):
        ax.add_patch(RegularPolygon((i * .95 + (.47 if j % 2 else 0), j * .82), 6, radius=.5, facecolor="none", edgecolor="#2F6B3E", lw=1.2))
ax.add_patch(FancyBboxPatch((.7, 1.3), 10.6, 4.1, boxstyle="round,pad=0.1", facecolor="#F3FAEE", edgecolor=GOLD, lw=5))
ax.text(.95, 4.75, ("BEECOUNTER DAILY" if DAILY else "BEECOUNTER MONTHLY · " + MONTH.upper()) + (f" #{NUM}" if NUM else ""), fontsize=28 if DAILY else 25, fontweight="bold", color=G1)
ax.text(.95, 3.95, "Final payouts: the honey is in the jar", fontsize=21, color=G2, fontweight="bold")
ax.text(.95, 3.05, f"Posts created {CREATEDS}  →  paid {PAIDS}", fontsize=14.5, color=G1)
ax.text(.95, 2.35, f"{d['nPosts']:,} posts · {d['votes']:,} votes · ≈ ${d['tot']:,.0f} paid", fontsize=15, color=G1, fontweight="bold")
ax.text(.95, 1.65, "by @beecounter · The Hive Tree by @hive3", fontsize=12.5, color="#5B7F63")
ax.text(9.35, 3.25, "PAID\nOUT", ha="center", va="center", fontsize=44, fontweight="bold", color="#C62828", rotation=-14, linespacing=.95,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="none", edgecolor="#C62828", lw=6))
ax.text(9.35, 1.85, "FINAL · NOT PENDING", ha="center", fontsize=12, fontweight="bold", color="white", rotation=-14,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#C62828", edgecolor="none"))
f.savefig(os.path.join(OUT, "0_cover.png"), facecolor=G1); plt.close(f)
try:   # bee avatar, top right
    cv = Image.open(os.path.join(OUT, "0_cover.png")).convert("RGBA"); av = Image.open(os.path.join(HERE, "avatar.png")).convert("RGBA").resize((130, 130))
    cv.alpha_composite(av, (1040, 30)); cv.convert("RGB").save(os.path.join(OUT, "0_cover.png"))
except Exception as e: print("avatar:", e)
IMGS.insert(0, "0_cover.png")

# ---------- text ----------
img = lambda name: f"<center>\n\nIMG:{name}\n\n</center>"
link = lambda r: "[" + ((r.get("t") or r["p"][:60]).strip().replace("|", "/").replace("[", "(").replace("]", ")")) + f"](/@{r['a']}/{r['p']})"
def uniq(rows):
    seen = set(); out = []
    for r in rows:
        if r["a"] not in seen: seen.add(r["a"]); out.append(r)
    return out
def table(rows, cols):
    head = "| " + " | ".join(c[0] for c in cols) + " |\n|" + "|".join("---:" if c[2] else "---" for c in cols) + "|\n"
    return head + "\n".join("| " + " | ".join(c[1](r) for c in cols) + " |" for r in rows)
z, N = d["zero"], d["nPosts"]; low = d["buckets"][0][1] + d["buckets"][1][1]
big = sum(b[1] for b in d["buckets"][6:]); top = sum(b[1] for b in d["buckets"][7:])
vt0 = [v for v in d["topVoters"] if v[0] not in SELF]; app = vt0[0]
h = {x + 1: p for x, p in d["hourCurve"]}
period = f"on **{PAID}**" if DAILY else f"between **{PAID}**".replace(" – ", "** and **")
L = []
L.append(img("0_cover.png"))
L.append(pick("Bzzz! 🐝 BeeCounter here, back from counting the jars. 🍯",
              "Bzzz bzzz! 🐝 Another payout day, another honeycomb to count. 🍯",
              "Hello, hive! 🐝 Your friendly counting bee has finished the sums. 🍯"))
L.append(f"This report looks at the posts paid out {period}, the ones created on **{CREATED} (UTC)**. "
         "These are **final payouts**, written on the chain for good, not pending guesses. 🌳")
L.append("---\n\n## 📊 The payout in numbers\n\n| | |\n|---|---:|\n"
         f"| 📝 Posts paid out | **{N:,}** |\n| ✍️ Different authors | **{d['nAuthors']:,}** |\n"
         f"| 🗳️ Upvotes | **{d['votes']:,}** |\n| 🐝 Different voters | **{d['nVoters']:,}** |\n"
         f"| 🍯 Paid to authors + curators | **≈ ${d['tot']:,.0f}** |\n| 🎁 Paid to beneficiaries | **≈ ${d['ben']:,.0f}** |\n"
         f"| ⚖️ Median post | **${d['med']:.2f}** |\n| 🥀 Posts paid zero (< $0.02) | **{z:,} ({pct(z, N)})** |\n"
         f"| 👎 Downvotes | **{d['down']:,}** on {d['postsHit']:,} posts |")
L.append("---\n\n## 🍯 How much did each post earn?\n\n" + img("1_payout_distribution.png"))
L.append(f"- **{low:,} posts ({pct(low, N)}) got less than $0.50.**\n- **{big:,} posts went above $10**, and **{top:,} above $25**.\n"
         f"- **{z:,} posts ({pct(z, N)}) were paid zero.** Hive doesn't pay out dust (anything below ≈ 0.02 HBD rounds down to zero, because amounts have only 3 decimals), and posts that declined payout count as zero too. 🐝")
L.append("---\n\n## 🌳 The honey curve\n\n" + img("3_honey_curve.png"))
L.append(f"- **{d['half']:,} authors ({pct(d['half'], d['nAuthors'])}) received half of all the rewards.**\n"
         f"- **The bottom half of authors shared just {d['bottomHalf']}%.**\n- The top 10% of authors took **{d['top10a'] * 100:.0f}%**.")
L.append("---\n\n## 🫙 Who filled the jars?\n\n" + img("2_top_voters.png"))
br = [b for b in d["broad"] if b[0] not in SELF][:4]
L.append(f"- **The top 10 voters gave {d['top10v'] * 100:.0f}%** of all rewards, the **top 50 gave {d['top50v'] * 100:.0f}%**.\n"
         f"- @{app[0]} was the biggest honey-giver: **≈ ${app[1]:,.0f} across {app[3]:,} authors**.\n"
         "- **Busiest wings** (most different authors voted): " + ", ".join(f"@{b[0]} ({b[3]:,})" for b in br) + ". 🌼")
L.append("---\n\n## ⏱️ Day one vs. payout day\n\n" + img("4_time_curve.png"))
txt = (f"- Within **1 hour** a post had received **{h.get(1, 0):.0f}%** of its final upvote power, within **24 hours** "
       f"**{h.get(25, 0):.0f}%**, within **3 days** **{h.get(73, 0):.0f}%**.\n" +
       (f"- In other words, **Hive is mostly a 24-hour game**: only **{100 - h.get(25, 0):.0f}% of the honey arrived after day one**. 🐝\n" if h.get(25, 0) >= 85 else f"- So **{100 - h.get(25, 0):.0f}% of the honey arrived after day one**: what you see after 24 hours is not the end of the story. 🐝\n") +
       f"- For a typical post earning at least $1, **{d['f24med'] * 100:.1f}%** of its final upvote power was already there after 24 hours.\n" +
       f"- Still, **≈ ${d['gainAfter24']:,.0f}** of rewards arrived after day one.")
L.append(txt)
lvt = [x for x in d["lateVoters"] if x[0] not in SELF and x[1] >= MIN_USD][:10]
if lvt:
    L.append("**🐝 Late pollinators: the curators who vote after day one** (idea by @antisocialist)\n\n"
             "Curation rewards are split by voting time: votes in the **first 24 hours** earn the full curation share, on **days 2–3** half, and from **day 4 until the last 12 hours** only an eighth; in the last 12 hours a vote can no longer raise the payout. The curation a late voter gives up is not lost: it is shared among the curators who voted earlier (thanks @antisocialist for the correction), while their vote still raises the post's payout for the author. In short, late voters **do a favor to the author and to every earlier curator**. Here are the ones who gave the most honey after day one:\n\n" +
             table(lvt, [("Voter", lambda x: "@" + x[0], 0), ("≈ $ given after 24h", lambda x: money(x[1]), 1), ("Share of their votes after 24h", lambda x: f"{x[2] * 100:.0f}%", 1)]))
late = uniq([r for r in d["late"] if r["a"] not in SELF and r["pay"] >= MIN_USD])[:10]
if late:
    L.append("**🌸 Late bloomers**: poor after 24 hours, well paid in the end\n\n" + table(late, [
        ("Post", lambda r: link(r), 0), ("Author", lambda r: "@" + r["a"], 0),
        ("≈ $ after 24h", lambda r: money(r["e24"]), 1), ("$ paid", lambda r: money(r["pay"]), 1)]))
drops = uniq([r for r in d["drops"] if r["a"] not in SELF and r["e24"] - r["pay"] >= MIN_USD])[:10]
if drops:
    L.append("**🍂 Shrunk before payout**: worth more after 24 hours than what was finally paid (downvotes or removed votes)\n\n" + table(drops, [
        ("Post", lambda r: link(r), 0), ("Author", lambda r: "@" + r["a"], 0),
        ("≈ $ after 24h", lambda r: money(r["e24"]), 1), ("$ paid", lambda r: money(r["pay"]), 1), ("Downvotes", lambda r: str(r["nd"]), 1)]))
L.append("---\n\n## 🕸️ Who votes whom\n\n" + img("5_vote_map.png"))
e0 = d["edges"][0]; rc = d["recip"][:1]
L.append(f"The strongest single link was **@{e0[0]} → @{e0[1]}** (≈ ${e0[2]:,.2f}). " +
         (f"The most balanced two-way pair was **@{rc[0][0]} ⇄ @{rc[0][1]}** (≈ ${rc[0][2]:,.2f} one way, ${rc[0][3]:,.2f} the other). 🍯" if rc else ""))
if not DAILY:
    L.append("---\n\n## 📅 Day by day\n\n" + img("6_daily.png"))
    ta = [a for a in d["topAuthors"] if a[0] not in SELF and a[1] >= MIN_USD][:20]
    L.append("**Top authors of the period** 🏆\n\n" + table(ta, [("Author", lambda a: "@" + a[0], 0), ("Posts", lambda a: f"{a[2]:,}", 1), ("$ paid", lambda a: money(a[1]), 1)]))
cols = lambda first: [("Post", lambda r: link(r), 0), ("Author", lambda r: "@" + r["a"], 0)] + (
    [("$ paid", lambda r: money(r["pay"]), 1), ("Voters", lambda r: f"{r['nv']:,}", 1)] if first else
    [("Voters", lambda r: f"{r['nv']:,}", 1), ("$ paid", lambda r: money(r["pay"]), 1)])
L.append("---\n\n## 🏆 Top posts\n\n**Biggest jars** 🍯\n\n" + table([r for r in d["topPay"] if r["a"] not in SELF and r["pay"] >= MIN_USD][:10], cols(True)))
L.append("**Crowd favorites** 🐝 (most voters)\n\n" + table([r for r in d["crowd"] if r["a"] not in SELF][:10], cols(False)))
L.append("## 🌸 For the rest of us\n\nPosts by authors **outside the top 25% of earners**, ranked by **how many people voted**:\n\n" +
         table([r for r in d["rest"] if r["a"] not in SELF][:10], cols(False)) + "\n\nLots of love, little honey: go give them a visit! 🐝💛")
tb = [b for b in d["topBen"] if b[1] >= MIN_USD][:10]
L.append("---\n\n## 🎁 Beneficiaries\n\n" + f"**{d['postsBen']:,} posts ({pct(d['postsBen'], N)})** shared their reward with **{d['nBenAcc']:,} accounts**, "
         f"for **≈ ${d['ben']:,.2f}** in total.\n\n" + table(tb, [("Beneficiary", lambda b: ("@" + b[0]) + (" 🔥" if b[0] == "null" else ""), 0),
         ("≈ $ received", lambda b: money(b[1]), 1), ("Posts", lambda b: f"{b[2]:,}", 1)]))
ra = d.get("rewardApp") or []
if ra and not DAILY:
    rt = d["rewardAppTot"]
    L.append("**🔁 Who uses @reward.app the most?** It is a service that pays post rewards out as liquid tokens right away, for a fee. "
             f"In this period **{rt[0]:,} authors** set it as beneficiary on **{rt[1]:,} posts**, sending it **≈ ${rt[2]:,.2f}**. The top 10:\n\n" +
             table(ra, [("Author", lambda x: "@" + x[0], 0), ("Posts", lambda x: f"{x[2]:,}", 1), ("Avg. share", lambda x: f"{x[3]:.0f}%", 1), ("≈ $ to @reward.app", lambda x: money(x[1]), 1)]))
dv = [x for x in d["topDV"] if x[2] >= MIN_USD][:10]; hit = [x for x in d["topHit"]][:3]
# Nov 2026: late-voter curation and "where removed rewards go" corrected/added on a suggestion by @antisocialist
L.append("---\n\n## 👎 Downvotes\n\n" + "Downvotes are part of how Hive works. Just the numbers, no judgment:\n\n"
         f"- **{d['down']:,} downvotes** from **{d['nDownvoters']:,} accounts** hit **{d['postsHit']:,} posts** and removed an estimated **≈ ${d['removed']:,.2f}**.\n"
         f"- **{d['zeroed']:,} posts that had upvotes ended at zero.**\n"
         f"- **Where does that honey go?** It is not burned: it goes back to the reward pool and is paid out again by the next votes. "
         f"This month the **top 10 voters** cast **{d['top10v'] * 100:.0f}%** of all upvote value, so roughly that share of the removed honey "
         f"ends up with them as curators and with the authors they choose (a point raised by @antisocialist).\n\n" +
         (table(dv, [("Downvoter", lambda x: "@" + x[0], 0), ("Downvotes", lambda x: f"{x[1]:,}", 1), ("≈ $ removed", lambda x: money(x[2]), 1), ("Authors", lambda x: f"{x[3]:,}", 1)]) if dv else "") +
         ("\n\nMost hit: " + ", ".join(f"@{x[0]} ({x[1]} downvotes, ≈ ${x[2]:,.2f})" for x in hit) + "." if hit else ""))
cm = d["comm"][:4]
L.append("---\n\n## 🏘️ Communities\n\nThe communities that took home the most: " +
         ", ".join(f"**{ctitle(c[0])}** ({c[1]:,} posts, ≈ ${c[2]:,.0f})" for c in cm) + ". 🐝")
L.append("---\n\n## 🔬 How this bee counts\n\n"
         f"- All top-level posts created on **{CREATED} (UTC)**, with all their upvotes, read from the public **HAFSQL** database by @mahdiyari. No public API node is hammered.\n"
         "- Rewards are the **final payouts** recorded on the chain (author + curator share, USD value). Beneficiaries are counted separately.\n"
         "- \"$ given\", \"≈ $ after 24h\" and \"$ removed\" are **estimates**, based on each vote's rshares.\n"
         "- Comments and Hive-Engine tokens are not counted. Accounts of The Hive Tree are left out of the rankings.\n"
         f"- Rankings show at most 10–20 names and leave out anyone below **${MIN_USD:,.2f}** (payout cutoff suggested by @antisocialist).")
L.append("---\n\nThis bee is a 🤖 **bot**, built with love 💛 by @hive3 for every bee in the Hive 🐝🌼🍯. It never votes and never comments: it only counts, so the whole hive can see where the honey flows. Ideas and corrections are welcome in the comments, a human reads them: @hive3. 🌳")
L.append("🧩 **Open source & AI-generated**: every script that builds this report is public on [GitHub](https://github.com/hiveb3/beecounter) (MIT license), written with an AI (Claude) and reviewed by a human. Anyone can check the numbers, run it, fork it or keep it alive. 🐝")
L.append("<sub>🔥 **100% of this post's rewards are burned** (beneficiary @null): pure data for the hive, nothing to farm. "
         "Data by @mahdiyari's HAFSQL, idea by @antisocialist.</sub>")
L.append("**BeeCounter** 🐝🧮\n@beecounter · *The Hive Tree* 🌳 by @hive3\n\n"
         "<sub>🐝 Join **[AIBees](/c/hive-170283)**, the AI-assisted creators' community · 🎮 Play **[BeeTris](https://hiveb3.github.io/beetris/)** · "
         "🗳️ [Vote @hive3 as witness](https://vote.hive.uno/@hive3)</sub>")
body = "\n\n".join(L) + "\n"
title = (f"🐝 BeeCounter Daily{(' #' + NUM) if NUM else ''}: who fed whom on payout day {PAID}" if DAILY else
         f"🐝 BeeCounter Monthly: who fed whom in {MONTH} (final payouts)")
desc = f"Final Hive payouts {PAID}: {N:,} posts, ≈ ${d['tot']:,.0f}, who fed whom, beneficiaries, downvotes. 🐝🍯"
if len(desc) > 120: desc = f"Final Hive payouts: {N:,} posts, ≈ ${d['tot']:,.0f}, who fed whom, beneficiaries, downvotes. 🐝"
permlink = (f"beecounter-daily-payout-{p0.isoformat()}" if DAILY else f"beecounter-monthly-{FROM}-{TO}")
tags = ["hive-133987", "hive", "statistics", "curation", "data", "downvotes", "beneficiaries", "hivestats", "aibees"]
open(os.path.join(OUT, "post.md"), "w").write(body)
json.dump(dict(title=title, permlink=permlink, description=desc, tags=tags, images=IMGS, community="hive-133987"),
          open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False, indent=1)
print("OK", OUT, title)
