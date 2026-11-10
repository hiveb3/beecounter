#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter pair check - pairs of authors who vote each other regularly, and what they publish (HAFSQL, public data).
# Ranks reciprocal pairs (>= MINV votes each way) by a "low-content" score: few words, image-only posts, art/abstract/AI tags.
# Signals for a human to look at, not verdicts: abstract art is legitimate art.
# Usage: python3 pair_check.py farm_edges_2026-10-17_2026-10-30.csv [minvotes=5]   -> pair_report.txt-style output
import sys, csv, json, re, collections as C
EDGES = sys.argv[1]; MINV = int(sys.argv[2]) if len(sys.argv) > 2 else 5
FROM, TO = re.findall(r'\d{4}-\d{2}-\d{2}', EDGES)[:2]
e, n = {}, {}
for r in csv.DictReader(open(EDGES)):
    e[(r['voter'], r['author'])] = float(r['usd']); n[(r['voter'], r['author'])] = int(r['votes'])
pairs = [(a, b) for (a, b) in e if a < b and n.get((b, a), 0) >= MINV and n[(a, b)] >= MINV]
authors = sorted({x for p in pairs for x in p})
print(f'{len(pairs)} reciprocal pairs with >= {MINV} votes each way, {len(authors)} authors, {FROM} → {TO}')

import psycopg2
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '900s'")
IMG = re.compile(r'https?://[^\s)"\'<>\]]+?\.(?:png|jpe?g|gif|webp)|https?://(?:images\.(?:hive|ecency)\.blog|files\.peakd\.com|i\.ecency\.com)/[^\s)"\'<>\]]+', re.I)
ART = {'art', 'abstract', 'abstractart', 'digitalart', 'aiart', 'ai', 'nft', 'nftart', 'painting', 'colors', 'colours', 'generativeart',
       'creativecoin', 'artzone', 'alive', 'drawing', 'pixelart', 'neoxian', 'photography'}
def words(t): return len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", re.sub(r'!\[[^\]]*\]\([^)]*\)|<[^>]+>|https?://\S+', ' ', t or '')))
info = {}
for a in authors:
    cur.execute("""SELECT permlink, title, body, json_metadata, total_payout_value FROM hafsql.comments
                   WHERE author=%s AND parent_author='' AND created >= %s AND created < %s::date + 1 AND NOT deleted""", (a, FROM, TO))
    P = cur.fetchall()
    if not P: continue
    W, I, tags, links, pay = [], [], C.Counter(), [], 0.0
    for pl, title, body, meta, p in P:
        try: m = json.loads(meta) if isinstance(meta, str) else (meta or {})
        except Exception: m = {}
        tg = [str(t).lower() for t in (m.get('tags') or [])] if isinstance(m, dict) else []
        tags.update(tg); u = IMG.findall(body or '')
        W.append(words(body)); I.append(len(u)); pay += float(p or 0)
        links.append((f'https://peakd.com/@{a}/{pl}', (u[:1] or [''])[0]))
    k = len(P); wm = sorted(W)[k // 2]
    art = sum(c for t, c in tags.items() if t in ART) / k
    info[a] = dict(posts=k, words=wm, imgs=sorted(I)[k // 2], pay=round(pay, 2), tags=[t for t, _ in tags.most_common(6)], links=links[:3],
                   low=(wm < 80) + (sorted(I)[k // 2] >= 1 and wm < 150) + (art >= 1))
rows = []
for a, b in pairs:
    if a in info and b in info:
        rows.append((info[a]['low'] + info[b]['low'], min(e[(a, b)], e[(b, a)]), a, b))
rows.sort(reverse=True)
print('\n=== RECIPROCAL PAIRS, most "low-content" first (score 0-6: short text, image-only, art/abstract tags) ===')
for s, m, a, b in rows[:40]:
    print(f'\n[{s}] {a} ⇄ {b}   {e[(a, b)]:.2f} $ / {e[(b, a)]:.2f} $   votes {n[(a, b)]}/{n[(b, a)]}')
    for x in (a, b):
        i = info[x]
        print(f'     {x:<18} {i["posts"]} posts · {i["words"]} words · {i["imgs"]} imgs · {i["pay"]} $ · tags {", ".join(i["tags"])}')
        for url, img in i['links'][:2]: print(f'        {url}   {img}')
