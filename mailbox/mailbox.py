#!/usr/bin/env python3
# Bee Mailbox - lets Claude read the internet through this VPS, using a private GitHub repo as a mailbox.
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human.
#
# Claude writes requests/<id>.json  ->  this service runs it  ->  writes results/<id>.json (+ results/<id>.<ext> for images)
# Only READ-ONLY operations from a fixed list. No shell, no keys, nothing is ever written to Hive.
#
#   {"op": "hive",   "method": "bridge.get_discussion", "params": {...}}     Hive API, allowed methods only
#   {"op": "url",    "url": "https://...", "mode": "text"|"raw"|"image"}      download a page (text = HTML stripped) or an image
#   {"op": "sql",    "query": "SELECT ..."}                                    HAFSQL public, read-only, max 5000 rows
#   {"op": "report", "file": "money_report.txt", "tail": 200}                  read a report from /root/beecounter (*.txt, *.json, *.csv)
import json, os, re, time, subprocess, urllib.request, urllib.error, html, datetime as dt, traceback, glob

REPO = os.environ.get('MAILBOX_DIR', '/opt/bee-mailbox/repo')
REPORTS = '/root/beecounter'
NODES = ['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network', 'https://techcoderx.com']
HIVE_METHODS = {
    'bridge.get_discussion', 'bridge.get_post', 'bridge.get_ranked_posts', 'bridge.get_account_posts', 'bridge.get_profile',
    'bridge.get_community', 'bridge.list_communities', 'bridge.get_post_header', 'bridge.account_notifications',
    'condenser_api.get_accounts', 'condenser_api.get_active_votes', 'condenser_api.get_content', 'condenser_api.get_content_replies',
    'condenser_api.get_dynamic_global_properties', 'condenser_api.get_witness_by_account', 'condenser_api.get_witnesses_by_vote',
    'condenser_api.get_account_history', 'condenser_api.get_vesting_delegations', 'condenser_api.get_follow_count',
    'condenser_api.get_current_median_history_price', 'condenser_api.get_reward_fund', 'database_api.find_accounts',
    'rc_api.find_rc_accounts', 'condenser_api.lookup_accounts', 'condenser_api.get_block',
}
MAX_TEXT = 3_000_000; MAX_IMG = 10_000_000; UA = 'bee-mailbox/1.0 (read-only fetcher for @hive3)'

def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, text=True, timeout=120)

def http(url, data=None, limit=MAX_TEXT, ctype='application/json'):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, **({'Content-Type': ctype} if data else {})})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read(limit + 1), r.headers.get('Content-Type', '')

def op_hive(q):
    m = q.get('method')
    if m not in HIVE_METHODS: raise ValueError(f'method not allowed: {m}')
    body = json.dumps({'jsonrpc': '2.0', 'method': m, 'params': q.get('params', []), 'id': 1}).encode()
    last = None
    for n in NODES:
        try:
            raw, _ = http(n, body); d = json.loads(raw)
            if 'result' in d: return {'node': n, 'result': d['result']}
            last = d.get('error')
        except Exception as e: last = str(e)
    raise RuntimeError(f'all nodes failed: {last}')

def strip_html(t):
    t = re.sub(r'(?is)<(script|style|noscript).*?</\1>', ' ', t)
    t = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>', '\n', t)
    t = re.sub(r'<[^>]+>', ' ', t); t = html.unescape(t)
    return re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n\n', t)).strip()

def op_url(q, rid):
    u = q.get('url', '')
    if not re.match(r'^https?://', u): raise ValueError('only http(s) urls')
    if re.search(r'://(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|\[?::1)', u): raise ValueError('private address not allowed')
    mode = q.get('mode', 'text')
    raw, ct = http(u, limit=MAX_IMG if mode == 'image' else MAX_TEXT)
    if mode == 'image':
        ext = {'image/png': 'png', 'image/gif': 'gif', 'image/webp': 'webp'}.get(ct.split(';')[0], 'jpg')
        name = f'results/{rid}.{ext}'; open(os.path.join(REPO, name), 'wb').write(raw[:MAX_IMG])
        return {'content_type': ct, 'file': name, 'bytes': len(raw)}
    txt = raw[:MAX_TEXT].decode('utf-8', 'replace')
    return {'content_type': ct, 'truncated': len(raw) > MAX_TEXT, 'text': strip_html(txt) if mode == 'text' and 'html' in ct else txt}

def op_sql(q):
    s = q.get('query', '').strip().rstrip(';')
    if not re.match(r'(?is)^\s*(select|with)\b', s) or ';' in s: raise ValueError('only one SELECT/WITH query')
    import psycopg2
    con = psycopg2.connect(host='hafsql-sql.mahdiyari.info', port=5432, dbname='haf_block_log',
                           user='hafsql_public', password='hafsql_public', connect_timeout=30)
    con.set_session(readonly=True, autocommit=True)
    cur = con.cursor(); cur.execute("SET statement_timeout = '600s'")
    cur.execute(s); cols = [c[0] for c in cur.description]; rows = cur.fetchmany(5000)
    con.close()
    return {'columns': cols, 'rows': [[str(x) if x is not None else None for x in r] for r in rows], 'row_count': len(rows)}

def op_report(q):
    f = os.path.basename(q.get('file', ''))
    if not re.match(r'^[\w.-]+\.(txt|json|csv)$', f): raise ValueError('only .txt/.json/.csv names')
    p = os.path.join(REPORTS, f)
    if not os.path.isfile(p):
        return {'error': 'not found', 'available': sorted(os.path.basename(x) for x in glob.glob(REPORTS + '/*.txt') + glob.glob(REPORTS + '/*.json'))}
    lines = open(p, errors='replace').read().splitlines()
    n = int(q.get('tail', 0) or 0)
    return {'file': f, 'lines_total': len(lines), 'text': '\n'.join(lines[-n:] if n else lines)[:MAX_TEXT],
            'modified': dt.datetime.fromtimestamp(os.path.getmtime(p)).isoformat()}

def handle(path):
    rid = os.path.splitext(os.path.basename(path))[0]
    t0 = time.time()
    try:
        q = json.load(open(path)); op = q.get('op')
        res = op_hive(q) if op == 'hive' else op_url(q, rid) if op == 'url' else op_sql(q) if op == 'sql' \
            else op_report(q) if op == 'report' else (_ for _ in ()).throw(ValueError(f'unknown op {op}'))
        out = {'id': rid, 'ok': True, 'request': q, **res}
    except Exception as e:
        out = {'id': rid, 'ok': False, 'error': f'{type(e).__name__}: {e}', 'trace': traceback.format_exc()[-1500:]}
    out['seconds'] = round(time.time() - t0, 1); out['done_at'] = dt.datetime.utcnow().isoformat() + 'Z'
    json.dump(out, open(os.path.join(REPO, 'results', rid + '.json'), 'w'), ensure_ascii=False, indent=1)
    os.remove(path)

def cleanup():
    old = time.time() - 7 * 86400
    for f in glob.glob(os.path.join(REPO, 'results', '*')):
        if os.path.basename(f) != '.keep' and os.path.getmtime(f) < old: os.remove(f)

def main():
    os.makedirs(os.path.join(REPO, 'requests'), exist_ok=True); os.makedirs(os.path.join(REPO, 'results'), exist_ok=True)
    n = 0
    while True:
        try:
            git('pull', '-q', '--rebase')
            reqs = sorted(glob.glob(os.path.join(REPO, 'requests', '*.json')))
            for r in reqs: handle(r)
            n += 1
            if n % 500 == 0: cleanup()
            if reqs or n % 500 == 0:
                git('add', '-A', 'requests', 'results')
                git('commit', '-qm', f'results: {", ".join(os.path.basename(r) for r in reqs) or "cleanup"}')
                p = git('push', '-q')
                if p.returncode: git('pull', '-q', '--rebase'); git('push', '-q')
        except Exception as e:
            print('loop error:', e, flush=True)
        time.sleep(15)

if __name__ == '__main__':
    main()
