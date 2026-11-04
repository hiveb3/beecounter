#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter - where the HIVE/HBD created in a month went (HAFSQL data).
Usage: python3 inflation.py 2026-10          -> inflation_2026-10.json
Each section is independent: if a query fails, the others go on and the error is stored in "errors"."""
import sys, json, datetime as dt, psycopg2

M = sys.argv[1] if len(sys.argv) > 1 else (dt.date.today().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
D0 = dt.datetime.fromisoformat(M + "-01")
D1 = (D0 + dt.timedelta(days=32)).replace(day=1)
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '900s'"); cur.execute("SET TIME ZONE 'UTC'")
out = {"month": M, "errors": {}}
f = lambda x: float(x or 0)

def q(name, sql, params=()):
    try:
        cur.execute(sql, params); return cur.fetchall()
    except Exception as e:
        out["errors"][name] = str(e).splitlines()[0][:300]; print("ERROR", name, out["errors"][name], flush=True)
        con.rollback() if not con.autocommit else None
        return None

def first_block(t):
    r = q("dgp_block", "SELECT block_num, timestamp FROM hafsql.dynamic_global_properties WHERE timestamp >= %s ORDER BY timestamp LIMIT 1", (t,))
    if r and r[0][1] < t + dt.timedelta(hours=1): return r[0][0]
    r = q("vote_block", """SELECT min(block_num) FROM hafsql.operation_effective_comment_vote_view
                           WHERE timestamp >= %s AND timestamp < %s""", (t, t + dt.timedelta(minutes=10)))
    return r[0][0] if r and r[0][0] else None

B0, B1 = first_block(D0), first_block(D1)
out["blocks"] = [B0, B1]
print("blocks", B0, B1, flush=True)
if not (B0 and B1): print(json.dumps(out)); sys.exit(1)
LO, HI = B0 << 32, B1 << 32          # in HAF the operation id = block number << 32 + position
R = (LO, HI)

# chain state at start and end of month (supply, vests)
def dgp(b):
    r = q("dgp_%d" % b, """SELECT block_num, timestamp, current_supply, current_hbd_supply, virtual_supply,
                                 total_vesting_fund_hive, total_vesting_shares, vests_per_hive, hbd_interest_rate, total_reward_fund_hive
                          FROM hafsql.dynamic_global_properties WHERE block_num <= %s ORDER BY block_num DESC LIMIT 1""", (b,))
    if not r: return None
    k = ["block", "time", "hive", "hbd", "virtual", "vest_hive", "vest_shares", "vests_per_hive", "hbd_apr", "reward_fund"]
    return {a: (str(v) if a == "time" else f(v)) for a, v in zip(k, r[0])}
s0, s1 = dgp(B0), dgp(B1)
out["dgp"] = [s0, s1]
if not s0 and not s1:   # table holds only the current row: use it for VESTS->HP
    r = q("dgp_now", "SELECT vests_per_hive, total_vesting_shares, total_vesting_fund_hive FROM hafsql.dynamic_global_properties ORDER BY block_num DESC LIMIT 1")
    if r: out["vests_per_hive_now"] = f(r[0][0]) or (f(r[0][1]) / f(r[0][2]) if f(r[0][2]) else 0)
vph = (s0 or s1 or {}).get("vests_per_hive") or out.get("vests_per_hive_now") or 0
if not vph and s0 and s0["vest_hive"]: vph = s0["vest_shares"] / s0["vest_hive"]
out["vests_per_hive"] = vph
V = lambda vests: vests / vph if vph else 0      # VESTS -> HP

# witness (10%)
r = q("producer", """SELECT producer, sum(vesting_shares), count(*) FROM hafsql.operation_producer_reward_table
                     WHERE id >= %s AND id < %s GROUP BY producer ORDER BY 2 DESC""", R)
if r:
    out["witness_total_hp"] = round(sum(V(f(x[1])) for x in r), 3); out["witness_blocks"] = sum(x[2] for x in r)
    out["witnesses"] = [[x[0], round(V(f(x[1])), 3), x[2]] for x in r[:30]]; out["n_witnesses"] = len(r)
r = q("missed", "SELECT producer, count(*) FROM hafsql.operation_producer_missed_table WHERE id >= %s AND id < %s GROUP BY 1 ORDER BY 2 DESC", R)
if r is not None: out["missed"] = [[a, b] for a, b in r[:15]]; out["missed_total"] = sum(b for _, b in r)

# DHF: inflows (10%) and outflows
r = q("dhf_funding", "SELECT symbol, sum(additional_funds), count(*) FROM hafsql.operation_dhf_funding_table WHERE id >= %s AND id < %s GROUP BY 1", R)
if r: out["dhf_funding"] = {a: round(f(b), 3) for a, b, _ in r}
r = q("dhf_conversion", "SELECT sum(hive_amount_in), sum(hbd_amount_out) FROM hafsql.operation_dhf_conversion_table WHERE id >= %s AND id < %s", R)
if r: out["dhf_conversion"] = [round(f(r[0][0]), 3), round(f(r[0][1]), 3)]
r = q("proposal_pay", """SELECT receiver, proposal_id, symbol, sum(payment), count(*) FROM hafsql.operation_proposal_pay_table
                         WHERE id >= %s AND id < %s GROUP BY 1,2,3 ORDER BY 4 DESC""", R)
if r:
    out["proposal_pay"] = [[a, int(p), s, round(f(x), 3)] for a, p, s, x, _ in r]
    ids = sorted({int(p) for _, p, *_ in r})
    t = q("proposal_subjects", """SELECT DISTINCT ON (c.receiver, c.subject) c.receiver, c.subject, c.daily_pay, c.creator
                                  FROM hafsql.operation_create_proposal_table c WHERE c.receiver = ANY(%s)""", ([x[0] for x in r],))
    if t: out["proposal_subjects"] = [[a, s, f(dp), cr] for a, s, dp, cr in t]
r = q("proposal_fee", "SELECT sum(fee) FROM hafsql.operation_proposal_fee_table WHERE id >= %s AND id < %s", R)
if r: out["proposal_fee"] = round(f(r[0][0]), 3)

# content rewards (65%): authors, curators, beneficiaries
r = q("author", """SELECT sum(hbd_payout), sum(hive_payout), sum(vesting_payout), count(*) FROM hafsql.operation_author_reward_table
                   WHERE id >= %s AND id < %s""", R)
if r: out["author"] = {"hbd": round(f(r[0][0]), 3), "hive": round(f(r[0][1]), 3), "hp": round(V(f(r[0][2])), 3), "n": r[0][3]}
r = q("curation", "SELECT sum(reward), count(*), count(DISTINCT curator) FROM hafsql.operation_curation_reward_table WHERE id >= %s AND id < %s", R)
if r: out["curation"] = {"hp": round(V(f(r[0][0])), 3), "n": r[0][1], "curators": r[0][2]}
r = q("benefactor", """SELECT sum(hbd_payout), sum(hive_payout), sum(vesting_payout), count(*) FROM hafsql.operation_comment_benefactor_reward_table
                       WHERE id >= %s AND id < %s""", R)
if r: out["benefactor"] = {"hbd": round(f(r[0][0]), 3), "hive": round(f(r[0][1]), 3), "hp": round(V(f(r[0][2])), 3), "n": r[0][3]}

# HBD: interest (new HBD) and conversions
r = q("interest", "SELECT sum(interest), count(DISTINCT owner) FROM hafsql.operation_interest_table WHERE id >= %s AND id < %s", R)
if r: out["hbd_interest"] = [round(f(r[0][0]), 3), r[0][1]]
r = q("interest_top", "SELECT owner, sum(interest) FROM hafsql.operation_interest_table WHERE id >= %s AND id < %s GROUP BY 1 ORDER BY 2 DESC LIMIT 10", R)
if r: out["hbd_interest_top"] = [[a, round(f(b), 3)] for a, b in r]
r = q("convert", """SELECT amount_in_symbol, sum(amount_in), sum(amount_out), count(*) FROM hafsql.operation_fill_convert_request_table
                    WHERE id >= %s AND id < %s GROUP BY 1""", R)
if r: out["convert_hbd_to_hive"] = [[a, round(f(b), 3), round(f(c), 3), n] for a, b, c, n in r]
r = q("collat", """SELECT sum(amount_in), sum(amount_out), sum(excess_collateral), count(*) FROM hafsql.operation_fill_collateralized_convert_request_table
                   WHERE id >= %s AND id < %s""", R)
if r: out["convert_hive_to_hbd"] = [round(f(r[0][0]), 3), round(f(r[0][1]), 3), round(f(r[0][2]), 3), r[0][3]]

json.dump(out, open(f"inflation_{M}.json", "w"), ensure_ascii=False, default=str)
print(json.dumps(out, ensure_ascii=False, default=str))
