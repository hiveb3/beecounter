// Witness ranking recomputed by dropping votes from accounts inactive for N months/years.
// Witnesses: top N enabled ones (signing key set) + EXTRA ones; idle = days since their last block.
// v3 activity = block of the last operation SIGNED by the account (games/Splinterlands,
// transfers, posts, votes, dApps...). Not counted: virtual ops (received delegations,
// rewards, interest), claim_reward_balance, feed_publish, Hive-Engine auto-claims.
// social6m = old social-only measure (last post/vote/profile update) for comparison.
// Weight = voter own HP + HP of every account proxying to it, also through proxy chains
// (A -> B -> C), each proxier filtered by ITS OWN activity: an active proxy carries only
// the HP of proxiers that are active too.
// Usage: node witness-activity.js [N=100] [extra witnesses, comma separated = hive3]
require('dns').setDefaultResultOrder('ipv4first');
const { Client } = require('pg');
const fs = require('fs');
const DAY = 864e5;
const CUTS = [['all', Infinity], ['6m', 182], ['1y', 365], ['2y', 730], ['3y', 1095], ['4y', 1461], ['5y', 1826]];
const N = +(process.argv[2] || 100);
const EXTRA = (process.argv[3] || 'hive3').split(',');
const NULL_KEY = 'STM1111111111111111111111111111111114T1Anm';
const NODES = ['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network'];
const rpc = async (method, params) => {
  for (let t = 0; t < 6; t++) {
    try {
      const r = await (await fetch(NODES[t % NODES.length], { method: 'POST', body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) })).json();
      if (r.result) return r.result;
    } catch {}
    await new Promise(r => setTimeout(r, 1500));
  }
  throw new Error('rpc failed ' + method);
};
const log = (...a) => console.error(new Date().toISOString(), ...a);
(async () => {
  const head0 = (await rpc('condenser_api.get_dynamic_global_properties', [])).head_block_number;
  const all = await rpc('condenser_api.get_witnesses_by_vote', ['', 250]);
  all.forEach((w, i) => { w.chainRank = i + 1; });
  const enabled = all.filter(w => w.signing_key !== NULL_KEY);
  const list = enabled.filter((w, i) => i < N || EXTRA.includes(w.owner));
  for (const w of list) w.idleDays = Math.round((head0 - w.last_confirmed_block_num) / 28800);
  log('witnesses', list.length, 'enabled', enabled.length, 'of', all.length);
  const c = new Client({ host: 'hafsql-sql.mahdiyari.info', user: 'hafsql_public', password: 'hafsql_public', database: 'haf_block_log' });
  await c.connect();
  const proxied = {}; // proxy -> [names]
  for (const r of (await c.query("select name, proxy from hafsql.accounts where proxy is not null and proxy <> ''")).rows) (proxied[r.proxy] ||= []).push(r.name);
  log('proxiers', Object.values(proxied).flat().length);
  const voters = {};
  for (const w of list) {
    const r = await c.query(`select account from (select distinct on (account) account, approve from hafsql.operation_account_witness_vote_table
                              where witness = $1 order by account, id desc) v where approve`, [w.owner]);
    voters[w.owner] = r.rows.map(x => x.account);
    log('votes', w.owner, voters[w.owner].length);
  }
  // every account whose HP can reach a witness: direct voters + whole proxy trees under them
  const tree = (n, depth, out) => { for (const p of proxied[n] || []) if (!out.has(p) && depth < 5) { out.add(p); tree(p, depth + 1, out); } };
  const need = new Set();
  for (const vs of Object.values(voters)) for (const v of vs) { need.add(v); tree(v, 0, need); }
  const info = {};
  const names = [...need];
  for (let i = 0; i < names.length; i += 3000) {
    const r = await c.query(`select a.name, coalesce(a.proxy,'') proxy, b.hp_equivalent::float8 hp,
      greatest(coalesce(a.last_vote_time,'1970-01-01'), coalesce(a.last_post,'1970-01-01'),
               coalesce(a.last_root_post,'1970-01-01'), coalesce(a.last_update,'1970-01-01')) la
      from hafsql.accounts a join hafsql.balances b on b.account_name = a.name where a.name = any($1)`, [names.slice(i, i + 3000)]);
    for (const x of r.rows) info[x.name] = { proxy: x.proxy, hp: x.hp, la: new Date(x.la).getTime(), laSocial: new Date(x.la).getTime() };
    log('accounts', i);
  }
  await c.end();
  // v3: last operation SIGNED by the account itself (hafd account_operations.transacting_account_id).
  // Excluded: virtual ops (received delegations, rewards, interest...), claim_reward_balance (39),
  // feed_publish (7), Hive-Engine auto-claims (custom_json scot_claim_token / scot_claim).
  const head = (await rpc('condenser_api.get_dynamic_global_properties', [])).head_block_number;
  const c2 = new Client({ host: 'hafsql-sql.mahdiyari.info', user: 'hafsql_public', password: 'hafsql_public', database: 'haf_block_log' });
  await c2.connect();
  let signedHits = 0;
  for (let i = 0; i < names.length; i += 200) {
    const batch = names.slice(i, i + 200);
    let r;
    for (let t = 0; t < 3; t++) {
      try {
        r = await c2.query(`select a.name, x.block_num from hafsql.accounts a cross join lateral (
            select ao.block_num from hive.account_operations_view ao
            where ao.account_id = a.id and ao.transacting_account_id = a.id
              and ao.op_type_id < 50 and ao.op_type_id not in (7, 39)
              and not (ao.op_type_id = 18 and exists (select 1 from hafsql.operation_custom_json_view j
                        where j.id = ao.operation_id and j.custom_id in ('scot_claim_token','scot_claim')))
            order by ao.account_op_seq_no desc limit 1) x
          where a.name = any($1)`, [batch]);
        break;
      } catch (e) { log('signed retry', i, e.message); if (t === 2) { log('signed FAIL batch', i); r = { rows: [] }; } }
    }
    for (const x of r.rows) {
      const a = info[x.name]; if (!a) continue;
      a.la = Date.now() - (head - x.block_num) * 3000; signedHits++;
    }
    if (i % 10000 === 0) log('signed', i);
  }
  await c2.end();
  log('accounts with a signed op found', signedHits, 'of', names.length);
  const now = Date.now();
  const rows = list.map(w => {
    const row = { witness: w.owner, chain: w.chainRank, idle: w.idleDays, voters: voters[w.owner].length };
    for (const [k] of CUTS) { row[k] = 0; row['s' + k] = 0; }
    const add = n => {
      const a = info[n]; if (!a) return;
      const age = (now - a.la) / DAY, ageS = (now - a.laSocial) / DAY;
      for (const [k, d] of CUTS) { if (age <= d) row[k] += a.hp; if (ageS <= d) row['s' + k] += a.hp; }
    };
    for (const v of voters[w.owner]) {
      if (info[v] && info[v].proxy) continue;           // has a proxy: its own witness votes don't count
      const t = new Set([v]); tree(v, 0, t);
      for (const n of t) add(n);                        // each account filtered by its own activity
    }
    return row;
  });
  const dist = {}, distS = {}; let tot = 0;
  for (const n of need) {
    const a = info[n]; if (!a) continue; tot += a.hp;
    for (const [k, d] of CUTS) { if ((now - a.la) / DAY <= d) dist[k] = (dist[k] || 0) + a.hp; if ((now - a.laSocial) / DAY <= d) distS[k] = (distS[k] || 0) + a.hp; }
  }
  const res = { at: new Date().toISOString(), signedHits, tot, dist, distS, rows };
  fs.writeFileSync('witness-activity.json', JSON.stringify(res, null, 1));
  const M = x => (x / 1e6).toFixed(2);
  console.log(`tot ${M(tot)} | ` + CUTS.map(([k]) => `${k} ${M(dist[k] || 0)}/${M(distS[k] || 0)}`).join(' | ') + ` | signedHits ${signedHits}`);
  console.log('witness,chain,idle,voters,' + CUTS.map(([k]) => k).join(',') + ',social6m');
  for (const r of rows) console.log([r.witness, r.chain, r.idle, r.voters, ...CUTS.map(([k]) => M(r[k])), M(r.s6m)].join(','));
  log('done');
})().catch(e => { log('ERR', e.message); process.exit(1); });
