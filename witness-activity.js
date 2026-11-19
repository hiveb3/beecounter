// Witness ranking recomputed by dropping votes from accounts inactive for N months/years.
// Witnesses: top N ACTIVE ones (signing key set and a block produced in the last 30 days).
// v2 activity = latest of:
//   - last_vote_time, last_post, last_root_post, last_update (HAFSQL)
//   - RC manabar last_update_time (rc_api): moves whenever the account pays RC for ANY
//     transaction, so Splinterlands / game custom_json, transfers and dApp actions count too.
// Weight = voter own HP + HP of every account proxying to it, also through proxy chains
// (A -> B -> C), each proxier filtered by ITS OWN activity: an active proxy carries only
// the HP of proxiers that are active too.
require('dns').setDefaultResultOrder('ipv4first');
const { Client } = require('pg');
const fs = require('fs');
const DAY = 864e5;
const CUTS = [['all', Infinity], ['6m', 182], ['1y', 365], ['2y', 730], ['3y', 1095], ['4y', 1461], ['5y', 1826]];
const N = +(process.argv[2] || 100);
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
  const head = (await rpc('condenser_api.get_dynamic_global_properties', [])).head_block_number;
  const all = await rpc('condenser_api.get_witnesses_by_vote', ['', 250]);
  const list = all.filter(w => w.signing_key !== NULL_KEY && head - w.last_confirmed_block_num < 30 * 28800).slice(0, N);
  log('active witnesses', list.length, 'of', all.length, 'last', list[list.length - 1].owner);
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
  // RC last_update_time = last transaction the account paid for (games, transfers, custom_json...)
  let rcHits = 0;
  for (let i = 0; i < names.length; i += 500) {
    const r = await rpc('rc_api.find_rc_accounts', { accounts: names.slice(i, i + 500) });
    for (const x of r.rc_accounts) {
      const a = info[x.account]; if (!a) continue;
      const t = +x.rc_manabar.last_update_time * 1000;
      if (t > a.la) { a.la = t; rcHits++; }
    }
    if (i % 10000 === 0) log('rc', i);
  }
  log('rc newer than social activity for', rcHits, 'accounts');
  const now = Date.now();
  const rows = list.map((w, i) => {
    const row = { witness: w.owner, chain: i + 1, voters: voters[w.owner].length };
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
  const res = { at: new Date().toISOString(), rcHits, tot, dist, distS, rows };
  fs.writeFileSync('witness-activity.json', JSON.stringify(res, null, 1));
  const M = x => (x / 1e6).toFixed(2);
  console.log(`tot ${M(tot)} | ` + CUTS.map(([k]) => `${k} ${M(dist[k] || 0)}/${M(distS[k] || 0)}`).join(' | ') + ` | rcHits ${rcHits}`);
  console.log('witness,voters,' + CUTS.map(([k]) => k).join(',') + ',social6m');
  for (const r of rows) console.log([r.witness, r.voters, ...CUTS.map(([k]) => M(r[k])), M(r.s6m)].join(','));
  log('done');
})().catch(e => { log('ERR', e.message); process.exit(1); });
