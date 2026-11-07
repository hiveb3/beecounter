#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter exchange flow - how much HIVE/HBD the biggest accounts sent to exchanges, year by year (HAFSQL, public data).
#   A) today's top N stakes: HIVE and HBD sent to exchanges per year
#   B) the top N senders of HIVE and the top N senders of HBD to exchanges (whoever they are), per year
#   C) totals per year for the whole chain, and per exchange
# Measures, does not accuse: sending to an exchange can be a sale, but also a swap, a move to cold storage, or a service.
# Usage: python3 exchange_flow.py [top=30] [since=2020-03-20]    -> prints + exchange_flow.json
import sys, json, collections as C
TOP = int(sys.argv[1]) if len(sys.argv) > 1 else 30
SINCE = sys.argv[2] if len(sys.argv) > 2 else '2020-03-20'
EXCHANGES = ['binance-hot', 'bdhivesteem', 'deepcrypto8', 'huobi-pro', 'upbit-exchange', 'user.dunamu', 'bittrex', 'ionomy',
             'gateiohive', 'mxchive', 'probitred', 'probithive', 'bithumb.hot', 'bitget-hive', 'hotbit', 'wazirx', 'okex-hive',
             'blocktrades', 'hiveswap', 'swap-eth', 'coinbasebase', 'steemit2hive', 'kucoinhive', 'htx-hive', 'hive.coinex']

import psycopg2
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '3600s'"); cur.execute("SET TIME ZONE 'UTC'")

cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='hafsql'")
COLS = C.defaultdict(list)
for t, c in cur.fetchall(): COLS[t].append(c)
def table(*w, avoid=()):
    # prefer views that carry a timestamp column (HAFSQL has both bare tables and *_view with timestamp)
    for t in sorted(COLS, key=lambda t: (not any('timestamp' in c for c in COLS[t]), len(t))):
        if all(x in t for x in w) and not any(a in t for a in avoid): return t
def col(t, *cands):
    for c in cands:
        if c in COLS[t]: return c
    for c in cands:
        for x in COLS[t]:
            if c in x: return x
T = table('transfer', avoid=('vesting', 'savings', 'recurrent', 'escrow', 'convert', 'fill', 'route'))
F, TO, AM, SYM = col(T, 'from_account', 'from'), col(T, 'to_account', 'to'), col(T, 'amount'), col(T, 'symbol', 'nai', 'asset')
# operation_*_table views have no timestamp: HAF op id = block_num << 32; block time ≈ HF23 (block 41818752, 2020-03-20 14:00 UTC) + 3 s/block
TS = col(T, 'timestamp', 'created_at', 'block_time') or "to_timestamp(1584712800 + 3 * ((id >> 32) - 41818752))"
BAL = table('balances') or table('balance'); ACC, VESTS = col(BAL, 'account_name', 'account', 'name'), col(BAL, 'vests', 'vesting_shares')
print(f'transfers view: {T} ({F}, {TO}, {AM}, {SYM}, {TS}) · balances: {BAL} ({ACC}, {VESTS})')
out = {}
# symbol may come as text ('HIVE'/'HBD') or as NAI ('@@000000021' = HIVE, '@@000000013' = HBD)
def S(x):
    x = str(x).upper()
    return 'HIVE' if ('HIVE' in x or '000000021' in x or x == 'STEEM') else 'HBD' if ('HBD' in x or '000000013' in x or x == 'SBD') else x

def by_year(accounts):
    cur.execute(f"""SELECT {F}, EXTRACT(YEAR FROM {TS})::int, {SYM}, SUM({AM}) FROM hafsql.{T}
                    WHERE {F} = ANY(%s) AND {TO} = ANY(%s) AND {TS} >= %s GROUP BY 1,2,3""", (accounts, EXCHANGES, SINCE))
    r = C.defaultdict(lambda: C.defaultdict(lambda: C.Counter()))
    for a, y, s, x in cur.fetchall(): r[a][y][S(s)] += float(x)
    return r

def show(title, accounts, data):
    years = sorted({y for a in data for y in data[a]})
    print(f'\n=== {title} — HIVE sent to exchanges per year, HBD in brackets ===')
    print(f'  {"account":<20}' + ''.join(f'{y:>20}' for y in years) + f'{"TOTAL HIVE":>16}{"TOTAL HBD":>14}')
    rows = []
    for a in accounts:
        tot = sum(data[a][y].get('HIVE', 0) for y in years); totd = sum(data[a][y].get('HBD', 0) for y in years)
        rows.append((tot + totd, tot, totd, a))
    for _, tot, totd, a in sorted(rows, reverse=True):
        cells = ''
        for y in years:
            h, d = data[a][y].get('HIVE', 0), data[a][y].get('HBD', 0)
            cells += f'{(f"{h:,.0f}" + (f" ({d:,.0f})" if d >= 1 else "")) if h or d else "-":>20}'
        print(f'  {a:<20}{cells}{tot:>16,.0f}{totd:>14,.0f}')
    return {a: {y: dict(v) for y, v in data[a].items()} for a in accounts}

# A) today's biggest stakes
cur.execute(f'SELECT {ACC} FROM hafsql.{BAL} WHERE NOT ({ACC} = ANY(%s)) ORDER BY {VESTS} DESC NULLS LAST LIMIT %s', (EXCHANGES, TOP))
whales = [r[0] for r in cur.fetchall()]
out['whales'] = show(f'A) TOP {TOP} STAKES TODAY', whales, by_year(whales))

# B) biggest senders to exchanges of all time
cur.execute(f"""SELECT {F}, {SYM}, SUM({AM}) FROM hafsql.{T} WHERE {TO} = ANY(%s) AND NOT ({F} = ANY(%s))
                AND {TS} >= %s GROUP BY 1,2""", (EXCHANGES, EXCHANGES, SINCE))
best = {'HIVE': C.Counter(), 'HBD': C.Counter()}
for a, s_, x in cur.fetchall(): best.setdefault(S(s_), C.Counter())[a] += float(x)
senders = [a for a, _ in best['HIVE'].most_common(TOP)] + [a for a, _ in best['HBD'].most_common(TOP)]
senders = list(dict.fromkeys(senders))   # top senders of HIVE and top senders of HBD
out['senders'] = show(f'B) TOP {TOP} HIVE + TOP {TOP} HBD SENDERS TO EXCHANGES SINCE {SINCE}', senders, by_year(senders))
for s in senders:
    if s in whales: print(f'  ★ {s} is also among today\'s top stakes')

# C) whole chain per year and per exchange
cur.execute(f"""SELECT EXTRACT(YEAR FROM {TS})::int, {TO}, {SYM}, SUM({AM}) FROM hafsql.{T}
                WHERE {TO} = ANY(%s) AND NOT ({F} = ANY(%s)) AND {TS} >= %s GROUP BY 1,2,3""", (EXCHANGES, EXCHANGES, SINCE))
yr, ex = C.defaultdict(C.Counter), C.defaultdict(C.Counter)
for y, e, s, x in cur.fetchall(): yr[y][S(s)] += float(x); ex[e][S(s)] += float(x)
print('\n=== C) WHOLE HIVE: sent to exchanges per year ===')
for y in sorted(yr): print(f'  {y}  HIVE {yr[y].get("HIVE", 0):>16,.0f}   HBD {yr[y].get("HBD", 0):>14,.0f}')
print('\n=== per exchange (whole period) ===')
for e, v in sorted(ex.items(), key=lambda i: -i[1].get('HIVE', 0)):
    print(f'  {e:<18} HIVE {v.get("HIVE", 0):>16,.0f}   HBD {v.get("HBD", 0):>14,.0f}')
out['per_year'] = {y: dict(v) for y, v in yr.items()}; out['per_exchange'] = {e: dict(v) for e, v in ex.items()}
json.dump(out, open('exchange_flow.json', 'w'), indent=1, default=str)
print('\nSaved exchange_flow.json')
