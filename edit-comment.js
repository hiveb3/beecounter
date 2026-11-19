#!/usr/bin/env node
// Edits an existing post/comment/snap of the swarm with the body from a file, keeping parent, title and metadata.
// Signed with the @hive3 posting key (works for every bee that granted @hive3 its posting authority).
// Usage (VPS): /opt/hive-block-producer/run-with-key.sh /root/beecounter/edit-comment.js <author> <permlink> <body.md>
const fs = require('fs');
const dhive = require('@hiveio/dhive');
const [author, permlink, file] = process.argv.slice(2);
if (!author || !permlink || !file || !process.env.HIVE3_POSTING_KEY) { console.log('Usage: run-with-key.sh edit-comment.js <author> <permlink> <body.md>'); process.exit(1); }
const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
(async () => {
  const c = await client.call('condenser_api', 'get_content', [author, permlink]);
  if (!c || !c.author) { console.log('not found'); process.exit(1); }
  const r = await client.broadcast.comment({ parent_author: c.parent_author, parent_permlink: c.parent_permlink, author, permlink,
    title: c.title, body: fs.readFileSync(file, 'utf8'), json_metadata: c.json_metadata }, dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY));
  console.log(`edited @${author}/${permlink} (tx ${r.id})`);
  process.exit(0);
})().catch((e) => { console.log('error:', e.message); process.exit(1); });
