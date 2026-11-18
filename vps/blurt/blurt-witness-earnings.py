#!/usr/bin/env python3
# Blurt witness earnings: counts produced blocks and producer rewards for a witness.
# Usage: python3 blurt-witness-earnings.py [account]   (default: blurtbee)
# Writes a report to /root/beecounter/blurt_witness.txt (readable via bee-mailbox "report").
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
import json, sys, os, urllib.request, collections, datetime as dt

ACC = sys.argv[1] if len(sys.argv) > 1 else 'blurtbee'
NODES = ['http://127.0.0.1:8091', 'https://rpc.blurt.world', 'https://blurt-rpc.saboin.com', 'https://rpc.beblurt.com']
OUT = '/root/beecounter/blurt_witness.txt'

def rpc(method, params, node=None):
    last = None
    for n in ([node] if node else NODES):
        try:
            body = json.dumps({'jsonrpc': '2.0', 'method': method, 'params': params, 'id': 1}).encode()
            req = urllib.request.Request(n, body, {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if 'result' in d:
                return d['result'], n
            last = d.get('error')
        except Exception as e:
            last = e
    raise SystemExit(f'all nodes failed: {last}')

wit, node = rpc('condenser_api.get_witness_by_account', [ACC])
dgp, _ = rpc('condenser_api.get_dynamic_global_properties', [], node)
fund_key = next(k for k in dgp if k.startswith('total_vesting_fund'))
ratio = float(dgp[fund_key].split()[0]) / float(dgp['total_vesting_shares'].split()[0])

rewards, start = [], -1
while True:
    hist, _ = rpc('condenser_api.get_account_history', [ACC, start, 1000 if start < 0 else min(1000, start)], node)
    if not hist:
        break
    for idx, item in hist:
        op = item['op']
        if op[0] == 'producer_reward':
            v = float(op[1]['vesting_shares'].split()[0])
            rewards.append((item['timestamp'], item.get('block'), v * ratio))
    first = hist[0][0]
    if first <= 1:
        break
    start = first - 1

rewards.sort()
total = sum(r[2] for r in rewards)
days = collections.Counter(r[0][:10] for r in rewards)
lines = [
    f'=== Blurt witness report for @{ACC} ({dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC, node {node}) ===',
    f'Version: {wit.get("running_version")}  | missed blocks: {wit.get("total_missed")}  | last confirmed block: {wit.get("last_confirmed_block_num")}',
    f'Witness votes (vests): {wit.get("votes")}',
    f'Blocks produced: {len(rewards)}',
    f'Total producer rewards: {total:.3f} BP (BLURT Power)',
]
if rewards:
    first_day = dt.date.fromisoformat(rewards[0][0][:10])
    n_days = max(1, (dt.date.today() - first_day).days + 1)
    lines += [f'First block: {rewards[0][0]} | last block: {rewards[-1][0]}',
              f'Average: {len(rewards)/n_days:.2f} blocks/day, {total/n_days:.3f} BP/day, ~{total/n_days*30:.1f} BP/month',
              '', 'Blocks per day:'] + [f'  {d}: {n}' for d, n in sorted(days.items())]
report = '\n'.join(lines)
print(report)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w').write(report + '\n')
