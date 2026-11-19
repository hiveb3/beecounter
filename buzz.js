#!/usr/bin/env node
// The Buzz List: honest opt-in for the hive3 swarm.
// Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
//
// Every run (cron, every 2 hours):
//   1. reads the replies under each opt-in snap: 🐝 = opt in, 🚫 = opt out (the chain is the register)
//   2. thank-you vote, ONCE per person, ever: the inviting bee at 100%, other bees added until >= $0.03
//      (opt-out / opt-in again never earns a second vote)
//   3. invitations: one bee per run, max 5 names, only in daytime (12-23 UTC), each person tagged ONCE in total
//      across the whole swarm; people who already replied (even without an invite) are never invited
//
// Usage (VPS):  /opt/hive-block-producer/run-with-key.sh /root/beecounter/buzz.js [--live]
//   without --live it only prints what it would do. Needs: npm i pg  (in /root/beecounter)
// Kill switch: create the file /root/beecounter/BUZZ_STOP and nothing is broadcast.

const fs = require('fs');
const path = require('path');
const dhive = require('@hiveio/dhive');
const { Client: PG } = require('pg');

const DIR = __dirname;
const LIVE = process.argv.includes('--live');
const STATE_FILE = path.join(DIR, 'buzz-state.json');
const CONFIG_FILE = path.join(DIR, 'buzz-config.json');
const STOP_FILE = path.join(DIR, 'BUZZ_STOP');

const FAMILY = ['hive3', 'hive-170283', 'aibees', 'ai-bee', 'hive3.guard', 'beecounter', 'scoutbee', 'hivethree', 'hive-3',
  'hive2bee3', 'hive.bee-3', 'bz3', 'pollenpatron', 'ant-thebeekeeper', 'blurtbee'];
const VOTERS = FAMILY.filter((a) => a !== 'hive3.guard');   // the security bot never hands out honey
const NAMES_PER_INVITE = 5;
const INVITE_EVERY_MIN = 110;          // one invitation per run (the timer runs every 2 h)
const DAY_UTC = [12, 23];              // invitations only 12:00-23:00 UTC (daytime in Argentina)
const TOP_EVERY = 5;                   // every 5th invitation goes to the 75% group, the others to the 25% tail
const THANK_USD = 0.03;
const MAX_THANKS_PER_RUN = 10;
const MIN_REP = 40;                    // reputation score
const MIN_LEFT_H = 13;                 // a reply closer than this to payout can't be voted any more

const INVITE_TEXT = (names) =>
  `🐝 ${names.map((n) => '@' + n).join(' ')}: one-time hello from the swarm. We share rewards & governance data. ` +
  `Want updates? Reply 🐝 to the snap above. We won't tag you again unless you say yes. 🍯\n\n` +
  `![Ant](https://images.hive.blog/u/ant-thebeekeeper/avatar/small) Ant\n\n` +
  `<sub>Automated one-time invitation from the hive3 swarm, run by Ant (human, AI-assisted). ` +
  `No reply = no more tags. Joining earns a single thank-you vote, once.</sub>`;

const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
const key = process.env.HIVE3_POSTING_KEY ? dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY) : null;
const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const save = (s) => fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log(`[${new Date().toISOString()}]`, ...a);
const canBroadcast = () => LIVE && key && !fs.existsSync(STOP_FILE);

// ---------- 1. read the opt-in replies ----------
function verdict(body) {
  const b = String(body || '').toLowerCase();
  if (b.includes('🚫') || /\bopt[ -]?out\b|\bstop tagging\b|\bunsubscribe\b/.test(b)) return 'out';
  if (b.includes('🐝') || /\bopt[ -]?in\b|\bbuzz me\b|\bsubscribe\b/.test(b)) return 'in';
  return null;
}

async function scanReplies(state, snaps) {
  for (const [bee, permlink] of Object.entries(snaps)) {
    const disc = await client.call('bridge', 'get_discussion', { author: bee, permlink }).catch(() => null);
    if (!disc) { log(`! could not read the snap of @${bee}`); continue; }
    const replies = Object.values(disc).filter((c) => c.depth > 0 && !FAMILY.includes(c.author))
      .sort((a, b) => (a.created < b.created ? -1 : 1));
    for (const c of replies) {
      const u = c.author, v = verdict(c.body);
      const s = state.people[u] || (state.people[u] = { first_seen: c.created, via: bee });
      if (!v) continue;                                   // any reply still counts as "seen": never invited later
      if (s.last_reply && s.last_reply >= c.created) continue;
      s.last_reply = c.created;
      if (s.status !== v) { s.status = v; s.changes = (s.changes || 0) + 1; log(`${v === 'in' ? '🐝' : '🚫'} @${u} (${bee})`); }
      if (v === 'in' && !s.first_in) s.first_in = { author: u, permlink: c.permlink, created: c.created, cashout: c.payout_at };
    }
  }
}

// ---------- 2. thank-you vote (once per person, ever) ----------
async function chainPrices() {
  const [fund, med] = await Promise.all([
    client.call('condenser_api', 'get_reward_fund', ['post']),
    client.call('condenser_api', 'get_current_median_history_price', []),
  ]);
  const usdPerHive = parseFloat(med.base) / parseFloat(med.quote);
  return parseFloat(fund.reward_balance) / parseFloat(fund.recent_claims) * usdPerHive;   // USD per rshare
}
function bee(a) {   // voting mana and full-vote rshares of a bee
  const vests = parseFloat(a.vesting_shares) - parseFloat(a.delegated_vesting_shares) + parseFloat(a.received_vesting_shares);
  const max = vests * 1e6, m = a.voting_manabar;
  const cur = Math.min(max, +m.current_mana + max * (Date.now() / 1000 - m.last_update_time) / 432000);
  return { name: a.name, vp: max ? cur / max * 100 : 0, full: cur * 0.02 };   // a 100% vote spends 2% of the current mana
}

async function thank(state) {
  const due = Object.entries(state.people).filter(([u, s]) => s.first_in && !s.thanked).slice(0, MAX_THANKS_PER_RUN);
  if (!due.length) return;
  const usdPerRshare = await chainPrices();
  const bees = (await client.database.getAccounts(VOTERS)).map(bee);
  for (const [u, s] of due) {
    const left = (new Date(s.first_in.cashout + 'Z') - Date.now()) / 3600e3;
    if (!(left > MIN_LEFT_H)) { s.thanked = { skipped: 'too close to payout' }; log(`- @${u}: reply too old to vote`); continue; }
    const inviter = (state.invited[u] && state.invited[u].bee) || s.via;
    const order = [bees.find((b) => b.name === inviter), ...bees.filter((b) => b.name !== inviter && b.vp >= 80).sort((a, b) => b.vp - a.vp)]
      .filter(Boolean);
    const plan = []; let usd = 0;
    for (const b of order) { if (usd >= THANK_USD) break; plan.push(b); usd += b.full * usdPerRshare; }
    log(`🍯 @${u}: ${plan.map((b) => '@' + b.name).join(', ')} ≈ $${usd.toFixed(3)}`);
    if (!canBroadcast()) continue;
    const done = [];
    for (const b of plan) {
      try {
        await client.broadcast.vote({ voter: b.name, author: u, permlink: s.first_in.permlink, weight: 10000 }, key);
        done.push(b.name); b.full *= 0.98;
      } catch (e) { log(`  ✗ @${b.name}: ${e.message.split('\n')[0]}`); }
      await sleep(3500);
    }
    s.thanked = { at: new Date().toISOString(), by: done, usd: +usd.toFixed(3) };   // set even if partial: never a second round
    save(state);
  }
}

// ---------- 3. invitations ----------
async function candidates(group, exclude) {
  const pg = new PG({ host: 'hafsql-sql.mahdiyari.info', port: 5432, database: 'haf_block_log',
    user: 'hafsql_public', password: 'hafsql_public', statement_timeout: 300000 });
  await pg.connect();
  const minRaw = Math.pow(10, (MIN_REP - 25) / 9 + 9);
  const { rows } = await pg.query(`
    WITH p AS (SELECT author, count(*) n14, max(created) last_post,
                      sum(coalesce(total_payout_value,0)+coalesce(pending_payout_value,0)) rew
               FROM hafsql.comments WHERE parent_author='' AND created > now()-interval '14 days' AND NOT deleted GROUP BY author),
         r AS (SELECT p.*, sum(rew) OVER (ORDER BY rew DESC, author) - rew AS before, sum(rew) OVER () AS tot FROM p),
         dv AS (SELECT DISTINCT voter FROM hafsql.operation_vote_view
                WHERE author = ANY($1) AND weight < 0 AND timestamp > now()-interval '180 days')
    SELECT r.author FROM r JOIN hafsql.reputations rp ON rp.account_name = r.author
    WHERE (CASE WHEN r.before < 0.75*r.tot THEN 'top75' ELSE 'tail25' END) = $2
      AND r.n14 BETWEEN 2 AND 60 AND r.last_post > now()-interval '7 days' AND rp.reputation >= $3
      AND r.author NOT IN (SELECT voter FROM dv) AND NOT (r.author = ANY($4))
    ORDER BY random() LIMIT 40`, [FAMILY, group, minRaw, exclude]);
  await pg.end();
  return rows.map((r) => r.author);
}

async function invite(state, snaps) {
  const h = new Date().getUTCHours();
  if (h < DAY_UTC[0] || h >= DAY_UTC[1]) { log('night in the hive: no invitations now'); return; }
  if (state.last_invite && Date.now() - new Date(state.last_invite) < INVITE_EVERY_MIN * 60e3) return;
  const bees = Object.keys(snaps);
  if (!bees.length) return;
  const sender = bees[(state.batches || 0) % bees.length];
  const group = (state.batches || 0) % TOP_EVERY === TOP_EVERY - 1 ? 'top75' : 'tail25';
  const extra = readJson(path.join(DIR, 'buzz-exclude.json'), []);
  const known = new Set([...Object.keys(state.invited), ...Object.keys(state.people), ...extra, ...FAMILY]);
  const names = (await candidates(group, [...known])).filter((n) => !known.has(n)).slice(0, NAMES_PER_INVITE);
  if (!names.length) { log('no new candidates'); return; }
  const body = INVITE_TEXT(names);
  log(`📨 @${sender} (${group}): ${names.join(', ')}`);
  if (!canBroadcast()) { log('   ' + body); return; }
  const permlink = `buzz-invite-${Date.now().toString(36)}`;
  try {
    await client.broadcast.comment({ parent_author: sender, parent_permlink: snaps[sender], author: sender, permlink, title: '', body,
      json_metadata: JSON.stringify({ app: 'buzzlist/1.0', tags: ['buzzlist'] }) }, key);
  } catch (e) { log(`✗ invitation failed: ${e.message.split('\n')[0]}`); return; }
  const at = new Date().toISOString();
  for (const n of names) state.invited[n] = { bee: sender, at, permlink, group };
  state.last_invite = at; state.batches = (state.batches || 0) + 1;
  save(state);
}

(async () => {
  if (LIVE && !key) { console.log('Run it via run-with-key.sh'); process.exit(1); }
  if (fs.existsSync(STOP_FILE)) log('BUZZ_STOP present: read-only run');
  const snaps = readJson(CONFIG_FILE, {}).snaps || {};
  const state = Object.assign({ invited: {}, people: {} }, readJson(STATE_FILE, {}));
  await scanReplies(state, snaps);
  if (LIVE) save(state);
  await thank(state).catch((e) => log('thank error:', e.message));
  await invite(state, snaps).catch((e) => log('invite error:', e.message));
  if (LIVE) save(state);
  const ins = Object.values(state.people).filter((s) => s.status === 'in').length;
  log(`buzz list: ${ins} in · ${Object.keys(state.invited).length} invited · ${Object.keys(state.people).length} replied`);
  process.exit(0);
})();
