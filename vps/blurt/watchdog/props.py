#!/usr/bin/env python3
# Prints the JSON params for cli_wallet update_witness_properties:
#   ["<account>", {<current witness props>, "new_signing_key": "<key>"}, <broadcast>]
# The chain validates account_creation_fee (and other props) on every witness_set_properties,
# so the current values are copied from the witness object and only the signing key changes.
# Usage: props.py <account> <new_signing_key> <true|false>
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
import json, sys, urllib.request
acc, key, bc = sys.argv[1], sys.argv[2], sys.argv[3] == 'true'
NODES = ['http://127.0.0.1:8191', 'https://blurt-rpc.saboin.com', 'https://rpc.beblurt.com']
for n in NODES:
    try:
        q = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'condenser_api.get_witness_by_account', 'params': [acc]}).encode()
        w = json.loads(urllib.request.urlopen(urllib.request.Request(n, q, {'Content-Type': 'application/json'}), timeout=15).read()).get('result')
        if w:
            break
    except Exception:
        continue
else:
    sys.exit('witness not found on any node')
props = {k: v for k, v in (w.get('props') or {}).items() if k != 'account_subsidy_budget' and k != 'account_subsidy_decay'}
props['key'] = w['signing_key']          # current key: authorizes the change
props['new_signing_key'] = key           # new key: the null key disables block production
print(json.dumps([acc, props, bc]))
