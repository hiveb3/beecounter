#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter cross-check: compares HAFSQL with the blockchain itself (public API nodes).
1) N random blocks of the month: every reward/DHF/HBD virtual operation, summed by type, HAFSQL vs chain.
2) The top posts of the Ledger: payout in HAFSQL vs condenser_api.get_content.
Usage: python3 verify.py 2026-10 [N_BLOCKS=150]      (read-only, a few minutes)"""
import sys, json, random, time, datetime as dt, urllib.request, collections as C, psycopg2

M = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 150
NODES = ["https://api.hive.blog", "https://api.deathwing.me", "https://api.openhive.network"]
D0 = dt.datetime.fromisoformat(M + "-01"); D1 = (D0 + dt.timedelta(days=32)).replace(day=1)
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True); cur = con.cursor(); cur.execute("SET TIME ZONE 'UTC'")

def rpc(method, params, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(NODES[i % len(NODES)], method="POST", headers={"Content-Type": "application/json"},
                  data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode())
            r = json.load(urllib.request.urlopen(req, timeout=20))
            if "result" in r: return r["result"]
        except Exception: pass
        time.sleep(1 + i)
    raise RuntimeError(f"rpc failed: {method}")

def amt(a):
    """'1.234 HIVE' or {'amount':'1234','precision':3,'nai':...} -> float"""
    if isinstance(a, dict): return int(a["amount"]) / 10 ** a["precision"]
    return float(str(a).split()[0])

def block_at(t):
    cur.execute("SELECT min(block_num) FROM hafsql.operation_effective_comment_vote_view WHERE timestamp >= %s AND timestamp < %s",
                (t, t + dt.timedelta(minutes=10)))
    return cur.fetchone()[0]

B0, B1 = block_at(D0), block_at(D1)
random.seed(M); blocks = sorted(random.sample(range(B0, B1), N))
print(f"Month {M}: blocks {B0:,} .. {B1:,} · checking {N} random blocks\n", flush=True)

# what to compare: chain op type -> (HAFSQL table, [(chain field, hafsql column)])
CHECK = {
    "producer_reward_operation": ("operation_producer_reward_table", [("vesting_shares", "vesting_shares")]),
    "author_reward_operation": ("operation_author_reward_table", [("hbd_payout", "hbd_payout"), ("hive_payout", "hive_payout"), ("vesting_payout", "vesting_payout")]),
    "curation_reward_operation": ("operation_curation_reward_table", [("reward", "reward")]),
    "comment_benefactor_reward_operation": ("operation_comment_benefactor_reward_table", [("hbd_payout", "hbd_payout"), ("hive_payout", "hive_payout"), ("vesting_payout", "vesting_payout")]),
    "interest_operation": ("operation_interest_table", [("interest", "interest")]),
    "fill_convert_request_operation": ("operation_fill_convert_request_table", [("amount_in", "amount_in"), ("amount_out", "amount_out")]),
    "proposal_pay_operation": ("operation_proposal_pay_table", [("payment", "payment")]),
    "dhf_funding_operation": ("operation_dhf_funding_table", [("additional_funds", "additional_funds")]),
    "dhf_conversion_operation": ("operation_dhf_conversion_table", [("hive_amount_in", "hive_amount_in"), ("hbd_amount_out", "hbd_amount_out")]),
}
chain, sql, nops = C.Counter(), C.Counter(), C.Counter()
bad_blocks = []
for i, b in enumerate(blocks):
    res = rpc("account_history_api.get_ops_in_block", {"block_num": b, "only_virtual": True, "include_reversible": False})
    cb = C.Counter()
    for o in res.get("ops", []):
        t = o["op"]["type"]; v = o["op"]["value"]
        if t in CHECK:
            nops[t] += 1
            for cf, _ in CHECK[t][1]: cb[(t, cf)] += amt(v[cf])
    sb = C.Counter()
    for t, (table, cols) in CHECK.items():
        cur.execute(f"SELECT {', '.join('coalesce(sum(' + c + '),0)' for _, c in cols)} FROM hafsql.{table} WHERE id >= %s AND id < %s",
                    (b << 32, (b + 1) << 32))
        row = cur.fetchone()
        for (cf, _), val in zip(cols, row): sb[(t, cf)] += float(val or 0)
    for k in set(cb) | set(sb):
        chain[k] += cb[k]; sql[k] += sb[k]
        if abs(cb[k] - sb[k]) > 0.002: bad_blocks.append((b, k, cb[k], sb[k]))
    if (i + 1) % 25 == 0: print(f"  {i + 1}/{N} blocks checked", flush=True)
    time.sleep(0.15)

print("\n== 1) Virtual operations in the sampled blocks (chain vs HAFSQL)")
print(f"{'operation / field':52} {'ops':>6} {'chain':>16} {'HAFSQL':>16}  result")
ok = True
for t, (_, cols) in CHECK.items():
    for cf, _ in cols:
        c, s = chain[(t, cf)], sql[(t, cf)]; same = abs(c - s) <= 0.002 * max(1, N / 50)
        ok &= same
        print(f"{t.replace('_operation', '') + ' · ' + cf:52} {nops[t]:>6} {c:>16,.3f} {s:>16,.3f}  {'OK' if same else 'DIFF'}")
if bad_blocks:
    print("\nBlocks with a difference (first 10):")
    for x in bad_blocks[:10]: print("  ", x)

# 2) top posts of the Ledger
print("\n== 2) Top posts: payout in HAFSQL vs chain (condenser_api.get_content)")
try:
    d = json.load(open(f"out/ledger-{M}/content/data.json"))
    rows = d["topPay"][:10]
except Exception as e:
    rows = []; print("  (Ledger data not found, skipped:", e, ")")
print(f"{'post':50} {'HAFSQL total':>13} {'chain total+cur':>16} {'HAFSQL ben':>11}  result")
for r in rows:
    c = rpc("condenser_api.get_content", [r["a"], r["p"]])
    ch = amt(c["total_payout_value"]) + amt(c["curator_payout_value"])
    cur.execute("SELECT total_payout_value, curator_payout_value, beneficiary_payout_value FROM hafsql.comments WHERE author=%s AND permlink=%s",
                (r["a"], r["p"]))
    tpv, cpv, bpv = [float(x or 0) for x in cur.fetchone()]
    same = abs(ch - tpv) <= 0.01 or abs(ch - (tpv + cpv)) <= 0.01 or abs(ch - (tpv - bpv)) <= 0.01
    ok &= same
    print(f"{('@' + r['a'] + '/' + r['p'])[:50]:50} {tpv:>13.3f} {ch:>16.3f} {bpv:>11.3f}  {'OK' if same else 'CHECK'}")
    time.sleep(0.2)
print("\nRESULT:", "HAFSQL matches the blockchain on every sample ✅" if ok and not bad_blocks else "differences found ⚠️ (see above)")
