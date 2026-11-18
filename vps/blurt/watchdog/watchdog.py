#!/usr/bin/env python3
# Blurt witness watchdog for @blurtbee.
# Runs every minute (systemd timer). Sends push alerts via ntfy.sh and, if enabled,
# disables the witness signing key after too many missed blocks.
# Config: /etc/blurt-watchdog.json   State: /var/lib/blurt-watchdog/state.json
# Status report: /root/beecounter/blurt_watchdog.txt (readable via bee-mailbox "report")
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
import json, os, subprocess, sys, time, urllib.request, datetime as dt

CFG_PATH = '/etc/blurt-watchdog.json'
STATE_DIR = '/var/lib/blurt-watchdog'
STATE = os.path.join(STATE_DIR, 'state.json')
REPORT = '/root/beecounter/blurt_watchdog.txt'
NULL_KEY = 'BLT1111111111111111111111111111111114T1Anm'
DEFAULTS = {
    'account': 'blurtbee',
    'local_rpc': '',                       # e.g. http://127.0.0.1:8093 (Blurt node, NOT the Hive one)
    'public_rpc': ['https://blurt-rpc.saboin.com', 'https://rpc.beblurt.com', 'https://blurt-rpc.node01.org', 'https://rpc.blurt.world'],
    'ntfy_topic': '',                      # push alerts: https://ntfy.sh/<topic>
    'miss_threshold': 3,                   # misses ...
    'miss_window_min': 30,                 # ... within this many minutes => disable
    'stall_seconds': 90,                   # local node head block older than this => alert
    'auto_disable': False,                 # stays False until the disable command has been tested
    'disable_cmd': '',                     # shell command that sets the signing key to NULL_KEY
    'alert_every_min': 15,                 # do not repeat the same alert more often than this
}

def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default

cfg = {**DEFAULTS, **load(CFG_PATH, {})}
st = load(STATE, {'last_missed': None, 'events': [], 'last_alert': {}, 'disabled_at': None})
now = time.time()
log = []

def rpc(method, params, nodes):
    last = None
    for n in nodes:
        if not n:
            continue
        try:
            body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
            r = json.loads(urllib.request.urlopen(urllib.request.Request(n, body, {'Content-Type': 'application/json'}), timeout=15).read())
            if 'result' in r:
                return r['result'], n
            last = r.get('error')
        except Exception as e:
            last = e
    return None, f'failed: {last}'

def alert(key, title, msg, prio='default'):
    log.append(f'ALERT [{key}] {title}: {msg}')
    if now - st['last_alert'].get(key, 0) < cfg['alert_every_min'] * 60:
        return
    st['last_alert'][key] = now
    if not cfg['ntfy_topic']:
        return
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{cfg['ntfy_topic']}", msg.encode(),
                                     {'Title': title.encode('utf-8'), 'Priority': prio, 'Tags': 'bee'})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        log.append(f'ntfy error: {e}')

acc = cfg['account']
nodes = [cfg['local_rpc']] + cfg['public_rpc']
wit, src = rpc('condenser_api.get_witness_by_account', [acc], cfg['public_rpc'])  # public view = what the network sees
if not wit:
    alert('rpc', 'Blurt watchdog: no data', f'Cannot read witness @{acc} from public nodes ({src}).', 'low')
else:
    missed, key = int(wit['total_missed']), wit['signing_key']
    if st['last_missed'] is not None and missed > st['last_missed']:
        d = missed - st['last_missed']
        st['events'].append([now, d])
        alert('miss', f'Bea missed {d} block(s)', f'@{acc} total_missed {st["last_missed"]} -> {missed}', 'high')
    st['last_missed'] = missed
    win = cfg['miss_window_min'] * 60
    st['events'] = [e for e in st['events'] if now - e[0] < win]
    recent = sum(e[1] for e in st['events'])
    log.append(f'@{acc}: total_missed={missed}, misses in last {cfg["miss_window_min"]} min={recent}, signing_key={"NULL (disabled)" if key == NULL_KEY else key[:12] + "..."}, last block={wit.get("last_confirmed_block_num")}')
    if key != NULL_KEY and recent >= cfg['miss_threshold']:
        if st.get('disabled_at') and now - st['disabled_at'] < 600:
            log.append('disable command already run in the last 10 min, waiting for the chain to show the null key')
        elif cfg['auto_disable'] and cfg['disable_cmd']:
            r = subprocess.run(cfg['disable_cmd'], shell=True, capture_output=True, text=True, timeout=120)
            ok = r.returncode == 0
            st['disabled_at'] = now if ok else st.get('disabled_at')
            alert('disable', 'Bea witness DISABLED' if ok else 'Bea: DISABLE FAILED',
                  f'{recent} misses in {cfg["miss_window_min"]} min. Command exit {r.returncode}. {(r.stdout + r.stderr)[-300:]}', 'urgent')
        else:
            alert('disable', 'Bea: too many missed blocks', f'{recent} misses in {cfg["miss_window_min"]} min. Auto-disable is OFF: disable the key by hand!', 'urgent')

if cfg['local_rpc']:
    dgp, _ = rpc('condenser_api.get_dynamic_global_properties', [], [cfg['local_rpc']])
    if not dgp:
        alert('local', 'Blurt node not responding', f'Local Blurt RPC {cfg["local_rpc"]} does not answer.', 'high')
    else:
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(dgp['time']).replace(tzinfo=dt.timezone.utc)).total_seconds()
        log.append(f'local node head block {dgp["head_block_number"]}, age {age:.0f}s')
        if age > cfg['stall_seconds']:
            alert('stall', 'Blurt node stalled', f'Local head block is {age:.0f}s old (block {dgp["head_block_number"]}).', 'high')

os.makedirs(STATE_DIR, exist_ok=True)
json.dump(st, open(STATE, 'w'))
os.makedirs(os.path.dirname(REPORT), exist_ok=True)
with open(REPORT, 'w') as f:
    f.write(f'=== Blurt watchdog {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC | auto_disable={cfg["auto_disable"]} | ntfy={"on" if cfg["ntfy_topic"] else "off"} ===\n')
    f.write('\n'.join(log) + '\n')
if '-v' in sys.argv:
    print('\n'.join(log))
