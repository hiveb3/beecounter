#!/usr/bin/env node
// Sets 100% beneficiary @null on swarm snaps/waves/invitations that are already published.
// Hive allows it only once and only BEFORE the first vote: items already voted are reported, not touched.
// Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
// Usage (VPS): /opt/hive-block-producer/run-with-key.sh /root/beecounter/set-null-beneficiary.js [--live]
//   without --live it only lists what it would do. Items checked: the opt-in snaps (buzz-config.json),
//   the bee's own replies under them and every invitation recorded in buzz-state.json.
const fs = require('fs');
const path = require('path');
const dhive = require('@hiveio/dhive');
const DIR = __dirname;
const LIVE = process.argv.includes('--live');
const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
const key = process.env.HIVE3_POSTING_KEY ? dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY) : null;
(async () => {
  const items = new Map();
  const snaps = readJson(path.join(DIR, 'buzz-config.json'), {}).snaps || {};
  for (const [a, p] of Object.entries(snaps)) items.set(`${a}/${p}`, [a, p]);
  for (const v of Object.values(readJson(path.join(DIR, 'buzz-state.json'), {}).invited || {})) items.set(`${v.bee}/${v.permlink}`, [v.bee, v.permlink]);
  // also the bee's own replies under its snap (reading lists, invitations not in the state file)
  for (const [a, p] of Object.entries(snaps)) {
    const kids = await client.call('condenser_api', 'get_content_replies', [a, p]).catch(() => []);
    for (const k of kids) if (k.author === a) items.set(`${a}/${k.permlink}`, [a, k.permlink]);
  }
  let ok = 0, voted = 0, done = 0, paid = 0;
  for (const [author, permlink] of items.values()) {
    const c = await client.call('condenser_api', 'get_content', [author, permlink]);
    if (!c || !c.author) { console.log(`? @${author}/${permlink}: not found`); continue; }
    if ((c.beneficiaries || []).some((b) => b.account === 'null' && b.weight === 10000)) { done++; continue; }
    if (c.last_payout && !c.last_payout.startsWith('1970')) { paid++; console.log(`- @${author}/${permlink}: already paid out`); continue; }
    if ((c.beneficiaries || []).length) { console.log(`✗ @${author}/${permlink}: has other beneficiaries, can't change`); continue; }
    if (Number(c.abs_rshares) !== 0 || (c.active_votes || []).length) {
      voted++; console.log(`✗ @${author}/${permlink}: already voted (${c.active_votes.length}), Hive no longer accepts beneficiaries`); continue; }
    console.log(`${LIVE ? '✓' : '→'} @${author}/${permlink}: 100% @null`);
    if (!LIVE || !key) continue;
    try {
      await client.broadcast.sendOperations([['comment_options', { author, permlink, max_accepted_payout: c.max_accepted_payout,
        percent_hbd: c.percent_hbd, allow_votes: c.allow_votes, allow_curation_rewards: c.allow_curation_rewards,
        extensions: [[0, { beneficiaries: [{ account: 'null', weight: 10000 }] }]] }]], key);
      ok++; await new Promise((r) => setTimeout(r, 3500));
    } catch (e) { console.log(`  error: ${e.message.split('\n')[0]}`); }
  }
  console.log(`\nset now: ${ok} · already @null: ${done} · voted (not possible): ${voted} · paid out: ${paid}${LIVE ? '' : '   (dry run: add --live)'}`);
  process.exit(0);
})().catch((e) => { console.log('error:', e.message); process.exit(1); });
