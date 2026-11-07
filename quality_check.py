#!/usr/bin/env python3
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter quality check - what the authors who take most of the rewards actually publish (HAFSQL, public data).
# For each author: words per post, images per post, how often the same images come back, stock / AI-generator image hosts,
# repeated text between their own posts (templates, copy-paste), and the share of AI-disclosure tags.
# These are signals for a human reader, not verdicts: AI-written text cannot be detected reliably by a script.
# Usage: python3 quality_check.py farm_2026-10-17_2026-10-30.json [top=50]  -> quality_report.txt-style output + quality.json + quality_sample.csv
import sys, json, re, csv, collections as C, datetime as dt
FARM = json.load(open(sys.argv[1])); TOP = int(sys.argv[2]) if len(sys.argv) > 2 else 50
FROM, TO = FARM['from'], FARM['to']
import psycopg2
con = psycopg2.connect(host="hafsql-sql.mahdiyari.info", port=5432, dbname="haf_block_log",
                       user="hafsql_public", password="hafsql_public", connect_timeout=30)
con.set_session(readonly=True, autocommit=True)
cur = con.cursor(); cur.execute("SET statement_timeout = '900s'"); cur.execute("SET TIME ZONE 'UTC'")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='hafsql' AND table_name='comments'")
cols = {r[0] for r in cur.fetchall()}
BODY = 'body' if 'body' in cols else None; META = 'json_metadata' if 'json_metadata' in cols else None
if not BODY: raise SystemExit(f'hafsql.comments has no body column: {sorted(cols)}')

# authors: the top N by payout in the farm report (the full list is the 75% group if TOP is large enough)
authors = [a for a, *_ in FARM['top']][:TOP] if len(FARM['top']) >= TOP else None
if authors is None or len(authors) < TOP:
    cur.execute(f"""SELECT author, SUM(total_payout_value + curator_payout_value) p FROM hafsql.comments
                    WHERE parent_author='' AND created >= %s AND created < %s::date + 1 AND NOT deleted
                    GROUP BY author ORDER BY p DESC LIMIT %s""", (FROM, TO, TOP))
    authors = [r[0] for r in cur.fetchall()]

IMG = re.compile(r'https?://[^\s)"\'<>\]]+?\.(?:png|jpe?g|gif|webp)|https?://(?:images\.(?:hive|ecency)\.blog|files\.peakd\.com|img\.leopedia\.io|i\.ecency\.com|ipfs[^\s)"\'<>]+)/[^\s)"\'<>\]]+', re.I)
STOCK = ('unsplash', 'pixabay', 'pexels', 'shutterstock', 'freepik', 'istockphoto', 'gettyimages', 'canva.com', 'wikimedia')
AIHOST = ('openai', 'oaidalle', 'dalle', 'midjourney', 'leonardo', 'ideogram', 'lexica', 'nightcafe', 'stablediffusion', 'dreamstudio',
          'bing.com/images/create', 'grok', 'gemini', 'firefly', 'playground', 'craiyon', 'ai-generated', 'aigenerated', 'imagine')
AITAG = ('ai', 'aiart', 'aigenerated', 'ai-generated', 'chatgpt', 'gpt', 'claude', 'gemini', 'midjourney', 'dalle', 'aibees')
def words(t): return len(re.findall(r"[A-Za-zÀ-ÿЀ-ӿ一-鿿]{2,}", re.sub(r'!\[[^\]]*\]\([^)]*\)|<[^>]+>|https?://\S+', ' ', t or '')))
def shingles(t, k=8):
    w = re.findall(r'\w+', (t or '').lower()); return {' '.join(w[i:i + k]) for i in range(0, max(len(w) - k, 0), 3)}

rep, sample = {}, []
for a in authors:
    cur.execute(f"""SELECT permlink, title, {BODY}, {META or "''"}, total_payout_value + curator_payout_value FROM hafsql.comments
                    WHERE author=%s AND parent_author='' AND created >= %s AND created < %s::date + 1 AND NOT deleted ORDER BY created""",
                (a, FROM, TO))
    posts = cur.fetchall()
    if not posts: continue
    W, I, imgs, stock, aiimg, aitag, sh = [], [], C.Counter(), 0, 0, 0, []
    for pl, title, body, meta, pay in posts:
        u = set(IMG.findall(body or ''))
        try: m = json.loads(meta) if isinstance(meta, str) else (meta or {})
        except Exception: m = {}
        tags = [str(t).lower() for t in (m.get('tags') or [])] if isinstance(m, dict) else []
        for x in (m.get('image') or []) if isinstance(m, dict) else []: u.add(str(x))
        W.append(words(body)); I.append(len(u)); imgs.update(u)
        stock += any(s in x.lower() for x in u for s in STOCK); aiimg += any(s in x.lower() for x in u for s in AIHOST)
        aitag += any(t in AITAG for t in tags); sh.append(shingles(body))
        sample.append([a, f'https://peakd.com/@{a}/{pl}', (title or '')[:80], W[-1], I[-1], round(float(pay or 0), 2), (sorted(u)[:1] or [''])[0]])
    n = len(posts)
    reused = sum(c for c in imgs.values() if c > 1)                       # image URLs appearing in more than one post
    sim = []                                                              # text overlap between consecutive own posts
    for x, y in zip(sh, sh[1:]):
        if x and y: sim.append(len(x & y) / min(len(x), len(y)))
    rep[a] = dict(posts=n, words_med=sorted(W)[n // 2], words_min=min(W), imgs_med=sorted(I)[n // 2],
                  img_reuse=round(reused / max(sum(I), 1), 2), stock_posts=stock, ai_host_posts=aiimg, ai_tag_posts=aitag,
                  self_overlap=round(sum(sim) / len(sim), 2) if sim else 0)

print(f'=== QUALITY SIGNALS of the top {len(rep)} earners, {FROM} → {TO} ===')
print('words = median words per post · imgs = median images per post · reuse = share of image links already used in their other posts')
print('stock/AI-host = posts with stock-photo or AI-generator image links · AI-tag = posts tagged as AI · overlap = text repeated between own posts\n')
print(f'  {"author":<18}{"posts":>6}{"words":>7}{"min":>6}{"imgs":>6}{"reuse":>7}{"stock":>7}{"AIhost":>7}{"AItag":>7}{"overlap":>9}  flags')
for a, r in rep.items():
    f = []
    if r['words_med'] < 150: f.append('short')
    if r['imgs_med'] >= 8 and r['words_med'] < 300: f.append('image-heavy')
    if r['img_reuse'] >= .3: f.append('reused-images')
    if r['self_overlap'] >= .3: f.append('template/copy')
    if r['ai_host_posts'] or r['ai_tag_posts']: f.append('AI-signals')
    print(f'  {a:<18}{r["posts"]:>6}{r["words_med"]:>7}{r["words_min"]:>6}{r["imgs_med"]:>6}{r["img_reuse"]:>7.0%}{r["stock_posts"]:>7}'
          f'{r["ai_host_posts"]:>7}{r["ai_tag_posts"]:>7}{r["self_overlap"]:>9.0%}  {", ".join(f)}')
json.dump(rep, open('quality.json', 'w'), indent=1)
with open('quality_sample.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['author', 'url', 'title', 'words', 'images', 'payout', 'first_image']); w.writerows(sample)
print('\nSaved quality.json and quality_sample.csv (every post with link, words, images, payout, first image)')
