#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter farm check - whole of Hive, from HAFSQL: reward concentration, vote rings, focused voters, bot timing.
# Measures, does not accuse: every number is a signal to check by hand.
# Usage: python3 farm_check.py 2026-10-24 2026-11-06   -> prints the report, saves farm_FROM_TO.json + farm_edges_FROM_TO.csv
import sys, json, csv, datetime as dt, collections as C, statistics
from collect import fetch_day   # same HAFSQL queries as the BeeCounter reports
FROM, TO = sys.argv[1], sys.argv[2]

def connect():
    import psycopg2
    con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                           user="hafsql_public", password="hafsql_public", connect_timeout=30)
    con.set_session(readonly=True, autocommit=True)
    cur = con.cursor(); cur.execute("SET statement_timeout = '900s'"); cur.execute("SET TIME ZONE 'UTC'")
    return con, cur

pay = C.Counter()                                   # author -> $ (author+curation of their posts)
edge = C.Counter(); edge_n = C.Counter()            # (voter, author) -> $ given, votes
vusd = C.Counter(); vn = C.Counter()                # voter -> $ given, votes
delay = C.defaultdict(list)                         # voter -> seconds after publication
selfv = C.Counter()                                 # author -> $ from own votes
nposts = C.Counter()
con, cur = connect()
d, end = dt.date.fromisoformat(FROM), dt.date.fromisoformat(TO)
while d <= end:
    for t in range(3):
        try: posts, votes = fetch_day(cur, d.isoformat()); break
        except Exception as e:
            print('retry', d, e, flush=True); con, cur = connect()
    last = {}
    for voter, a, pl, rs, ts in votes: last[(a, pl, voter)] = (float(rs), ts)
    byp = C.defaultdict(list)
    for (a, pl, voter), (rs, ts) in last.items(): byp[(a, pl)].append((voter, rs, ts))
    for a, pl, title, created, cat, tpv, cpv, bpv, net, bens, deleted in posts:
        if deleted: continue
        cr = created.astimezone(dt.timezone.utc).replace(tzinfo=None) if created.tzinfo else created
        p = float(tpv or 0); pay[a] += p; nposts[a] += 1  # HAFSQL tpv already includes curators
        vs = byp.get((a, pl), []); pos = sum(rs for _, rs, _ in vs if rs > 0)
        for voter, rs, ts in vs:
            if rs <= 0: continue
            usd = p * rs / pos if pos else 0
            if voter == a: selfv[a] += usd; continue
            edge[(voter, a)] += usd; edge_n[(voter, a)] += 1; vusd[voter] += usd; vn[voter] += 1
            tsn = ts.astimezone(dt.timezone.utc).replace(tzinfo=None) if ts.tzinfo else ts
            delay[voter].append((tsn - cr).total_seconds())
    print(d, len(posts), 'posts', len(votes), 'votes', flush=True)
    d += dt.timedelta(days=1)

tot = sum(pay.values()) or 1
ranked = pay.most_common(); n = len(ranked)
acc = 0; k75 = 0
for _, x in ranked:
    acc += x; k75 += 1
    if acc >= .75 * tot: break
v = sorted(pay.values()); s = sum(v)
gini = sum((2 * i - n + 1) * x for i, x in enumerate(v)) / (n * s) if s else 0
out = {'from': FROM, 'to': TO, 'authors': n, 'total': round(tot, 2), 'k75': k75, 'gini': round(gini, 3)}

print(f'\n=== CONCENTRATION ({FROM} → {TO}, whole Hive, top-level posts) ===')
print(f'{n} authors, {tot:,.0f} $ · {k75} authors ({k75/n:.1%}) take 75% · Gini {gini:.2f}')
out['top'] = []
for a, x in ranked[:25]:
    sv = selfv[a] / x if x else 0
    out['top'].append([a, round(x, 2), nposts[a], round(sv, 3)])
    print(f'  {a:<18} {x:9.2f} $ {x/tot:6.2%}  posts {nposts[a]:<4} self-vote {sv:4.0%}')

print('\n=== RECIPROCAL PAIRS ($ given both ways, min of the two) ===')
pairs = sorted([(min(x, edge[(b, a)]), a, b, x, edge[(b, a)]) for (a, b), x in edge.items()
                if a < b and edge.get((b, a), 0) > 0], reverse=True)[:30]
out['pairs'] = [[a, b, round(x, 2), round(y, 2)] for _, a, b, x, y in pairs]
for _, a, b, x, y in pairs: print(f'  {a} ⇄ {b}   {x:.2f} $ / {y:.2f} $   votes {edge_n[(a, b)]}/{edge_n[(b, a)]}')

print('\n=== FOCUSED VOTERS (>=60% of the $ they give goes to one author, >=5 votes) ===')
best = {}
for (vt, a), x in edge.items():
    if x > best.get(vt, ('', 0))[1]: best[vt] = (a, x)
foc = sorted([(x, vt, a, x / vusd[vt]) for vt, (a, x) in best.items()
              if vusd[vt] and x / vusd[vt] >= .6 and edge_n[(vt, a)] >= 5], reverse=True)[:40]
out['focused'] = [[vt, a, round(x, 2), round(sh, 3)] for x, vt, a, sh in foc]
for x, vt, a, sh in foc: print(f'  {vt:<18} → {a:<18} {sh:4.0%} of its votes, {x:.2f} $ ({edge_n[(vt, a)]} votes)')

print('\n=== BOT TIMING (>=20 votes, vote delay almost always the same) ===')
bots = []
for vt, ds in delay.items():
    if len(ds) >= 20:
        q = statistics.quantiles(ds, n=10); spread = q[7] - q[1]
        if spread < 60: bots.append((vusd[vt], vt, statistics.median(ds), spread, len(ds)))
bots.sort(reverse=True)
out['bots'] = [[vt, round(u, 2), round(m), round(sp), c] for u, vt, m, sp, c in bots[:40]]
for u, vt, m, sp, c in bots[:40]: print(f'  {vt:<18} ~{m/60:6.1f} min after posting (spread {sp:.0f}s), {c} votes, {u:.2f} $')

print('\n=== DEPENDENCE: share of each top author\'s votes ($) from their 5 biggest voters ===')
by_a = C.defaultdict(C.Counter)
for (vt, a), x in edge.items(): by_a[a][vt] += x
out['dependence'] = []
for a, _ in ranked[:25]:
    t = sum(by_a[a].values()) or 1; t5 = by_a[a].most_common(5); sh = sum(x for _, x in t5) / t
    out['dependence'].append([a, round(sh, 3), [v for v, _ in t5]])
    print(f'  {a:<18} top-5 give {sh:4.0%}: ' + ', '.join(f'{v} {x/t:.0%}' for v, x in t5))

json.dump(out, open(f'farm_{FROM}_{TO}.json', 'w'), ensure_ascii=False, indent=1)
with open(f'farm_edges_{FROM}_{TO}.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['voter', 'author', 'usd', 'votes'])
    for (vt, a), x in edge.most_common(): w.writerow([vt, a, round(x, 4), edge_n[(vt, a)]])
print(f'\nSaved farm_{FROM}_{TO}.json and farm_edges_{FROM}_{TO}.csv')
