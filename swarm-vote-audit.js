// Audit: posts where the swarm both upvotes and downvotes (last N days, latest vote per voter).
// For every conflicting upvote, shows who voted the same post just before it (trail leader hint).
require('dns').setDefaultResultOrder('ipv4first');
const { Client } = require('pg');
const SWARM = ['hive3', 'hive3.guard', 'ant-thebeekeeper', 'blurtbee', 'beecounter', 'scoutbee', 'pollenpatron',
  'hive-170283', 'aibees', 'ai-bee', 'hivethree', 'hive-3', 'hive2bee3', 'hive.bee-3', 'bz3'];
const DAYS = +(process.argv[2] || 30);
(async () => {
  const c = new Client({ host: 'hafsql-sql.mahdiyari.info', user: 'hafsql_public', password: 'hafsql_public', database: 'haf_block_log' });
  await c.connect();
  const cols = (await c.query("select column_name from information_schema.columns where table_schema='hafsql' and table_name='operation_vote_view'")).rows.map(r => r.column_name);
  console.log('cols', cols.join(','));
  const r = await c.query(`
    with v as (select distinct on (voter, author, permlink) voter, author, permlink, weight, timestamp
               from hafsql.operation_vote_view
               where voter = any($1) and timestamp > now() - ($2 || ' days')::interval
               order by voter, author, permlink, id desc),
    p as (select author, permlink from v group by 1,2 having bool_or(weight > 0) and bool_or(weight < 0))
    select v.* from v join p using (author, permlink) order by v.author, v.permlink, v.timestamp`, [SWARM, String(DAYS)]);
  const posts = {};
  for (const x of r.rows) (posts[x.author + '/' + x.permlink] ||= []).push(x);
  console.log('conflict posts', Object.keys(posts).length);
  const byUp = {};
  for (const [k, vs] of Object.entries(posts)) {
    console.log('\n' + k);
    for (const x of vs) console.log(`  ${x.timestamp.toISOString()} ${x.voter} ${x.weight / 100}%`);
    for (const x of vs.filter(y => y.weight > 0)) {
      byUp[x.voter] = (byUp[x.voter] || 0) + 1;
      const [a, p] = k.split('/');
      const lead = await c.query(`select voter, weight, timestamp from hafsql.operation_vote_view
          where author=$1 and permlink=$2 and timestamp between $3::timestamp - interval '10 minutes' and $3::timestamp and voter <> $4
          order by timestamp desc limit 3`, [a, p, x.timestamp, x.voter]);
      console.log(`    before ${x.voter}: ` + lead.rows.map(l => `${l.voter} ${l.weight / 100}% ${Math.round((x.timestamp - l.timestamp) / 1000)}s`).join(' | '));
    }
  }
  console.log('\nconflicting upvotes by voter', JSON.stringify(byUp));
  await c.end();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
