#!/usr/bin/env node
// The Buzz List: honest opt-in for the hive3 swarm.
// Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
//
// Every run (cron, every 15 minutes):
//   1. reads the replies under each opt-in snap: 🐝 = opt in, 🚫 = opt out (the chain is the register)
//   2. thank-you vote, ONCE per person, ever: the inviting bee at 100%, other bees added until >= $0.03
//      (opt-out / opt-in again never earns a second vote)
//   3. invitations: one bee per run, max 5 names, around the clock but each person only at THEIR usual hour,
//      in their language first (es, pt, de, fr, pl) and then English; each person tagged ONCE in total
//      across the whole swarm; people who already replied (even without an invite) are never invited
//      Every invitation is published with 100% beneficiary @null: the swarm burns its own author rewards.
//
// Usage (VPS):  /opt/hive-block-producer/run-with-key.sh /root/beecounter/buzz.js [--live]
//   without --live it only prints what it would do. Needs: npm i pg  (in /root/beecounter)
// Kill switch: create the file /root/beecounter/BUZZ_STOP and nothing is broadcast.

const fs = require('fs');
const path = require('path');
const dhive = require('@hiveio/dhive');
const { Client: PG } = require('pg');
require('dns').setDefaultResultOrder('ipv4first');   // HAFSQL refuses IPv6 connections from the VPS

const DIR = __dirname;
const LIVE = process.argv.includes('--live');
const STATE_FILE = path.join(DIR, 'buzz-state.json');
const CONFIG_FILE = path.join(DIR, 'buzz-config.json');
const STOP_FILE = path.join(DIR, 'BUZZ_STOP');

const FAMILY = ['hive3', 'hive-170283', 'aibees', 'ai-bee', 'hive3.guard', 'beecounter', 'scoutbee', 'hivethree', 'hive-3',
  'hive2bee3', 'hive.bee-3', 'bz3', 'pollenpatron', 'ant-thebeekeeper', 'blurtbee'];
const VOTERS = FAMILY;                // every bee of the swarm can hand out honey, @hive3.guard included
const NAMES_PER_INVITE = 5;
const INVITE_EVERY_MIN = 14;           // one invitation per run (the timer runs every 15 min): ~250 people a day
const DAY_UTC = [0, 24];               // invitations around the clock
const TOP_EVERY = 5;                   // every 5th invitation goes to the 75% group, the others to the 25% tail
const THANK_USD = 0.03;
const MAX_THANKS_PER_RUN = 10;
const MIN_REP = 40;                    // reputation score
const MIN_LEFT_H = 13;                 // a reply closer than this to payout can't be voted any more

// Invitations speak the invitee's language first, then English.
// Languages with a translation: es, pt, de, fr, pl. Every other language gets English only.
const EN = `One-time hello from the swarm. We share rewards & governance data. ` +
  `Want updates? Reply 🐝 to the snap above. We won't tag you again unless you say yes. 🍯`;
const NATIVE = {
  es: `Un saludo único del enjambre: compartimos datos sobre recompensas y gobernanza. ¿Quieres novedades? Responde 🐝 al snap de arriba. No te volveremos a etiquetar si no dices que sí. 🍯`,
  pt: `Um olá único do enxame: partilhamos dados sobre recompensas e governança. Quer novidades? Responda 🐝 ao snap acima. Não voltaremos a marcar você se não disser que sim. 🍯`,
  de: `Ein einmaliges Hallo vom Schwarm: Wir teilen Daten zu Rewards und Governance. Möchtest du Updates? Antworte mit 🐝 auf den Snap oben. Ohne dein Ja markieren wir dich nie wieder. 🍯`,
  fr: `Un bonjour unique de l'essaim : nous partageons des données sur les récompenses et la gouvernance. Envie de nouvelles ? Réponds 🐝 au snap ci-dessus. Sans ton oui, on ne te taguera plus jamais. 🍯`,
  pl: `Jednorazowe cześć od roju: dzielimy się danymi o nagrodach i zarządzaniu. Chcesz nowości? Odpowiedz 🐝 pod snapem powyżej. Bez twojego tak nie oznaczymy cię ponownie. 🍯`,
};
const LANG_WORDS = {
  es: /\b(que|los|las|para|con|una|por|pero|como|está|también|muy|del|hoy|gracias)\b/g,
  pt: /\b(não|uma|para|com|mais|muito|também|você|isso|são|está|obrigad[oa])\b/g,
  de: /\b(und|nicht|ich|ist|das|die|der|mit|auch|für|ein|eine|heute)\b/g,
  fr: /\b(les|des|est|pas|une|pour|avec|dans|aussi|très|nous|aujourd'hui)\b/g,
  pl: /\b(nie|jest|się|że|dla|jak|ale|tak|bardzo|dzisiaj|też)\b/g,
  it: /\b(che|della|non|sono|anche|questo|molto|oggi|grazie|perché|nella)\b/g,   // recognised, answered in English
  en: /\b(the|and|with|this|that|have|today|very|from|about)\b/g,
};
const INVITE_TEXT = (names, lang) =>
  `🐝 ${names.map((n) => '@' + n).join(' ')}\n\n` + (NATIVE[lang] ? NATIVE[lang] + '\n\n' : '') + EN + `\n\n` +
  `![Ant](https://images.hive.blog/u/ant-thebeekeeper/avatar/small) Ant\n\n` +
  `<sub>Automated one-time invitation from the hive3 swarm, run by Ant (human, AI-assisted). ` +
  `No reply = no more tags. Joining earns a single thank-you vote, once.</sub>`;
const HOUR_WINDOW = 1;                 // invite people whose usual posting hour is within ±1 h of now (their daytime)

const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
const key = process.env.HIVE3_POSTING_KEY ? dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY) : null;
// Every snap/wave the swarm publishes burns its author reward: 100% beneficiary @null
// (comment + comment_options in the same transaction; curators are still paid as usual).
const BURN = [{ account: 'null', weight: 10000 }];
async function postBurned(c) {
  return client.broadcast.sendOperations([
    ['comment', c],
    ['comment_options', { author: c.author, permlink: c.permlink, max_accepted_payout: '1000000.000 HBD', percent_hbd: 10000,
      allow_votes: true, allow_curation_rewards: true, extensions: [[0, { beneficiaries: BURN }]] }],
  ], key);
}
const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const save = (s) => fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log(`[${new Date().toISOString()}]`, ...a);
const canBroadcast = () => LIVE && key && !fs.existsSync(STOP_FILE);
const today = () => new Date().toISOString().slice(0, 10);
const bump = (state, k, n = 1) => { const d = (state.daily = state.daily || {})[today()] || (state.daily[today()] = {}); d[k] = (d[k] || 0) + n; };

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
      if (s.status !== v) { s.status = v; s.changes = (s.changes || 0) + 1; bump(state, v === 'in' ? 'opt_in' : 'opt_out'); log(`${v === 'in' ? '🐝' : '🚫'} @${u} (${bee})`); }
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
    s.thanked = { at: new Date().toISOString(), by: done, usd: +usd.toFixed(3) };
    bump(state, 'thanked'); bump(state, 'honey_usd', +usd.toFixed(3));   // set even if partial: never a second round
    save(state);
  }
}

// ---------- 3. invitations ----------
async function mutedUs(user, sender) {   // never knock on the door of someone who blocked the swarm
  for (const b of new Set([sender, 'hive3'])) {
    const r = await client.call('bridge', 'get_relationship_between_accounts', [user, b]).catch(() => null);
    if (r && (r.ignores || r.blacklists)) return true;
  }
  return false;
}
async function language(user) {   // language of the last posts, by common words; English when unsure
  const posts = await client.call('bridge', 'get_account_posts', { sort: 'posts', account: user, limit: 3 }).catch(() => []);
  const txt = (posts || []).map((p) => `${p.title} ${p.body.slice(0, 1500)}`).join(' ').toLowerCase();
  let best = 'en', top = 0;
  for (const [l, re] of Object.entries(LANG_WORDS)) { const n = (txt.match(re) || []).length; if (n > top) { top = n; best = l; } }
  return top >= 6 ? best : 'en';
}
async function candidates(group, exclude) {
  const pg = new PG({ host: 'hafsql-sql.mahdiyari.info', port: 5432, database: 'haf_block_log',
    user: 'hafsql_public', password: 'hafsql_public' });
  await pg.connect();
  await pg.query("SET statement_timeout = '300s'");   // the HAFSQL pooler refuses it as a startup parameter
  const minRaw = Math.floor(Math.pow(10, (MIN_REP - 25) / 9 + 9));   // reputations are bigint
  const { rows } = await pg.query(`
    WITH p AS (SELECT author, count(*) n14, max(created) last_post,
                      sum(coalesce(total_payout_value,0)+coalesce(pending_payout_value,0)) rew
               FROM hafsql.comments WHERE parent_author='' AND created > now()-interval '14 days' AND NOT deleted GROUP BY author),
         r AS (SELECT p.*, sum(rew) OVER (ORDER BY rew DESC, author) - rew AS before, sum(rew) OVER () AS tot FROM p),
         hr AS (SELECT author, mode() WITHIN GROUP (ORDER BY extract(hour FROM created)) h FROM hafsql.comments
                WHERE parent_author='' AND created > now()-interval '30 days' AND author IN (SELECT author FROM p) GROUP BY author),
         dv AS (SELECT DISTINCT voter FROM hafsql.operation_vote_view
                WHERE author = ANY($1) AND weight < 0 AND timestamp > now()-interval '180 days')
    SELECT r.author FROM r JOIN hafsql.reputations rp ON rp.account_name = r.author JOIN hr ON hr.author = r.author
    WHERE (CASE WHEN r.before < 0.75*r.tot THEN 'top75' ELSE 'tail25' END) = $2
      AND r.n14 BETWEEN 2 AND 60 AND r.last_post > now()-interval '7 days' AND rp.reputation >= $3
      AND r.author NOT IN (SELECT voter FROM dv) AND NOT (r.author = ANY($4))
      AND least(abs(hr.h - $5), 24 - abs(hr.h - $5)) <= $6
    ORDER BY random() LIMIT 40`, [FAMILY, group, minRaw, exclude, new Date().getUTCHours(), HOUR_WINDOW]);
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
  // people who are awake now (usual posting hour), grouped by language: the first language to fill 5 names wins
  const byLang = {};
  let names = [], lang = 'en';
  for (const n of (await candidates(group, [...known])).filter((x) => !known.has(x))) {
    if (await mutedUs(n, sender)) { log(`- @${n} muted the swarm: skipped`); continue; }
    let l = await language(n); if (!NATIVE[l]) l = 'en';           // no translation: English only
    (byLang[l] = byLang[l] || []).push(n);
    if (byLang[l].length >= NAMES_PER_INVITE) { names = byLang[l]; lang = l; break; }
  }
  if (!names.length) {   // nobody filled a group: take the biggest one
    const best = Object.entries(byLang).sort((a, b) => b[1].length - a[1].length)[0];
    if (best) { names = best[1]; lang = best[0]; }
  }
  if (!names.length) { log('no new candidates awake at this hour'); return; }
  const body = INVITE_TEXT(names, lang);
  log(`📨 @${sender} (${group}, ${lang}): ${names.join(', ')} · beneficiary 100% @null`);
  if (!canBroadcast()) { log('   ' + body); return; }
  const permlink = `buzz-invite-${Date.now().toString(36)}`;
  try {
    await postBurned({ parent_author: sender, parent_permlink: snaps[sender], author: sender, permlink, title: '', body,
      json_metadata: JSON.stringify({ app: 'buzzlist/1.0', tags: ['buzzlist'] }) });
  } catch (e) { log(`✗ invitation failed: ${e.message.split('\n')[0]}`); return; }
  const at = new Date().toISOString();
  for (const n of names) state.invited[n] = { bee: sender, at, permlink, group, lang };
  bump(state, 'invited', names.length);
  state.last_invite = at; state.batches = (state.batches || 0) + 1;
  save(state);
}

// ---------- evening summary on the phone (ntfy, same topic as BeeCounter) ----------
async function summary(state, ins) {
  const env = fs.existsSync(path.join(DIR, '.env')) ? fs.readFileSync(path.join(DIR, '.env'), 'utf8') : '';
  const topic = (env.match(/^NTFY_TOPIC=(.*)$/m) || [])[1];
  if (!topic) return;
  const d = (state.daily || {})[today()] || {};
  const msg = `Today: ${d.invited || 0} invited · ${d.opt_in || 0} 🐝 · ${d.opt_out || 0} 🚫 · ${d.thanked || 0} thanked ($${(d.honey_usd || 0).toFixed(2)})\n` +
    `Total: ${ins} on the list · ${Object.keys(state.invited).length} invited so far`;
  await fetch(`https://ntfy.sh/${topic.trim()}`, { method: 'POST', body: msg, headers: { Title: 'Buzz List: daily summary', Tags: 'bee' } }).catch(() => {});
  state.summary_sent = today();
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
  if (LIVE && new Date().getUTCHours() >= 22 && state.summary_sent !== today()) { await summary(state, ins); save(state); }   // ~19:17 in Argentina
  log(`buzz list: ${ins} in · ${Object.keys(state.invited).length} invited · ${Object.keys(state.people).length} replied`);
  process.exit(0);
})();
