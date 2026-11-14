-- Exact queries run on HAFSQL (hafsql-sql.mahdiyari.info, db haf_block_log, public login hafsql_public)

-- al1  Hive API condenser_api.get_accounts [["alpha", "erikah", "freebornsociety"]]

-- al2  (run 2026-11-14T11:20:41.152993Z, 3154 rows)
WITH a AS (SELECT author,permlink,min(timestamp) ta,min(weight) wa FROM hafsql.operation_vote_view WHERE voter='alpha' AND weight<0 AND timestamp>='2026-10-01' GROUP BY 1,2), e AS (SELECT author,permlink,min(timestamp) te FROM hafsql.operation_vote_view WHERE voter='erikah' AND weight<0 AND timestamp>='2026-10-01' GROUP BY 1,2) SELECT a.author, a.permlink, a.ta, a.wa/100.0 pct, e.te erikah_dv, extract(epoch FROM a.ta-e.te) delay_s FROM a LEFT JOIN e USING(author,permlink) ORDER BY a.ta;

-- al3  (run 2026-11-14T11:20:52.017999Z, 20 rows)
SELECT v.voter, v.timestamp, v.weight/100.0 pct FROM hafsql.operation_vote_view v WHERE v.author='hive3' AND v.permlink='re-offgridlife-to3k4k' ORDER BY v.timestamp;

-- al4  (run 2026-11-14T11:20:57.044445Z, 1 rows)
SELECT count(*) votes, sum((weight<0)::int) dv, sum((weight>0)::int) up, min(timestamp) first, max(timestamp) last, count(DISTINCT author) authors FROM hafsql.operation_vote_view WHERE voter='alpha' AND timestamp>='2026-10-01';

-- fm1  (run 2026-11-14T11:44:35.405570Z, 26 rows)
WITH f AS (SELECT unnest(ARRAY['hive3','blurtbee','hive-170283','aibees','ai-bee','hive3.guard','beecounter','scoutbee','hivethree','hive-3','hive2bee3','hive.bee-3','bz3','pollenpatron']) a), lv AS (SELECT DISTINCT ON (v.voter,v.author,v.permlink) v.voter,v.author,v.permlink,v.weight,v.timestamp FROM hafsql.operation_vote_view v WHERE v.author IN (SELECT a FROM f) ORDER BY v.voter,v.author,v.permlink,v.timestamp DESC) SELECT lv.author, lv.voter, count(*) n, round(avg(lv.weight)/100.0,2) avg_pct, min(lv.timestamp) first, max(lv.timestamp) last FROM lv WHERE lv.weight<0 GROUP BY 1,2 ORDER BY 1,3 DESC;

-- fm2  (run 2026-11-14T11:44:36.213637Z, 14 rows)
WITH f AS (SELECT unnest(ARRAY['hive3','blurtbee','hive-170283','aibees','ai-bee','hive3.guard','beecounter','scoutbee','hivethree','hive-3','hive2bee3','hive.bee-3','bz3','pollenpatron']) a) SELECT f.a, r.reputation, (SELECT count(*) FROM hafsql.comments c WHERE c.author=f.a) items, (SELECT count(*) FROM hafsql.comments c WHERE c.author=f.a AND c.parent_author='') posts, (SELECT count(*) FROM hafsql.operation_vote_view v WHERE v.voter=f.a AND v.weight<0) dv_given, (SELECT count(*) FROM hafsql.operation_vote_view v WHERE v.voter=f.a AND v.weight>0) up_given FROM f LEFT JOIN hafsql.reputations r ON r.account_name=f.a;

-- fm3  (run 2026-11-14T11:44:46.759782Z, 22 rows)
SELECT v.voter, v.author, count(*) n, round(avg(v.weight)/100.0,2) avg_pct, min(v.timestamp) first, max(v.timestamp) last FROM hafsql.operation_vote_view v WHERE v.voter IN ('hive3','blurtbee','hive-170283','aibees','ai-bee','hive3.guard','beecounter','scoutbee','hivethree','hive-3','hive2bee3','hive.bee-3','bz3','pollenpatron') AND v.weight<0 GROUP BY 1,2 ORDER BY 3 DESC;

-- fx1  (run 2026-11-13T21:37:44.619152Z, 15 rows)
WITH lv AS (SELECT DISTINCT ON (voter,author,permlink) voter,author,permlink,weight,timestamp FROM hafsql.operation_vote_view WHERE author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') ORDER BY voter,author,permlink,timestamp DESC) SELECT lv.voter, count(*) n, sum(CASE WHEN c.parent_author='' THEN 1 ELSE 0 END) posts, sum(CASE WHEN c.parent_author<>'' THEN 1 ELSE 0 END) comments, round(avg(lv.weight)/100.0,2) avg_pct, min(lv.weight)/100.0 min_pct, max(lv.weight)/100.0 max_pct, min(lv.timestamp) first, max(lv.timestamp) last, count(DISTINCT lv.timestamp::date) days, string_agg(DISTINCT lv.author, ',') targets FROM lv LEFT JOIN hafsql.comments c ON c.author=lv.author AND c.permlink=lv.permlink WHERE lv.weight<0 GROUP BY lv.voter ORDER BY n DESC;

-- fx2  (run 2026-11-13T21:38:41.002766Z, 1 rows)
WITH e AS (SELECT author,permlink,min(timestamp) te FROM hafsql.operation_vote_view WHERE voter='erikah' AND weight<0 AND author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') GROUP BY 1,2), f AS (SELECT author,permlink,min(timestamp) tf,min(weight) wf FROM hafsql.operation_vote_view WHERE voter='freebornsociety' AND weight<0 AND author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') GROUP BY 1,2) SELECT (SELECT count(*) FROM f) freeborn_total, (SELECT count(*) FROM e) erikah_total, count(e.permlink) in_common, sum(CASE WHEN f.tf>=e.te THEN 1 ELSE 0 END) after_erikah, round(avg(extract(epoch FROM f.tf-e.te))::numeric,1) avg_delay_s, min(extract(epoch FROM f.tf-e.te)) min_delay_s, max(extract(epoch FROM f.tf-e.te)) max_delay_s, (SELECT string_agg(w||'%:'||n, ' ') FROM (SELECT wf/100.0 w, count(*) n FROM f GROUP BY wf ORDER BY 2 DESC LIMIT 8) x) weights FROM f LEFT JOIN e ON e.author=f.author AND e.permlink=f.permlink;

-- fx3  (run 2026-11-13T21:38:44.940522Z, 4903 rows)
SELECT c.created, c.author, c.permlink, c.parent_author, c.parent_permlink, c.total_payout_value, c.net_rshares, left(regexp_replace(c.body,'\s+',' ','g'),160) excerpt, (SELECT string_agg(v.voter||'('||v.weight/100.0||'%)', ' ') FROM hafsql.operation_vote_view v WHERE v.author=c.author AND v.permlink=c.permlink AND v.weight<0) downvotes FROM hafsql.comments c WHERE c.author IN ('hive3','blurtbee','lett','zekepickleman') AND c.parent_author<>'' AND (c.body ILIKE '%phishing%' OR c.body ILIKE '%scam%' OR c.body ILIKE '%fake airdrop%' OR c.body ILIKE '%malicious%') ORDER BY c.created;

-- fx5  (run 2026-11-13T21:42:28.721700Z, 110 rows)
SELECT v.timestamp, v.weight/100.0 pct, c.parent_author, c.permlink, left(regexp_replace(c.body,'\s+',' ','g'),110) excerpt FROM hafsql.operation_vote_view v JOIN hafsql.comments c ON c.author=v.author AND c.permlink=v.permlink WHERE v.voter='erikah' AND v.weight<0 AND v.author IN ('hive3','beecounter') ORDER BY v.timestamp;

-- fx7  (run 2026-11-13T21:43:24.432711Z, 32 rows)
SELECT created::date d, count(*) n, sum((parent_author='')::int) posts FROM hafsql.comments WHERE author='hive3' AND created>='2026-10-01' GROUP BY 1 ORDER BY 1;

-- nl1  (run 2026-11-14T11:23:16.490146Z, 1208 rows)
WITH c AS (SELECT author, permlink, created, parent_author, beneficiaries::text ben, left(regexp_replace(body,'\s+',' ','g'),100) excerpt FROM hafsql.comments WHERE author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') AND beneficiaries::text ILIKE '%"null"%'), lv AS (SELECT DISTINCT ON (v.voter,v.author,v.permlink) v.voter,v.author,v.permlink,v.weight,v.timestamp FROM hafsql.operation_vote_view v JOIN c ON c.author=v.author AND c.permlink=v.permlink ORDER BY v.voter,v.author,v.permlink,v.timestamp DESC) SELECT c.author, c.permlink, c.created, c.parent_author, c.ben, c.excerpt, lv.voter, lv.weight/100.0 pct, lv.timestamp FROM c LEFT JOIN lv ON lv.author=c.author AND lv.permlink=c.permlink ORDER BY c.created, lv.timestamp;

-- nw1  (run 2026-11-13T21:56:26.552334Z, 569 rows)
SELECT parent_author acct, count(*) n FROM hafsql.comments WHERE author IN ('hive3','blurtbee','beecounter','scoutbee') AND parent_author<>'' GROUP BY 1 ORDER BY 2 DESC;

-- nw2  (run 2026-11-13T21:56:27.334758Z, 261 rows)
SELECT author acct, count(*) n FROM hafsql.comments WHERE parent_author IN ('hive3','blurtbee','beecounter','scoutbee') GROUP BY 1 ORDER BY 2 DESC;

-- nw3  (run 2026-11-13T21:56:27.775729Z, 1290 rows)
SELECT voter acct, sum((weight>0)::int) up, sum((weight<0)::int) dv FROM hafsql.operation_vote_view WHERE author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') GROUP BY 1 ORDER BY 2 DESC;

-- nw4  (run 2026-11-13T21:56:38.898294Z, 536 rows)
SELECT author acct, sum((weight>0)::int) up, sum((weight<0)::int) dv FROM hafsql.operation_vote_view WHERE voter IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') AND timestamp>='2026-10-01' GROUP BY 1 ORDER BY 2 DESC;

-- rb1  (run 2026-11-14T11:07:13.750805Z, 16 rows)
SELECT v.timestamp, v.voter, v.permlink, v.rshares, r.reputation vrep, (SELECT reputation FROM hafsql.reputations WHERE account_name='blurtbee') brep, left(regexp_replace(coalesce(c.body,''),'\s+',' ','g'),90) excerpt, c.parent_author FROM hafsql.operation_effective_comment_vote_view v LEFT JOIN hafsql.reputations r ON r.account_name=v.voter LEFT JOIN hafsql.comments c ON c.author=v.author AND c.permlink=v.permlink WHERE v.author='blurtbee' ORDER BY v.timestamp;

-- rp2  (run 2026-11-13T22:53:35.053129Z, 2753 rows)
SELECT v.timestamp, v.voter, v.permlink, v.rshares, r.reputation vrep, (SELECT reputation FROM hafsql.reputations WHERE account_name='hive3') hrep FROM hafsql.operation_effective_comment_vote_view v LEFT JOIN hafsql.reputations r ON r.account_name=v.voter WHERE v.author='hive3' ORDER BY v.timestamp;

-- tf2  (run 2026-11-13T21:51:22.213905Z, 23 rows)
SELECT v.timestamp, v.weight/100.0 pct, v.author, v.permlink, c.parent_author, left(regexp_replace(c.body,'\s+',' ','g'),140) excerpt FROM hafsql.operation_vote_view v LEFT JOIN hafsql.comments c ON c.author=v.author AND c.permlink=v.permlink WHERE v.voter='thefed' AND v.author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') ORDER BY v.timestamp;

-- tf3  (run 2026-11-13T21:54:15.306883Z, 89 rows)
SELECT v.voter, v.timestamp, v.weight/100.0 pct, v.author, v.permlink, c.parent_author, c.deleted, left(regexp_replace(coalesce(c.body,''),'\s+',' ','g'),140) excerpt FROM hafsql.operation_vote_view v LEFT JOIN hafsql.comments c ON c.author=v.author AND c.permlink=v.permlink WHERE v.voter IN ('thefed','dobro2020','davideownzall','gwajnberg') AND v.author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') ORDER BY v.voter, v.author, v.permlink, v.timestamp;

-- tf5  (run 2026-11-13T21:56:47.403907Z, 70 rows)
SELECT c.author, c.created, c.deleted, c.parent_author, c.parent_permlink, c.permlink, regexp_replace(c.body,'\s+',' ','g') body FROM hafsql.comments c WHERE c.created>='2026-10-01' AND ((c.author IN ('thefed','dobro2020','davideownzall','gwajnberg') AND (c.parent_author IN ('hive3','blurtbee','beecounter','scoutbee','pollenpatron') OR c.body ILIKE '%hive3%' OR c.body ILIKE '%blurtbee%' OR c.body ILIKE '%beecounter%' OR c.body ILIKE '%scoutbee%' OR c.body ILIKE '%pollenpatron%')) OR (c.author IN ('hive3','blurtbee','beecounter') AND c.parent_author IN ('thefed','dobro2020','davideownzall','gwajnberg'))) ORDER BY c.created;
