#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter - collects from HAFSQL all top-level posts created between FROM and TO (inclusive, UTC) and their votes.
# Usage: python3 collect.py 2026-10-01 2026-10-27   -> data_FROM_TO.json
import sys, json, csv, datetime as dt, collections as C, statistics
FROM, TO = sys.argv[1], sys.argv[2]

def fetch_day(cur, day):
    D0 = dt.datetime.fromisoformat(day); D1 = D0 + dt.timedelta(days=1); D8 = D0 + dt.timedelta(days=8)
    cur.execute("""SELECT author, permlink, title, created, category, total_payout_value, curator_payout_value,
                   beneficiary_payout_value, net_rshares, beneficiaries, deleted
                   FROM hafsql.comments WHERE parent_author='' AND created>=%s AND created<%s""", (D0, D1))
    posts = cur.fetchall()
    cur.execute("""SELECT v.voter, v.author, v.permlink, v.rshares, v.timestamp
                   FROM hafsql.operation_effective_comment_vote_view v
                   JOIN hafsql.comments c ON c.author=v.author AND c.permlink=v.permlink
                   WHERE c.parent_author='' AND c.created>=%s AND c.created<%s
                     AND v.timestamp>=%s AND v.timestamp<%s""", (D0, D1, D0, D8))
    return posts, sorted(cur.fetchall(), key=lambda x: x[4])

def analyze(days):
    """days: list of (day, posts, votes)"""
    H = [0.0] * 169                       # positive rshares per hour since publication
    P = []                                # one record per post
    vt = C.defaultdict(lambda: [0.0, 0, 0.0])   # voter: usd, votes, usd after 24h
    va = C.defaultdict(set)               # voter -> authors
    edges = C.Counter()
    dv = C.defaultdict(lambda: [0, 0.0, set()])  # downvoter: n, negative rshares (capped), authors
    hit = C.defaultdict(lambda: [0, 0.0])
    ben = C.defaultdict(lambda: [0.0, 0])
    rapp = C.defaultdict(lambda: [0.0, 0, 0])   # authors using @reward.app: usd, posts, sum of weights
    daily = []
    for day, posts, votes in days:
        last = {}
        for voter, a, pl, rs, ts in votes:
            last[(a, pl, voter)] = (float(rs), ts)
        byp = C.defaultdict(list)
        for (a, pl, voter), (rs, ts) in last.items():
            byp[(a, pl)].append((voter, rs, ts))
        dpay = dben = 0; dn = 0
        for a, pl, title, created, cat, tpv, cpv, bpv, net, bens, deleted in posts:
            if deleted: continue
            cr = created.astimezone(dt.timezone.utc).replace(tzinfo=None) if created.tzinfo else created
            # HAFSQL total_payout_value is the WHOLE payout: author + curators + beneficiaries (thanks @crimsonclad).
            # pay = authors + curators, b = beneficiaries, so pay + b = total_payout_value
            b = float(bpv or 0); pay = float(tpv or 0) - b
            try: L = json.loads(bens) if isinstance(bens, str) else (bens or [])
            except Exception: L = []
            w = sum(x.get("weight", 0) for x in L)
            for x in L:
                ben[x["account"]][0] += b * x["weight"] / w if w else 0; ben[x["account"]][1] += 1
                if x["account"] == "reward.app":
                    rapp[a][0] += b * x["weight"] / w if w else 0; rapp[a][1] += 1; rapp[a][2] += x["weight"]
            vs = byp.get((a, pl), [])
            pos = sum(rs for _, rs, _ in vs if rs > 0)
            r = dict(d=day, a=a, p=pl, t=(title or '')[:70], c=cat, pay=pay, ben=b, net=float(net or 0), pos=pos,
                     pos1=0.0, pos24=0.0, net24=0.0, nup=0, nup24=0, nd=0, neg=0.0)
            for voter, rs, ts in vs:
                h = (ts - cr).total_seconds() / 3600
                if h <= 24: r["net24"] += rs
                if rs > 0:
                    r["nup"] += 1; H[min(max(int(h), 0), 168)] += rs
                    if h <= 1: r["pos1"] += rs
                    if h <= 24: r["pos24"] += rs; r["nup24"] += 1
                    usd = pay * rs / pos if pos else 0
                    vt[voter][0] += usd; vt[voter][1] += 1
                    if h > 24: vt[voter][2] += usd
                    va[voter].add(a)
                    if voter != a: edges[(voter, a)] += usd
                elif rs < 0:
                    r["nd"] += 1; c = min(-rs, pos); r["neg"] += c
                    dv[voter][0] += 1; dv[voter][1] += c; dv[voter][2].add(a); hit[a][0] += 1
            P.append(r); dpay += pay; dben += b; dn += 1
        daily.append([day, dn, round(dpay, 2), round(dben, 2)])
    tot = sum(r["pay"] for r in P); totb = sum(r["ben"] for r in P)
    k = (tot + totb) / sum(max(r["net"], 0) for r in P)          # $ per rshare (average)
    for v in dv.values(): v[1] *= k
    for r in P:
        hit[r["a"]][1] += r["neg"] * k
        # estimate of what the post showed after 24h (payout is linear in net rshares)
        r["est24"] = max(r["net24"], 0) * k
    ap = C.Counter()
    for r in P: ap[r["a"]] += r["pay"]
    av = sorted(ap.values(), reverse=True); n = len(av); cum, c = [], 0; half = None
    for i, x in enumerate(av):
        c += x
        if half is None and c >= tot / 2: half = i + 1
        if i % max(n // 100, 1) == 0 or i == n - 1: cum.append([i + 1, round(c / tot * 100, 1)])
    pays = [r["pay"] for r in P]
    bk = [(0, .01), (.01, .5), (.5, 1), (1, 2), (2, 5), (5, 10), (10, 25), (25, 50), (50, 1e9)]
    vsum = sum(x[0] for x in vt.values()); svt = sorted(vt.items(), key=lambda i: -i[1][0])
    # day one vs final payout
    tp = sum(r["pos"] for r in P); Hc, acc = [], 0
    for h in range(169):
        acc += H[h]
        if h in (0, 1, 2, 3, 6, 12, 24, 36, 48, 72, 96, 120, 144, 168): Hc.append([h, round(acc / tp * 100, 1)])
    f24 = [r["pos24"] / r["pos"] for r in P if r["pos"] > 0 and r["pay"] >= 1]
    fb = [0] * 10
    for f in f24: fb[min(int(f * 10), 9)] += 1
    late = sorted([r for r in P if r["pay"] >= 3 and r["pos"] > 0], key=lambda r: r["pos24"] / r["pos"])[:12]
    drops = sorted([r for r in P if r["est24"] - r["pay"] - r["ben"] > 0.5], key=lambda r: -(r["est24"] - r["pay"] - r["ben"]))[:12]
    gain_tot = sum(max(r["pay"] + r["ben"] - r["est24"], 0) for r in P)
    est24_tot = sum(r["est24"] for r in P)
    sm = lambda r: dict(a=r["a"], p=r["p"], t=r["t"], d=r["d"], c=r["c"], pay=round(r["pay"], 2), nv=r["nup"],
                        e24=round(r["est24"], 2), f24=round(r["pos24"] / r["pos"], 3) if r["pos"] else 0, nd=r["nd"])
    q3 = sorted(ap.values())[int(n * .75)]
    comm = C.defaultdict(lambda: [0, 0.0])
    for r in P: comm[r["c"]][0] += 1; comm[r["c"]][1] += r["pay"]
    recip = sorted([(a, b, round(x, 2), round(edges[(b, a)], 2)) for (a, b), x in edges.items()
                    if a < b and edges.get((b, a), 0) > 0], key=lambda t: -min(t[2], t[3]))[:12]
    zeroed = sum(1 for r in P if r["nd"] and r["pos"] > 0 and r["net"] <= 0)
    return dict(
        days=len(daily), nPosts=len(P), nAuthors=n, nVoters=len(vt), votes=sum(r["nup"] for r in P),
        tot=round(tot, 2), ben=round(totb, 2), med=round(statistics.median(pays), 3),
        zero=sum(1 for x in pays if x < .01), daily=daily,
        buckets=[[f"{lo}-{hi}", sum(1 for x in pays if lo <= x < hi)] for lo, hi in bk],
        half=half, bottomHalf=round(sum(av[n // 2:]) / tot * 100, 1), top10a=round(sum(av[:n // 10]) / tot, 3),
        top10v=round(sum(x[1][0] for x in svt[:10]) / vsum, 3), top50v=round(sum(x[1][0] for x in svt[:50]) / vsum, 3),
        cum=cum, topAuthors=[[a, round(x, 2), sum(1 for r in P if r["a"] == a)] for a, x in ap.most_common(15)],
        topVoters=[[v, round(x[0], 2), x[1], len(va[v]), round(x[2] / x[0], 3) if x[0] else 0] for v, x in svt[:20]],
        lateVoters=[[v, round(x[2], 2), round(x[2] / x[0], 3)] for v, x in sorted(vt.items(), key=lambda i: -i[1][2])[:15]],
        broad=[[v, round(vt[v][0], 2), vt[v][1], len(s)] for v, s in sorted(va.items(), key=lambda i: -len(i[1]))[:10]],
        topPay=[sm(r) for r in sorted(P, key=lambda r: -r["pay"])[:10]],
        crowd=[sm(r) for r in sorted(P, key=lambda r: -r["nup"])[:10]],
        rest=[sm(r) for r in sorted([r for r in P if ap[r["a"]] < q3], key=lambda r: -r["nup"])[:12]],
        comm=sorted([[c, x[0], round(x[1], 2)] for c, x in comm.items()], key=lambda t: -t[2])[:12],
        edges=[[a, b, round(x, 2)] for (a, b), x in edges.most_common(50)], recip=recip,
        topBen=[[a, round(x[0], 2), x[1]] for a, x in sorted(ben.items(), key=lambda i: -i[1][0])[:15]],
        rewardApp=[[a, round(x[0], 2), x[1], round(x[2] / x[1] / 100, 1)] for a, x in sorted(rapp.items(), key=lambda i: -i[1][0])[:10]],
        rewardAppTot=[len(rapp), sum(x[1] for x in rapp.values()), round(sum(x[0] for x in rapp.values()), 2)],
        postsBen=sum(1 for r in P if r["ben"] > 0), nBenAcc=len(ben),
        down=sum(r["nd"] for r in P), postsHit=sum(1 for r in P if r["nd"]), zeroed=zeroed,
        nDownvoters=len(dv), removed=round(sum(x[1] for x in dv.values()), 2),
        topDV=[[a, x[0], round(x[1], 2), len(x[2])] for a, x in sorted(dv.items(), key=lambda i: -i[1][1])[:12]],
        topDVn=[[a, x[0], round(x[1], 2), len(x[2])] for a, x in sorted(dv.items(), key=lambda i: -i[1][0])[:8]],
        topHit=[[a, x[0], round(x[1], 2)] for a, x in sorted(hit.items(), key=lambda i: -i[1][1])[:12]],
        hourCurve=Hc, f24buckets=fb, nf24=len(f24), f24med=round(statistics.median(f24), 3) if f24 else 0,
        est24tot=round(est24_tot, 2), gainAfter24=round(gain_tot, 2),
        late=[sm(r) for r in late], drops=[sm(r) for r in drops])

if __name__ == "__main__":
    import psycopg2
    con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                           user="hafsql_public", password="hafsql_public", connect_timeout=30)
    con.set_session(readonly=True, autocommit=True)
    cur = con.cursor(); cur.execute("SET statement_timeout = '900s'"); cur.execute("SET TIME ZONE 'UTC'")
    def gen():
        global con, cur
        d, end = dt.date.fromisoformat(FROM), dt.date.fromisoformat(TO)
        while d <= end:
            for t in range(3):
                try:
                    posts, votes = fetch_day(cur, d.isoformat()); break
                except Exception as e:
                    print("retry", d, e, flush=True)
                    con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                                           user="hafsql_public", password="hafsql_public", connect_timeout=30)
                    con.set_session(readonly=True, autocommit=True); cur = con.cursor()
                    cur.execute("SET statement_timeout = '900s'"); cur.execute("SET TIME ZONE 'UTC'")
            print(d, len(posts), "posts", len(votes), "votes", flush=True)
            yield (d.isoformat(), posts, votes); d += dt.timedelta(days=1)
    days = gen()
    out = analyze(days)
    json.dump(out, open(f"data_{FROM}_{TO}.json", "w"), ensure_ascii=False)
    print("DONE: data_%s_%s.json" % (FROM, TO))
