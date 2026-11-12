#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
"""BeeCounter supply snapshot: reads HIVE/HBD supply from OUR OWN hived node (no HAFSQL, no public API)
and saves it in supply/YYYY-MM-DD.json. Run daily at 00:00 UTC by a systemd timer; the Monthly Ledger uses
the snapshots of the 1st of two consecutive months as an independent check of the supply change.
Usage: python3 supply_snapshot.py [NODE_URL]   (default http://127.0.0.1:8091)"""
import sys, os, json, datetime as dt, urllib.request

NODE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BEECOUNTER_NODE", "http://127.0.0.1:8091")
def rpc(method, params):
    req = urllib.request.Request(NODE, method="POST", headers={"Content-Type": "application/json"},
          data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode())
    r = json.load(urllib.request.urlopen(req, timeout=20))
    if "result" not in r: raise RuntimeError(r)
    return r["result"]
amt = lambda a: int(a["amount"]) / 10 ** a["precision"] if isinstance(a, dict) else float(str(a).split()[0])
g = rpc("database_api.get_dynamic_global_properties", {})
snap = {"node": NODE, "taken_utc": dt.datetime.utcnow().isoformat(timespec="seconds"), "block": g["head_block_number"], "block_time": g["time"],
        "current_supply": amt(g["current_supply"]), "current_hbd_supply": amt(g["current_hbd_supply"]),
        "virtual_supply": amt(g["virtual_supply"]), "total_vesting_fund_hive": amt(g["total_vesting_fund_hive"]),
        "total_vesting_shares": amt(g["total_vesting_shares"]), "hbd_interest_rate": g.get("hbd_interest_rate")}
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "supply"), exist_ok=True)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supply", g["time"][:10] + ".json")
if not os.path.exists(path):                 # keep the FIRST snapshot of each day (closest to 00:00 UTC)
    json.dump(snap, open(path, "w"), indent=1)
print(json.dumps(snap))
