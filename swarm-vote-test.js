#!/usr/bin/env node
// Test: every bee of the swarm votes one post, signing ONLY with the @hive3 posting key
// (works because each bee granted @hive3 its posting authority).
// Usage (VPS): /opt/hive-block-producer/run-with-key.sh /root/beecounter/swarm-vote-test.js <author> <permlink> [weight%]
// run-with-key.sh decrypts the @hive3 posting key into HIVE3_POSTING_KEY.

const dhive = require('@hiveio/dhive');

const BEES = ['hive-170283', 'aibees', 'ai-bee', 'hive3.guard', 'beecounter', 'scoutbee', 'hivethree', 'hive-3',
  'hive2bee3', 'hive.bee-3', 'bz3', 'pollenpatron', 'ant-thebeekeeper', 'blurtbee'];
const [author, permlink, pct = '1'] = process.argv.slice(2);
if (!author || !permlink || !process.env.HIVE3_POSTING_KEY) {
  console.log('Usage: run-with-key.sh swarm-vote-test.js <author> <permlink> [weight%]'); process.exit(1);
}
const key = dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY);
const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
const weight = Math.round(parseFloat(pct) * 100);

(async () => {
  const votes = await client.call('condenser_api', 'get_active_votes', [author, permlink]);
  for (const voter of BEES) {
    if (votes.some((v) => v.voter === voter)) { console.log(`= ${voter}: already voted`); continue; }
    try {
      const r = await client.broadcast.vote({ voter, author, permlink, weight }, key);
      console.log(`✓ ${voter}: voted ${pct}% (tx ${r.id})`);
    } catch (e) { console.log(`✗ ${voter}: ${e.message.split('\n')[0]}`); }
    await new Promise((r) => setTimeout(r, 3500));
  }
  process.exit(0);
})();
