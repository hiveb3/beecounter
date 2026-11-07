#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter whale check - where the stake of the biggest Hive accounts comes from (HAFSQL, public data, 2020-03-20 → today):
#   power ups (own / from others), money in and out by counterparty (exchanges flagged), power downs,
#   author / curation / witness rewards, delegations in and out, and delegations between whales.
# Measures, does not accuse.
# Usage: python3 whale_check.py [top=30] [since=2020-03-20]      -> whales_report.txt-style output + whales.json
import sys, json, datetime as dt, collections as C
TOP = int(sys.argv[1]) if len(sys.argv) > 1 else 30
SINCE = sys.argv[2] if len(sys.argv) > 2 else '2020-03-20'
EXCHANGES = {'binance-hot', 'bdhivesteem', 'deepcrypto8', 'huobi-pro', 'upbit-exchange', 'user.dunamu', 'bittrex', 'ionomy',
             'gateiohive', 'mxchive', 'hive-engine', 'honey-swap', 'blocktrades', 'probitred', 'probithive', 'bithumb.hot',
             'hiveswap', 'swap-eth', 'bitget-hive', 'hotbit', 'coinbasebase', 'wazirx', 'okex-hive', 'leodex', 'steemit2hive'}

import psycopg2
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '1800s'"); cur.execute("SET TIME ZONE 'UTC'")

# ---------- schema discovery: HAFSQL view/column names are found at run time, not guessed ----------
cur.execute("""SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='hafsql'""")
COLS = C.defaultdict(list)
for t, c in cur.fetchall(): COLS[t].append(c)
def table(*words, avoid=()):
    for t in sorted(COLS, key=len):
        if all(w in t for w in words) and not any(a in t for a in avoid): return t
    return None
def col(t, *cands):
    for c in cands:
        if c in COLS[t]: return c
    for c in cands:
        for x in COLS[t]:
            if c in x: return x
    return None
print('HAFSQL views with "transfer", "vesting", "deleg", "reward", "balance":')
for t in sorted(COLS):
    if any(w in t for w in ('transfer', 'vesting', 'deleg', 'reward', 'balance')): print('  ', t, COLS[t][:12])

def q(sql, args=()):
    try:
        cur.execute(sql, args); return cur.fetchall()
    except Exception as e:
        print('  [query failed]', str(e).splitlines()[0]); con.rollback() if not con.autocommit else None; return []

# ---------- 1. who are the whales: biggest own vesting today ----------
BAL = table('balances') or table('balance')
acc_c = col(BAL, 'account_name', 'account', 'name'); vests_c = col(BAL, 'vests', 'vesting_shares')
hp_c = col(BAL, 'hp', 'hive_power')
whales = [r[0] for r in q(f'SELECT {acc_c} FROM hafsql.{BAL} ORDER BY {vests_c} DESC NULLS LAST LIMIT %s', (TOP,))]
cur_bal = {r[0]: r[1:] for r in q(f'SELECT {acc_c}, {vests_c}{", " + hp_c if hp_c else ""} FROM hafsql.{BAL} WHERE {acc_c} = ANY(%s)', (whales,))}
print(f'\n=== TOP {TOP} ACCOUNTS BY OWN STAKE (today) ===')
for w in whales: print(f'  {w:<20} {cur_bal.get(w)}')

# ---------- 1b. who distributes the rewards: biggest upvoters by rshares, last 30 days (own stake + delegations received) ----------
VT = 'operation_effective_comment_vote_view'
d30 = (dt.datetime.utcnow() - dt.timedelta(days=30)).strftime('%Y-%m-%d')
dist = q(f'SELECT voter, SUM(rshares) AS rs, COUNT(*) FROM hafsql.{VT} WHERE timestamp >= %s AND rshares > 0 '
         f'GROUP BY voter ORDER BY rs DESC LIMIT %s', (d30, TOP))
tot_rs = q(f'SELECT SUM(rshares) FROM hafsql.{VT} WHERE timestamp >= %s AND rshares > 0', (d30,))
tot_rs = float(tot_rs[0][0] or 1) if tot_rs else 1
print(f'\n=== TOP {TOP} REWARD DISTRIBUTORS (share of all upvote power, last 30 days) ===')
acc = 0
for v, rs, n in dist:
    acc += float(rs)
    print(f'  {v:<20} {float(rs)/tot_rs:6.2%}  (cumulative {acc/tot_rs:6.1%})  {n} votes  {"[also a whale]" if v in whales else ""}')
whales += [v for v, _, _ in dist if v not in whales]
cur_bal.update({r[0]: r[1:] for r in q(f'SELECT {acc_c}, {vests_c}{", " + hp_c if hp_c else ""} FROM hafsql.{BAL} WHERE {acc_c} = ANY(%s)', (whales,))})
print(f'→ analysing {len(whales)} accounts: biggest stakes + biggest reward distributors')

def flows(view_words, from_words, to_words, extra_avoid=()):
    t = table(*view_words, avoid=('fill', 'withdraw_route') + extra_avoid)
    if not t: print('  [no view for', view_words, ']'); return None, None, None, None, None
    return t, col(t, *from_words), col(t, *to_words), col(t, 'amount', 'vesting_shares', 'reward'), col(t, 'symbol', 'nai', 'asset')

TS = lambda t: col(t, 'timestamp', 'created_at', 'block_time')
out = {w: {} for w in whales}

# ---------- 2. power ups ----------
t, f, to, am, sym = flows(('transfer_to_vesting',), ('from_account', 'from'), ('to_account', 'to'))
print(f'\n=== POWER UPS since {SINCE} (HIVE) — own vs received from others === [{t}]')
if t:
    for w in whales:
        rows = q(f'SELECT {f}, SUM({am}) FROM hafsql.{t} WHERE {to}=%s AND {TS(t)}>=%s GROUP BY {f} ORDER BY 2 DESC', (w, SINCE))
        own = sum(float(x[1]) for x in rows if x[0] == w); oth = [(x[0], float(x[1])) for x in rows if x[0] != w]
        out[w]['powerup_own'] = own; out[w]['powerup_from_others'] = oth[:5]
        print(f'  {w:<20} own {own:14,.0f}   from others {sum(x[1] for x in oth):12,.0f}  ' + ', '.join(f'{a} {x:,.0f}' for a, x in oth[:3]))

# ---------- 3. transfers in / out by counterparty ----------
t, f, to, am, sym = flows(('transfer',), ('from_account', 'from'), ('to_account', 'to'),
                          extra_avoid=('vesting', 'savings', 'recurrent', 'escrow', 'convert'))
print(f'\n=== LIQUID TRANSFERS since {SINCE} — biggest sources and destinations (⚑ = exchange) === [{t}]')
if t:
    for w in whales:
        ins = q(f'SELECT {f}, {sym}, SUM({am}) FROM hafsql.{t} WHERE {to}=%s AND {TS(t)}>=%s GROUP BY 1,2 ORDER BY 3 DESC LIMIT 8', (w, SINCE))
        outs = q(f'SELECT {to}, {sym}, SUM({am}) FROM hafsql.{t} WHERE {f}=%s AND {TS(t)}>=%s GROUP BY 1,2 ORDER BY 3 DESC LIMIT 8', (w, SINCE))
        fl = lambda a: '⚑' if a in EXCHANGES else ''
        out[w]['in'] = [[a, s, float(x)] for a, s, x in ins]; out[w]['out'] = [[a, s, float(x)] for a, s, x in outs]
        print(f'  {w}')
        print('     IN : ' + ', '.join(f'{fl(a)}{a} {float(x):,.0f} {s}' for a, s, x in ins[:6]))
        print('     OUT: ' + ', '.join(f'{fl(a)}{a} {float(x):,.0f} {s}' for a, s, x in outs[:6]))

# ---------- 4. power downs ----------
t = table('fill_vesting_withdraw')
print(f'\n=== POWER DOWNS since {SINCE} (HIVE actually withdrawn) === [{t}]')
if t:
    fa, ta, dep = col(t, 'from_account', 'from'), col(t, 'to_account', 'to'), col(t, 'deposited', 'amount')
    for w in whales:
        r = q(f'SELECT SUM({dep}) FROM hafsql.{t} WHERE {fa}=%s AND {TS(t)}>=%s', (w, SINCE))
        out[w]['powerdown'] = float(r[0][0] or 0) if r else 0
        print(f'  {w:<20} {out[w]["powerdown"]:14,.0f}')

# ---------- 5. rewards earned on Hive ----------
print(f'\n=== REWARDS EARNED since {SINCE} (in VESTS: author / curation / witness) ===')
for name, words, acc_words, amt_words in [('author', ('author_reward',), ('author',), ('vesting_payout', 'vesting')),
                                          ('curation', ('curation_reward',), ('curator',), ('reward',)),
                                          ('witness', ('producer_reward',), ('producer',), ('vesting_shares', 'vesting'))]:
    t = table(*words, avoid=('comment_',))
    if not t: print('  [no view for', name, ']'); continue
    a, v = col(t, *acc_words), col(t, *amt_words)
    for row in q(f'SELECT {a}, SUM({v}) FROM hafsql.{t} WHERE {a} = ANY(%s) AND {TS(t)}>=%s GROUP BY 1', (whales, SINCE)):
        out[row[0]][name] = float(row[1] or 0)
for w in whales:
    print(f'  {w:<20} author {out[w].get("author", 0):16,.0f}  curation {out[w].get("curation", 0):16,.0f}  witness {out[w].get("witness", 0):16,.0f}')

# ---------- 6. delegations: current, and between whales ----------
t = table('delegations', avoid=('operation',)) or table('delegate_vesting_shares')
print(f'\n=== DELEGATIONS (current) === [{t}]')
if t:
    dg, de, vs = col(t, 'delegator'), col(t, 'delegatee'), col(t, 'vests', 'vesting_shares')
    rows = q(f'SELECT {dg}, {de}, {vs} FROM hafsql.{t} WHERE ({dg} = ANY(%s) OR {de} = ANY(%s)) AND {vs} > 0', (whales, whales))
    gin, gout = C.defaultdict(list), C.defaultdict(list); between = []
    for a, b, v in rows:
        v = float(v)
        if a in out: gout[a].append((b, v))
        if b in out: gin[b].append((a, v))
        if a in out and b in out: between.append((a, b, v))
    for w in whales:
        i, o = sorted(gin[w], key=lambda x: -x[1]), sorted(gout[w], key=lambda x: -x[1])
        out[w]['deleg_in'] = i[:10]; out[w]['deleg_out'] = o[:10]
        print(f'  {w:<20} IN {sum(x[1] for x in i):16,.0f} from {len(i):<4} OUT {sum(x[1] for x in o):16,.0f} to {len(o):<4}'
              + ('  top in: ' + ', '.join(f'{a} {x:,.0f}' for a, x in i[:3]) if i else ''))
    print('\n=== DELEGATIONS BETWEEN WHALES ===')
    for a, b, v in sorted(between, key=lambda x: -x[2]): print(f'  {a} → {b}  {v:,.0f} VESTS')
    recip = {(a, b) for a, b, _ in between}
    for a, b in sorted(recip):
        if (b, a) in recip and a < b: print(f'  ⇄ crossed: {a} ⇄ {b}')
    out['_between'] = between

json.dump(out, open('whales.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('\nSaved whales.json')
