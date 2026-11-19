// Witness ranking recomputed by dropping votes from accounts inactive for N years.
// Activity = latest of last_vote_time, last_post, last_root_post, last_update.
// Weight = voter own HP + HP of accounts proxying to it (each filtered by its own activity).
require('dns').setDefaultResultOrder('ipv4first');
const { Client } = require('pg');
const fs = require('fs');
const CUTS = [['all', null], ['6m', '6 months'], ['1y', '1 year'], ['2y', '2 years'], ['3y', '3 years'], ['4y', '4 years'], ['5y', '5 years']];
(async () => {
  const c = new Client({ host: 'hafsql-sql.mahdiyari.info', user: 'hafsql_public', password: 'hafsql_public', database: 'haf_block_log' });
  await c.connect();
  await c.query("SET statement_timeout = '600s'");
  const col = (k, iv) => iv ? `(la >= now() - interval '${iv}')` : 'true';
  const sums = CUTS.map(([k, iv]) => `sum(case when ${col(k, iv)} then w else 0 end)::float8 as "${k}"`).join(',');
  const q = `
  with v as (select distinct on (account, witness) account, witness, approve
             from hafsql.operation_account_witness_vote_table order by account, witness, id desc),
  cur as (select account, witness from v where approve),
  acc as (select a.name, coalesce(a.proxy,'') proxy, b.hp_equivalent::float8 hp,
          greatest(coalesce(a.last_vote_time,'1970-01-01'), coalesce(a.last_post,'1970-01-01'),
                   coalesce(a.last_root_post,'1970-01-01'), coalesce(a.last_update,'1970-01-01')) la
          from hafsql.accounts a join hafsql.balances b on b.account_name = a.name),
  wts as (
    select acc.name voter, acc.hp w, acc.la from acc where acc.proxy = ''
    union all
    select p.proxy voter, p.hp w, p.la from acc p where p.proxy <> ''
  )
  select cur.witness, ${sums}, count(distinct cur.account) voters
  from cur join wts on wts.voter = cur.account
  group by cur.witness order by "all" desc limit 80`;
  const t0 = Date.now();
  const r = await c.query(q);
  await c.end();
  const rows = r.rows;
  const rank = {};
  for (const [k] of CUTS) {
    [...rows].sort((a, b) => b[k] - a[k]).forEach((x, i) => { (rank[x.witness] ||= {})[k] = i + 1; });
  }
  const top = rows.slice(0, 40);
  const M = n => (n / 1e6).toFixed(1);
  let md = `| # | Witness | ${CUTS.map(([k]) => k).join(' | ')} |\n|---|---|${CUTS.map(() => '---').join('|')}|\n`;
  top.forEach((x, i) => {
    md += `| ${i + 1} | ${x.witness} | ` + CUTS.map(([k]) => `${rank[x.witness][k]} (${M(x[k])}M, ${Math.round(100 * x[k] / x.all)}%)`).join(' | ') + ' |\n';
  });
  fs.writeFileSync('witness-activity.json', JSON.stringify({ at: new Date().toISOString(), rows, rank }, null, 1));
  fs.writeFileSync('witness-activity.md', md);
  console.log(md);
  console.log(`seconds ${(Date.now() - t0) / 1000}`);
})().catch(e => { console.error(e.message); process.exit(1); });
