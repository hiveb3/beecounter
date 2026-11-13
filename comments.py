#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter - the comments paid in a month: who earns from comments, how concentrated it is, self-votes, communities.
Reads from HAFSQL the comments (parent_author <> '') created between FROM and TO (same window as collect.py: paid 7 days later).
Usage: python3 comments.py FROM TO OUTDIR      -> OUTDIR/data.json, OUTDIR/post.md, OUTDIR/m1_commenters.png"""
import sys, os, json, datetime as dt, collections as C, statistics
import psycopg2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FROM, TO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
SELF = {"hive3", "beecounter"}            # The Hive Tree accounts: left out of the rankings

def connect():
    return psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                            user="hafsql_public", password="hafsql_public", connect_timeout=30)

def run(sql, args, tries=3):
    global con
    for i in range(tries):
        try:
            cur = con.cursor(); cur.execute(sql, args); return cur.fetchall()
        except Exception as e:
            print("retry", i + 1, str(e)[:120], flush=True)
            try: con.close()
            except Exception: pass
            con = connect()
    return None

con = connect()
au = C.defaultdict(lambda: [0, 0.0, 0.0])        # author: paid comments, $ kept by the author, $ total
cat = C.defaultdict(lambda: [0, 0.0])            # community/category: comments, $
ben = C.defaultdict(float)
fund = C.defaultdict(lambda: [0, 0.0, 0.0])     # (author, main beneficiary): comments, $ total, $ to beneficiaries
cur_tot = [0.0]
kept = set()                                     # (author, permlink) of the non-funding comments
top = []                                         # most paid single comments
pays, n_all, net_pos, self_rs, self_ok = [], 0, C.defaultdict(float), C.defaultdict(float), True
d, end = dt.date.fromisoformat(FROM), dt.date.fromisoformat(TO)
while d <= end:
    D0 = dt.datetime.combine(d, dt.time()); D1 = D0 + dt.timedelta(days=1); D8 = D0 + dt.timedelta(days=8)
    r = run("SELECT count(*) FROM hafsql.comments WHERE parent_author<>'' AND created>=%s AND created<%s", (D0, D1))
    n_all += r[0][0] if r else 0
    rows = run("""SELECT author, permlink, parent_author, parent_permlink, category, total_payout_value,
                  beneficiary_payout_value, net_rshares, beneficiaries, deleted, curator_payout_value
                  FROM hafsql.comments WHERE parent_author<>'' AND created>=%s AND created<%s
                  AND total_payout_value > 0""", (D0, D1)) or []
    for a, pl, pa, ppl, cg, tpv, bpv, net, bens, deleted, cpv in rows:
        if deleted: continue
        T = float(tpv or 0); b = float(bpv or 0); cu = float(cpv or 0)   # total_payout_value = author + curators + beneficiaries
        own = max(T - cu - b, 0)                                          # what the comment author really kept
        pays.append(T); cur_tot[0] += cu
        try: L = json.loads(bens) if isinstance(bens, str) else (bens or [])
        except Exception: L = []
        w = sum(x.get("weight", 0) for x in L)
        for x in L: ben[x["account"]] += b * x["weight"] / w if w else 0
        if T and b >= T / 3:                     # funding / burn comments: most of the author share goes to a beneficiary
            main = max(L, key=lambda x: x.get("weight", 0))["account"] if L else "?"
            fund[(a, main)][0] += 1; fund[(a, main)][1] += T; fund[(a, main)][2] += b
            continue
        au[a][0] += 1; au[a][1] += own; au[a][2] += T; cat[cg or "?"][0] += 1; cat[cg or "?"][1] += T
        net_pos[a] += max(float(net or 0), 0); top.append((own, a, pl, pa)); kept.add((a, pl))
    if self_ok:     # self-votes on the paid comments of the day (last vote of each author on own comment)
        sv = run("""SELECT v.author, v.permlink, v.rshares, v.timestamp FROM hafsql.operation_effective_comment_vote_view v
                    JOIN hafsql.comments c ON c.author=v.author AND c.permlink=v.permlink
                    WHERE v.voter=v.author AND c.parent_author<>'' AND c.total_payout_value > 0
                      AND c.created>=%s AND c.created<%s AND v.timestamp>=%s AND v.timestamp<%s""", (D0, D1, D0, D8))
        if sv is None: self_ok = False; print("self-votes skipped (query too heavy)", flush=True)
        else:
            last = {}
            for a, pl, rs, ts in sorted(sv, key=lambda x: x[3]): last[(a, pl)] = float(rs)
            for (a, pl), rs in last.items():
                if (a, pl) in kept: self_rs[a] += max(rs, 0)
    print(d, len(rows), "paid comments", flush=True)
    d += dt.timedelta(days=1)

def ctitles(ids):
    out = {}
    for i in ids:
        try:
            import urllib.request
            req = urllib.request.Request("https://api.hive.blog", method="POST",
                  data=json.dumps({"jsonrpc": "2.0", "method": "bridge.get_community", "params": {"name": i}, "id": 1}).encode())
            r = json.load(urllib.request.urlopen(req, timeout=15)).get("result")
            out[i] = r["title"] if r else i
        except Exception: out[i] = i
    return out

tot = sum(pays); totb = sum(ben.values()); ftot = sum(v[1] for v in fund.values())
rank = sorted(((a, v) for a, v in au.items() if a not in SELF), key=lambda x: -x[1][1])
amts = sorted((v[1] for v in au.values()), reverse=True)
share = lambda k: sum(amts[:k]) / sum(amts) * 100 if sum(amts) else 0
one_pct = max(len(amts) // 100, 1)
self_share = sum(self_rs.values()) / sum(net_pos.values()) * 100 if self_ok and sum(net_pos.values()) else None
best, seen = [], set()
for p, a, pl, pa in sorted(top, reverse=True):
    if a in seen or a in SELF: continue
    seen.add(a); best.append([round(p, 2), a, pl, pa])
    if len(best) == 5: break
cats = sorted(([k, v[0], v[1]] for k, v in cat.items()), key=lambda x: -x[2])[:5]
CT = ctitles([c[0] for c in cats if c[0].startswith("hive-")])
data = dict(FROM=FROM, TO=TO, n_all=n_all, n_paid=len(pays), n_authors=len(au), total=tot, ben_total=totb, cur_total=cur_tot[0],
            own_total=sum(amts), median=statistics.median(pays) if pays else 0, top10_share=share(10), top1pct_share=share(one_pct), one_pct=one_pct,
            self_share=self_share, fund_total=ftot,
            fund=sorted(([a, m, v[0], v[1], v[2]] for (a, m), v in fund.items()), key=lambda x: -x[3])[:5],
            top=[[a, v[0], v[1], v[2], (self_rs[a] / net_pos[a] * 100 if self_ok and net_pos[a] else None)] for a, v in rank[:15]],
            best=best, cats=[[CT.get(c, c), c, n, p] for c, n, p in cats],
            ben=sorted(ben.items(), key=lambda x: -x[1])[:5])
json.dump(data, open(os.path.join(OUT, "data.json"), "w"), indent=1)

# ---------- chart: top 15 commenters (what the author kept) ----------
t = data["top"][::-1]
f, ax = plt.subplots(figsize=(10, 6), dpi=110); f.patch.set_facecolor("#FFF8E7"); ax.set_facecolor("#FFF8E7")
ax.barh(["@" + x[0] for x in t], [x[2] for x in t], color="#E8A33D")
for i, x in enumerate(t): ax.text(x[2], i, f"  ${x[2]:,.0f} · {x[1]} comments", va="center", fontsize=9, color="#3B2A1A")
ax.set_title("Who earns the most from comments (author share)", fontsize=14, color="#3B2A1A", loc="left")
ax.set_xlabel("$ kept by the comment author (curators and beneficiaries excluded)"); ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(0, max([x[2] for x in t] + [1]) * 1.35)
f.text(0.99, 0.01, "@beecounter · The Hive Tree by @hive3 · data: HAFSQL", ha="right", fontsize=8, color="#8a7350")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "m1_commenters.png")); plt.close()

# ---------- markdown block ----------
D = data
L = ["## 💬 The comments: who earns from talking",
     f"Of **{D['n_all']:,} comments** written, **{D['n_paid']:,}** earned something, for **${D['total']:,.0f}** in total "
     f"(authors ${D['own_total']:,.0f} · curators ${D['cur_total']:,.0f} · beneficiaries ${D['ben_total']:,.0f}). "
     f"A typical paid comment (the median) earns **${D['median']:.3f}**.",
     ("**Not all comments are conversation.** " + f"**${D['fund_total']:,.0f}** went to comments that pass most of their reward to a beneficiary, to fund or burn something: "
      + "; ".join(f"@{a} → @{m} ({n:,} comments, ${p:,.0f})" for a, m, n, p, b in D["fund"][:3]) + ". They are left out of the rankings below."
      if D["fund_total"] >= 1 else ""),
     f"Among the other comments, **{D['n_authors']:,} accounts** shared the author rewards. The **top 10** kept **{D['top10_share']:.0f}%** of them, "
     f"the top 1% ({D['one_pct']} accounts) **{D['top1pct_share']:.0f}%**."
     + (f" About **{D['self_share']:.0f}%** of the vote weight on these comments came from **self-votes**." if D["self_share"] is not None else ""),
     "IMG:m1_commenters.png",
     "| # | Commenter | Paid comments | $ kept by the author | $ total (with curators) | Self-vote share |\n|---:|---|---:|---:|---:|---:|\n" +
     "\n".join(f"| {i} | @{a} | {n:,} | ${p:,.2f} | ${T:,.2f} | {('%.0f%%' % s) if s is not None else '–'} |" for i, (a, n, p, T, s) in enumerate(D["top"][:10], 1)),
     "**The most paid comments** (one per author):\n\n" + "\n".join(f"- ${p:,.2f} to the author · [@{a}](/@{a}/{pl}) replying to @{pa}" for p, a, pl, pa in D["best"]),
     "**Where comments are paid most:** " + " · ".join(f"{('[' + t + '](/created/' + c + ')') if c.startswith('hive-') else '#' + c} (${p:,.0f}, {n:,} comments)" for t, c, n, p in D["cats"]) + ".",
     "<sub>Comments created " + f"{FROM} – {TO}, paid 7 days later. \"Self-vote share\" = the author's own vote rshares / the comment's net rshares (estimate). "
     "Funding/burn comments = at least a third of the reward goes to beneficiaries.</sub>"]
open(os.path.join(OUT, "post.md"), "w").write("\n\n".join(x for x in L if x) + "\n")
print("OK", OUT, D["n_paid"], "paid comments")
