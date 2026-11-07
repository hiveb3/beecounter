#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter money trail - does voting power pay back? (HAFSQL, public data)
#   A) for every big delegation to the top reward distributors: HIVE/HBD sent BACK from the delegatee to the delegator, per year
#      (delegation rental / profit sharing: legal, but it means votes are run as a business)
#   B) paid votes: transfers to vote-selling services whose memo is a post link, per year, top buyers and the services
#   C) the distributors' own outgoing money: where do the curation rewards end up?
# Measures, does not accuse.  Usage: python3 money_trail.py [min_vests=100000000]  -> prints + money_trail.json
import sys, json, re, collections as C
MINV = float(sys.argv[1]) if len(sys.argv) > 1 else 1e8          # 1e8 VESTS ≈ 60,000 HP
import psycopg2
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '3600s'")
YEAR = "EXTRACT(YEAR FROM to_timestamp(1584712800 + 3 * ((id >> 32) - 41818752)))::int"   # HAF op id = block_num << 32
SINCE_ID = 41818752 << 32                                                                   # from the birth of Hive
def S(x):
    x = str(x).upper(); return 'HIVE' if ('HIVE' in x or '000000021' in x) else 'HBD' if ('HBD' in x or '000000013' in x) else x
out = {}

# who distributes: biggest upvoters last 30 days
cur.execute("""SELECT voter, SUM(rshares) FROM hafsql.operation_effective_comment_vote_view
               WHERE timestamp >= now() - interval '30 days' AND rshares > 0 GROUP BY 1 ORDER BY 2 DESC LIMIT 30""")
dist = [r[0] for r in cur.fetchall()]
cur.execute("SELECT delegator, delegatee, vests FROM hafsql.delegations WHERE delegatee = ANY(%s) AND vests >= %s ORDER BY vests DESC", (dist, MINV))
dels = cur.fetchall()
print(f'=== A) BIG DELEGATIONS TO THE TOP 30 DISTRIBUTORS ({len(dels)} with >= {MINV:,.0f} VESTS) and money sent back ===')
out['payback'] = []
for dg, de, v in dels:
    cur.execute(f"""SELECT {YEAR}, symbol, SUM(amount), COUNT(*) FROM hafsql.operation_transfer_table
                    WHERE from_account=%s AND to_account=%s AND id >= %s GROUP BY 1,2 ORDER BY 1""", (de, dg, SINCE_ID))
    rows = cur.fetchall()
    per = C.defaultdict(C.Counter)
    for y, s, a, n in rows: per[y][S(s)] += float(a)
    txt = '  '.join(f'{y}: {p.get("HIVE",0):,.0f} HIVE {p.get("HBD",0):,.0f} HBD' for y, p in sorted(per.items())) or 'nothing sent back'
    print(f'  {dg:<18} → {de:<16} {float(v)/1604:>12,.0f} HP   back: {txt}')
    out['payback'].append([dg, de, float(v), {y: dict(p) for y, p in per.items()}])

# B) paid votes: memo is a post link
print('\n=== B) PAID VOTES: transfers whose memo is a Hive post link, per service and year ===')
cur.execute(f"""SELECT to_account, {YEAR}, symbol, SUM(amount), COUNT(*), COUNT(DISTINCT from_account) FROM hafsql.operation_transfer_table
                WHERE id >= %s AND memo ~* '^\\s*https?://(www\\.)?(peakd\\.com|hive\\.blog|ecency\\.com|steemit\\.com)/.*@[a-z0-9.-]+/[a-z0-9-]+'
                GROUP BY 1,2,3""", (SINCE_ID,))
svc = C.defaultdict(lambda: C.defaultdict(C.Counter))
for to, y, s, a, n, b in cur.fetchall(): svc[to][y][S(s)] += float(a); svc[to][y]['n'] += n; svc[to][y]['buyers'] += b
rank = sorted(svc, key=lambda t: -sum(p.get('HIVE', 0) + p.get('HBD', 0) for p in svc[t].values()))[:15]
for t in rank:
    print(f'  {t:<18} ' + '  '.join(f'{y}: {p.get("HIVE",0):,.0f} HIVE {p.get("HBD",0):,.0f} HBD ({int(p["n"])} bids)' for y, p in sorted(svc[t].items())))
out['paid_votes'] = {t: {y: dict(p) for y, p in svc[t].items()} for t in rank}
if rank:
    cur.execute(f"""SELECT from_account, SUM(amount), COUNT(*) FROM hafsql.operation_transfer_table
                    WHERE to_account = ANY(%s) AND id >= %s AND memo ~* '^\\s*https?://.*@[a-z0-9.-]+/' GROUP BY 1 ORDER BY 2 DESC LIMIT 20""", (rank[:5], SINCE_ID))
    print('  top buyers of votes (all services above, HIVE+HBD):')
    for a, x, n in cur.fetchall(): print(f'     {a:<18} {float(x):>12,.0f}  ({n} bids)')

# C) where the distributors' money goes
print('\n=== C) OUTGOING MONEY OF THE TOP 30 DISTRIBUTORS since 2020 (top 5 destinations each) ===')
out['outgoing'] = {}
for d in dist:
    cur.execute("""SELECT to_account, symbol, SUM(amount) FROM hafsql.operation_transfer_table
                   WHERE from_account=%s AND id >= %s GROUP BY 1,2 ORDER BY 3 DESC LIMIT 5""", (d, SINCE_ID))
    r = cur.fetchall(); out['outgoing'][d] = [[a, S(s), float(x)] for a, s, x in r]
    print(f'  {d:<16} ' + ', '.join(f'{a} {float(x):,.0f} {S(s)}' for a, s, x in r))
json.dump(out, open('money_trail.json', 'w'), indent=1, default=str)
print('\nSaved money_trail.json')
