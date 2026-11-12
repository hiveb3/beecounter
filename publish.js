// Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
// BeeCounter - uploads the images and publishes the post.
// Usage: node publish.js OUTDIR            -> uploads images and writes OUTDIR/final.md (draft, does NOT publish)
//        node publish.js OUTDIR --publish  -> publishes on Hive
// The posting key comes from the BEECOUNTER_POSTING_KEY environment variable (decrypted by lib.sh).
const fs = require('fs'), path = require('path');
const { Client, PrivateKey, cryptoUtils } = require('@hiveio/dhive');

const ACCOUNT = 'beecounter';
const NODES = ['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network'];
const BENEFICIARIES = [{ account: 'null', weight: 10000 }];   // bot reports: 100% burned
const dir = process.argv[2], PUBLISH = process.argv.includes('--publish');
if (!dir) { console.error('usage: node publish.js OUTDIR [--publish]'); process.exit(1); }
const wif = process.env.BEECOUNTER_POSTING_KEY;
if (!wif) { console.error('manca BEECOUNTER_POSTING_KEY'); process.exit(1); }
const key = PrivateKey.fromString(wif);
const client = new Client(NODES, { timeout: 15000, failoverThreshold: 2 });

async function upload(file) {
  const buf = fs.readFileSync(file);
  const sig = key.sign(cryptoUtils.sha256(Buffer.concat([Buffer.from('ImageSigningChallenge'), buf]))).toString();
  for (let i = 0; i < 3; i++) {
    try {
      const fd = new FormData();
      fd.append('file', new Blob([buf], { type: 'image/png' }), path.basename(file));
      const r = await fetch(`https://images.hive.blog/${ACCOUNT}/${sig}`, { method: 'POST', body: fd });
      const j = await r.json();
      if (j.url) return j.url;
      console.error('upload', file, JSON.stringify(j));
    } catch (e) { console.error('upload', file, e.message); }
    await new Promise(r => setTimeout(r, 3000));
  }
  throw new Error('upload failed: ' + file);
}

(async () => {
  const meta = JSON.parse(fs.readFileSync(path.join(dir, 'meta.json')));
  const cacheFile = path.join(dir, 'images.json');
  const urls = fs.existsSync(cacheFile) ? JSON.parse(fs.readFileSync(cacheFile)) : {};
  for (const im of meta.images) if (!urls[im]) { urls[im] = await upload(path.join(dir, im)); fs.writeFileSync(cacheFile, JSON.stringify(urls, null, 1)); }
  let body = fs.readFileSync(path.join(dir, 'post.md'), 'utf8');
  for (const im of meta.images) body = body.split(`IMG:${im}`).join(`![${im}](${urls[im]})`);
  if (body.includes('IMG:')) throw new Error('missing images in the post');
  // house style: no centered text, and accounts are linked without "@" so nobody gets a notification
  body = body.replace(/<\/?center>\n?/g, '');
  body = body.replace(/\[@([a-z][a-z0-9.-]{1,14}[a-z0-9])\]\(/g, '[$1](');
  body = body.replace(/(^|[^\w\/\[@.-])@([a-z][a-z0-9.-]{1,14}[a-z0-9])(?![\w(])/g, '$1[$2](/@$2)');
  fs.writeFileSync(path.join(dir, 'final.md'), `# ${meta.title}\n\n${body}`);
  console.log('Draft ready:', path.join(dir, 'final.md'));
  if (!PUBLISH) return;

  let ex = null; try { ex = await client.database.call('get_content', [ACCOUNT, meta.permlink]); } catch (e) { ex = null; }
  if (ex && ex.author) { console.log('Already published, skipping:', meta.permlink); return; }
  const json_metadata = JSON.stringify({ app: 'beecounter/1.0', format: 'markdown', tags: meta.tags,
    description: meta.description, image: meta.images.map(i => urls[i]) });
  const ops = [
    ['comment', { parent_author: '', parent_permlink: meta.community, author: ACCOUNT, permlink: meta.permlink,
                  title: meta.title, body, json_metadata }],
    ['comment_options', { author: ACCOUNT, permlink: meta.permlink, max_accepted_payout: '1000000.000 HBD',
                          percent_hbd: 10000, allow_votes: true, allow_curation_rewards: true,
                          extensions: [[0, { beneficiaries: BENEFICIARIES }]] }],
  ];
  const r = await client.broadcast.sendOperations(ops, key);
  console.log('PUBLISHED:', `https://peakd.com/@${ACCOUNT}/${meta.permlink}`, 'tx', r.id);
})().then(() => process.exit(0)).catch(e => { console.error('ERROR', e.message || e); process.exit(1); });
