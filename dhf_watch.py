#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter DHF Watch - where the HBD paid by the DHF went, proposal by proposal (HAFSQL data).
Usage: python3 dhf_watch.py 2026-10      -> dhf_2026-10.json
On-chain flows only: an exchange deposit or a transfer can be perfectly legitimate (paying people off-chain)."""
import sys, json, datetime as dt, collections as C, psycopg2

M = sys.argv[1] if len(sys.argv) > 1 else (dt.date.today().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
D0 = dt.datetime.fromisoformat(M + "-01"); D1 = (D0 + dt.timedelta(days=32)).replace(day=1)
# known exchange / bridge deposit accounts (edit freely)
EXCHANGES = {"bdhivesteem": "Binance", "deepcrypto8": "Binance", "bitgethive": "Bitget", "user.dunamu": "Upbit", "huobi-pro": "HTX", "gateiodeposit": "Gate.io",
             "mxchive": "MEXC", "probitred": "ProBit", "blocktrades": "BlockTrades", "honey-swap": "Hive-Engine"}
SKIP = {"steem.dao"}                                  # return proposal: money stays in the treasury
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '900s'"); cur.execute("SET TIME ZONE 'UTC'")
out = {"month": M, "errors": {}, "exchanges": EXCHANGES}
f = lambda x: float(x or 0)

def q(name, sql, params=()):
    try:
        cur.execute(sql, params); return cur.fetchall()
    except Exception as e:
        out["errors"][name] = str(e).splitlines()[0][:300]; print("ERROR", name, out["errors"][name], flush=True); return None

def first_block(t):
    r = q("dgp_block", "SELECT block_num, timestamp FROM hafsql.dynamic_global_properties WHERE timestamp >= %s ORDER BY timestamp LIMIT 1", (t,))
    if r and r[0][1] < t + dt.timedelta(hours=1): return r[0][0]
    r = q("vote_block", "SELECT min(block_num) FROM hafsql.operation_effective_comment_vote_view WHERE timestamp >= %s AND timestamp < %s",
          (t, t + dt.timedelta(minutes=10)))
    return r[0][0] if r and r[0][0] else None

B0, B1 = first_block(D0), first_block(D1); out["blocks"] = [B0, B1]
R = (B0 << 32, B1 << 32)
pays = q("pay", """SELECT receiver, proposal_id, sum(payment), count(*) FROM hafsql.operation_proposal_pay_table
                   WHERE id >= %s AND id < %s GROUP BY 1,2 ORDER BY 3 DESC""", R) or []
props = {}
for rcv, pid, amt, n in pays:
    if rcv in SKIP: continue
    p = props.setdefault(rcv, {"receiver": rcv, "proposals": [], "received": 0.0})
    p["proposals"].append(int(pid)); p["received"] += f(amt)
ids = sorted({i for p in props.values() for i in p["proposals"]})
# proposal titles and creators (latest update wins, else creation)
info = {}
r = q("upd", """SELECT DISTINCT ON (proposal_id) proposal_id, creator, subject, permlink, daily_pay
                FROM hafsql.operation_update_proposal_table WHERE proposal_id = ANY(%s) ORDER BY proposal_id, id DESC""", (ids,))
for pid, cr, sub, pl, dp in r or []: info[int(pid)] = dict(creator=cr, subject=sub, permlink=pl, daily=f(dp))
r = q("create", """SELECT creator, receiver, subject, permlink, daily_pay, start_date, end_date
                   FROM hafsql.operation_create_proposal_table WHERE receiver = ANY(%s) ORDER BY id""", (list(props),))
created = C.defaultdict(list)
for cr, rc, sub, pl, dp, sd, ed in r or []: created[rc].append(dict(creator=cr, subject=sub, permlink=pl, daily=f(dp), start=str(sd)[:10], end=str(ed)[:10]))
for p in props.values():
    p["info"] = [info.get(i) for i in p["proposals"]]
    p["created"] = created.get(p["receiver"], [])[-3:]

accs = list(props)
def agg(name, sql):
    r = q(name, sql, (accs, *R)); return r or []
for acc, to, sym, amt, n in agg("transfers", """SELECT from_account, to_account, symbol, sum(amount), count(*) FROM hafsql.operation_transfer_table
                                              WHERE from_account = ANY(%s) AND id >= %s AND id < %s GROUP BY 1,2,3"""):
    props[acc].setdefault("out", []).append([to, sym, round(f(amt), 3), n, EXCHANGES.get(to, "")])
for acc, to, sym, amt, n in agg("recurrent", """SELECT from_account, to_account, symbol, sum(amount), count(*) FROM hafsql.operation_fill_recurrent_transfer_table
                                              WHERE from_account = ANY(%s) AND id >= %s AND id < %s GROUP BY 1,2,3"""):
    props[acc].setdefault("out", []).append([to, sym, round(f(amt), 3), n, EXCHANGES.get(to, "") or "recurrent"])
for acc, sym, amt in agg("savings", """SELECT from_account, symbol, sum(amount) FROM hafsql.operation_transfer_to_savings_table
                                     WHERE from_account = ANY(%s) AND id >= %s AND id < %s GROUP BY 1,2"""):
    props[acc].setdefault("to_savings", {})[sym] = round(f(amt), 3)
for acc, sym, amt in agg("from_savings", """SELECT from_account, symbol, sum(amount) FROM hafsql.operation_fill_transfer_from_savings_table
                                          WHERE from_account = ANY(%s) AND id >= %s AND id < %s GROUP BY 1,2"""):
    props[acc].setdefault("from_savings", {})[sym] = round(f(amt), 3)
for acc, amt in agg("powerup", """SELECT from_account, sum(amount) FROM hafsql.operation_transfer_to_vesting_table
                                WHERE from_account = ANY(%s) AND id >= %s AND id < %s GROUP BY 1"""):
    props[acc]["powered_up_hive"] = round(f(amt), 3)
for acc, ain, aout in agg("convert", """SELECT owner, sum(amount_in), sum(amount_out) FROM hafsql.operation_fill_convert_request_table
                                      WHERE owner = ANY(%s) AND id >= %s AND id < %s GROUP BY 1"""):
    props[acc]["converted_hbd_to_hive"] = [round(f(ain), 3), round(f(aout), 3)]
for acc, sym, amt in agg("market", """SELECT current_owner, current_pays_symbol, sum(current_pays) FROM hafsql.operation_fill_order_table
                                    WHERE current_owner = ANY(%s) AND id >= %s AND id < %s GROUP BY 1,2"""):
    props[acc].setdefault("market_sold", {})[sym] = round(f(amt), 3)
for acc, sym, amt in agg("market2", """SELECT open_owner, open_pays_symbol, sum(open_pays) FROM hafsql.operation_fill_order_table
                                     WHERE open_owner = ANY(%s) AND id >= %s AND id < %s GROUP BY 1,2"""):
    d = props[acc].setdefault("market_sold", {}); d[sym] = round(d.get(sym, 0) + f(amt), 3)
# balances at start and end of month (slow on the public server: enable with DHF_BALANCES=1)
import os
for tag, b in [] if os.environ.get("DHF_BALANCES") != "1" else (("start", B0), ("end", B1)):
    r = q("bal_" + tag, """SELECT DISTINCT ON (account_name) account_name, hbd, hbd_savings, hive, hive_savings, vests
                           FROM hafsql.balances_history WHERE account_name = ANY(%s) AND block_num <= %s
                           ORDER BY account_name, block_num DESC""", (accs, b))
    for acc, hbd, hbds, hive, hives, vests in r or []:
        props[acc]["bal_" + tag] = dict(hbd=f(hbd), hbd_savings=f(hbds), hive=f(hive), hive_savings=f(hives), vests=f(vests))
# reporting: top-level posts by the receiver and the proposal creators in the month
authors = sorted({a for p in props.values() for a in [p["receiver"]] + [i["creator"] for i in p["info"] if i]})
r = q("posts", """SELECT author, count(*), max(created), string_agg(left(title, 70), ' | ' ORDER BY created DESC)
                  FROM hafsql.comments WHERE parent_author = '' AND author = ANY(%s) AND created >= %s AND created < %s
                  GROUP BY 1""", (authors, D0, D1))
posts = {a: dict(n=n, last=str(last)[:10], titles=(t or "")[:400]) for a, n, last, t in r or []}
r = q("lastpost", """SELECT author, max(created) FROM hafsql.comments WHERE parent_author = '' AND author = ANY(%s) GROUP BY 1""", (authors,))
lastpost = {a: str(t)[:10] for a, t in r or []}
for p in props.values():
    who = [p["receiver"]] + [i["creator"] for i in p["info"] if i]
    p["reporting"] = {a: dict(posts_in_month=posts.get(a, {}).get("n", 0), last_post=lastpost.get(a, "never"),
                              titles=posts.get(a, {}).get("titles", "")) for a in dict.fromkeys(who)}
    o = p.get("out", []); hbd_out = sum(x[2] for x in o if x[1] == "HBD")
    p["summary"] = dict(hbd_out=round(hbd_out, 3), hbd_to_exchanges=round(sum(x[2] for x in o if x[1] == "HBD" and x[4] and x[4] != "recurrent"), 3),
                        top_destinations=sorted(o, key=lambda x: -x[2])[:8])
out["proposals"] = sorted(props.values(), key=lambda p: -p["received"])
json.dump(out, open(f"dhf_{M}.json", "w"), ensure_ascii=False, default=str)
print(json.dumps(out, ensure_ascii=False, default=str))
