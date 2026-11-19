// Witness ranking recomputed by dropping votes from accounts inactive for N months/years.
// Activity = latest of last_vote_time, last_post, last_root_post, last_update.
// Weight = voter own HP + HP of accounts proxying to it (each filtered by its own activity).
require('dns').setDefaultResultOrder('ipv4first');
const { Client } = require('pg');
const fs = require('fs');
const DAY = 864e5;
const CUTS = [['all', Infinity], ['6m', 182], ['1y', 365], ['2y', 730], ['3y', 1095], ['4y', 1461], ['5y', 1826]];
const N = +(process.argv[2] || 50);
const rpc = async (method, params) => (await (await fetch('https://api.hive.blog', { method: 'POST', body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) })).json()).result;
const log = (...a) => console.error(new Date().toISOString(), ...a);
(async () => {
  const list = await rpc('condenser_api.get_witnesses_by_vote', ['', N]);
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
  const need = new Set();
  for (const vs of Object.values(voters)) for (const v of vs) { need.add(v); for (const p of proxied[v] || []) need.add(p); }
  const info = {};
  const names = [...need];
  for (let i = 0; i < names.length; i += 3000) {
    const r = await c.query(`select a.name, coalesce(a.proxy,'') proxy, b.hp_equivalent::float8 hp,
      greatest(coalesce(a.last_vote_time,'1970-01-01'), coalesce(a.last_post,'1970-01-01'),
               coalesce(a.last_root_post,'1970-01-01'), coalesce(a.last_update,'1970-01-01')) la
      from hafsql.accounts a join hafsql.balances b on b.account_name = a.name where a.name = any($1)`, [names.slice(i, i + 3000)]);
    for (const x of r.rows) info[x.name] = { proxy: x.proxy, hp: x.hp, la: new Date(x.la).getTime() };
    log('accounts', i);
  }
  await c.end();
  const now = Date.now();
  const rows = list.map(w => {
    const row = { witness: w.owner, chain_mvests: +w.votes / 1e12, voters: voters[w.owner].length };
    for (const [k] of CUTS) row[k] = 0;
    const add = n => { const a = info[n]; if (!a) return; const age = (now - a.la) / DAY; for (const [k, d] of CUTS) if (age <= d) row[k] += a.hp; };
    for (const v of voters[w.owner]) { if (info[v] && info[v].proxy) continue; add(v); for (const p of proxied[v] || []) add(p); }
    return row;
  });
  const rank = {};
  for (const [k] of CUTS) [...rows].sort((a, b) => b[k] - a[k]).forEach((x, i) => { (rank[x.witness] ||= {})[k] = i + 1; });
  // activity distribution of all voters' HP (unique accounts)
  const dist = {}; let tot = 0;
  for (const n of need) { const a = info[n]; if (!a) continue; tot += a.hp; const age = (now - a.la) / DAY; for (const [k, d] of CUTS) if (age <= d) dist[k] = (dist[k] || 0) + a.hp; }
  fs.writeFileSync('witness-activity.json', JSON.stringify({ at: new Date().toISOString(), rows, rank, dist, tot }, null, 1));
  console.log(JSON.stringify({ rows, rank, dist, tot }));
  log('done');
})().catch(e => { log('ERR', e.message); process.exit(1); });
