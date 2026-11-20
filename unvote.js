// Remove votes (weight 0) cast by a swarm bee, signing with hive3's posting key (posting authority).
// Usage: run-with-key.sh unvote.js <voter> author/permlink [author/permlink ...]
const { Client, PrivateKey } = require('@hiveio/dhive');
const client = new Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
const key = PrivateKey.fromString(process.env.HIVE3_POSTING_KEY);
const [voter, ...posts] = process.argv.slice(2);
(async () => {
  for (const p of posts) {
    const [author, permlink] = p.replace(/^@/, '').split('/');
    try {
      const r = await client.broadcast.vote({ voter, author, permlink, weight: 0 }, key);
      console.log(`unvoted ${voter} on @${author}/${permlink} (tx ${r.id})`);
    } catch (e) { console.log(`FAIL ${voter} on @${author}/${permlink}: ${e.message}`); }
    await new Promise(r => setTimeout(r, 3200));
  }
})();
