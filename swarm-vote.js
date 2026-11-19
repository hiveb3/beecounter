#!/usr/bin/env node
// Swarm Vote Policy (public, see the declaration post):
//   every root post of the swarm gets AT MOST ONE vote from the swarm:
//   one bee, 100%, cast in the open (never in the last 12 hours before payout), never by the author itself.
// Signed only with the @hive3 posting key (each bee granted @hive3 its posting authority).
// Usage (VPS): /opt/hive-block-producer/run-with-key.sh /root/beecounter/swarm-vote.js [--live]
//   without --live it only prints what it would do.

const dhive = require('@hiveio/dhive');

const BEES = ['hive3', 'hive-170283', 'aibees', 'ai-bee', 'hive3.guard', 'beecounter', 'scoutbee', 'hivethree', 'hive-3',
  'hive2bee3', 'hive.bee-3', 'bz3', 'pollenpatron', 'ant-thebeekeeper', 'blurtbee'];
const AUTHORS = ['hive3', 'ant-thebeekeeper', 'blurtbee', 'beecounter', 'scoutbee', 'hive-170283', 'aibees', 'ai-bee'];
const LIVE = process.argv.includes('--live');
const LOCKOUT_H = 12;     // Hive ignores upvotes in the last 12 h: we stay well before it
const MIN_AGE_MIN = 15;   // let real readers vote first
const MIN_VP = 80;        // a bee votes only if its voting power is at least 80%
const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
const key = process.env.HIVE3_POSTING_KEY ? dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY) : null;
if (LIVE && !key) { console.log('Run it via run-with-key.sh'); process.exit(1); }

const vp = (a) => {   // current upvote mana in %
  const max = parseFloat(a.vesting_shares) - parseFloat(a.delegated_vesting_shares) + parseFloat(a.received_vesting_shares);
  const m = a.voting_manabar, cur = Math.min(max * 1e6, +m.current_mana + max * 1e6 * (Date.now() / 1000 - m.last_update_time) / 432000);
  return max ? cur / (max * 1e6) * 100 : 0;
};

(async () => {
  const accs = await client.database.getAccounts(BEES);
  const power = Object.fromEntries(accs.map((a) => [a.name, vp(a)]));
  const now = Date.now();
  for (const author of AUTHORS) {
    const posts = await client.call('bridge', 'get_account_posts', { sort: 'posts', account: author, limit: 20 });
    for (const p of posts || []) {
      if (p.author !== author) continue;                       // skip reblogs
      const left = (new Date(p.payout_at + 'Z') - now) / 3600e3, age = (now - new Date(p.created + 'Z')) / 60e3;
      if (left <= LOCKOUT_H || age < MIN_AGE_MIN) continue;
      if (p.active_votes.some((v) => BEES.includes(v.voter))) continue;   // already has its one swarm vote
      const voter = BEES.filter((b) => b !== author && power[b] >= MIN_VP).sort((a, b) => power[b] - power[a])[0];
      if (!voter) { console.log(`- @${author}/${p.permlink}: no bee with enough voting power`); continue; }
      if (!LIVE) { console.log(`~ @${voter} would vote @${author}/${p.permlink} (${left.toFixed(0)} h to payout)`); continue; }
      try {
        const r = await client.broadcast.vote({ voter, author, permlink: p.permlink, weight: 10000 }, key);
        power[voter] -= 2;   // ~2% mana per full vote
        console.log(`✓ @${voter} voted @${author}/${p.permlink} (tx ${r.id})`);
      } catch (e) { console.log(`✗ @${voter} -> @${author}/${p.permlink}: ${e.message.split('\n')[0]}`); }
      await new Promise((r) => setTimeout(r, 3500));
    }
  }
  process.exit(0);
})();
