// Witness ranking recomputed by dropping votes from accounts inactive for N months/years.
// Activity = latest of last_vote_time, last_post, last_root_post, last_update.
// Weight = voter own HP + HP of accounts proxying to it (each filtered by its own activity).
require('dns').setDefaultResultOrder('ipv4first');
const { Client } = require('pg');
const fs = require('fs');
const CUTS = [['all', null], ['6m', '6 months'], ['1y', '1 year'], ['2y', '2 years'], ['3y', '3 years'], ['4y', '4 years'], ['5y', '5 years']];
const N = +(process.argv[2] || 50);
const rpc = async (method, params) => (await (await fetch('https://api.hive.blog', { method: 'POST', body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) })).json()).result;
(async () => {
  const list = await rpc('condenser_api.get_witnesses_by_vote', ['', N]);
  const c = new Client({ host: 'hafsql-sql.mahdiyari.info', user: 'hafsql_public', password: 'hafsql_public', database: 'haf_block_log' });
  await c.connect();
  const sums = CUTS.map(([k, iv]) => `sum(case when ${iv ? `la >= now() - interval '${iv}'` : 'true'} then w else 0 end)::float8 as "${k}"`).join(',');
  const rows = [];
  for (const w of list) {
    const q = `
    with v as (select distinct on (account) account, approve from hafsql.operation_account_witness_vote_table
               where witness = $1 order by account, id desc),
    cur as (select account from v where approve),
    acc as (select a.name, coalesce(a.proxy,'') proxy, b.hp_equivalent::float8 hp,
            greatest(coalesce(a.last_vote_time,'1970-01-01'), coalesce(a.last_post,'1970-01-01'),
                     coalesce(a.last_root_post,'1970-01-01'), coalesce(a.last_update,'1970-01-01')) la
            from hafsql.accounts a join hafsql.balances b on b.account_name = a.name),
    own as (select acc.hp w, acc.la from cur join acc on acc.name = cur.account and acc.proxy = ''),
    prx as (select p.hp w, p.la from cur join acc p on p.proxy = cur.account),
    wts as (select * from own union all select * from prx)
    select ${sums}, (select count(*) from cur)::int voters from wts`;
    try {
      const r = (await c.query(q, [w.owner])).rows[0];
      rows.push({ witness: w.owner, chain_mvests: +w.votes / 1e12, ...r });
      console.error('ok', w.owner);
    } catch (e) { console.error('fail', w.owner, e.message); }
  }
  await c.end();
  const rank = {};
  for (const [k] of CUTS) [...rows].sort((a, b) => b[k] - a[k]).forEach((x, i) => { (rank[x.witness] ||= {})[k] = i + 1; });
  const M = n => (n / 1e6).toFixed(1);
  let md = `| # chain | Witness | ${CUTS.map(([k]) => k).join(' | ')} |\n|---|---|${CUTS.map(() => '---').join('|')}|\n`;
  rows.forEach((x, i) => {
    md += `| ${i + 1} | ${x.witness} | ` + CUTS.map(([k]) => `${rank[x.witness][k]} · ${M(x[k])}M · ${Math.round(100 * x[k] / x.all)}%`).join(' | ') + ' |\n';
  });
  fs.writeFileSync('witness-activity.json', JSON.stringify({ at: new Date().toISOString(), rows, rank }, null, 1));
  fs.writeFileSync('witness-activity.md', md);
  console.log(JSON.stringify({ rows, rank }));
})().catch(e => { console.error(e.message); process.exit(1); });
