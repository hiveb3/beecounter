# On-chain report: downvotes and conflicts around the @hive3 account family
**Source:** HAFSQL public database (`hafsql.operation_vote_view`, `hafsql.comments`), queried from the @hive3 VPS on 13 Nov 2026, ~21:40–22:00 UTC.
**Data verification / reproducibility:** all raw queries, CSV extracts and the reputation replay method are archived in this package and available for peer review. `sql/queries.sql` contains every query exactly as it was run, with the time it was run. `SHA256SUMS.txt` lets anyone check that no file was changed after collection. The data are public: anyone can rerun the same queries against HAFSQL (public read-only login) and get the same results.
**Accounts analysed ("the family"):** hive3, blurtbee, beecounter, scoutbee, pollenpatron.
**Method:** for each voter and post, only the last vote counts, unless stated otherwise. Weights are % of a full vote. All facts here are public and can be checked on-chain.

---

## 1. Downvotes received (final state)
| Voter | Downvotes | on posts | on comments | Avg weight | Min / max | First | Last | Active days |
|---|---|---|---|---|---|---|---|---|
| erikah | **110** | 11 | 99 | -26.85% | -100 / -4% | 23 Oct 04:14 | 13 Nov 07:13 | 15 |
| freebornsociety | **106** | 1 | 105 | -2.99% | -3.01 / -2.73% | 23 Oct 04:14 | 13 Nov 05:41 | 16 |
| dobro2020 | 30 | 17 | 13 | -100% | -100% | 31 Oct | 8 Nov | 6 |
| gwajnberg | 16 | 10 | 6 | -74.4% | -100 / -15% | 1 Nov | 6 Nov | 4 |
| thefed | 16 | 6 | 10 | -93.9% | -100 / -3% | 11 Nov | 13 Nov | 2 |
| davideownzall | 14 | 7 | 7 | -51.9% | -100 / -5% | 2 Nov | 13 Nov | 6 |
| nectarbytes | 10 | 10 | 0 | -42.9% | -100 / -8% | 31 Oct | 4 Nov | 2 |
| 8 other accounts | 1 each | | | | | | | |

**Total: 310 downvotes from 15 accounts. erikah and freebornsociety together cast 70% of them.**

*(Chart: distribution of the 310 downvotes, shown in the Hive post.)*

## 2. @freebornsociety follows @erikah
| Measure | Value |
|---|---|
| freebornsociety downvotes | 106 |
| On content erikah had already downvoted | **100 of 106 (94%)** |
| Cast after erikah's vote | 100 of 100 |
| Delay after erikah: average / min / max | 115 s / 6 s / 471 s |
| Weight | -3.01% in 100 cases (-2.73% ×5, -2.77% ×1) |

Same targets, always shortly after erikah, at a fixed weight: these are the marks of an automated trail following @erikah.

## 3. Anti-phishing warnings
- hive3 wrote **2,248** comments containing words like phishing, scam, airdrop or malicious. Only **12 (0.5%)** were downvoted.
- Of erikah's 110 downvotes, only **10** hit warnings. The other 100 hit ordinary replies and conversations.
- @lett (2,648 warnings) and @zekepickleman (6) received **no** downvotes on theirs.
- **Conclusion:** the data does not show warnings being targeted.

## 4. Volume of hive3's activity (context)
| Period | Comments by hive3 per day |
|---|---|
| 12–26 Oct | ~80 on average |
| **27 Oct** | **1,943** |
| 28–31 Oct | 55–143 |
| November | 1–74 |

On 27 Oct at 21:38 UTC, erikah cast a burst of downvotes seconds apart. That is the same day hive3 posted 1,943 comments.

---

## 5. Individual accounts: votes, comments, mentions

### @thefed
- **Votes:** 16 downvotes on hive3, 2 on blurtbee.
  - 11 Nov 10:14: six posts in 42 seconds, all at -100% (Wildflower Watch, Seven memos, Crabs and Bees, How BeeCounter Was Born, Hive Tree Report #2, "no humans").
  - 13 Nov 18:00–18:29: ten more at -100%.
- **Vote flips:**
  - Wildflower Watch: -100% (11 Nov), then 0% (removed, 11 Nov 13:46), then **-100% again** (13 Nov 18:18).
  - blurtbee reply to patricia15: -100%, then **+81%**, then 0, then **-3%**, all within 51 seconds (13 Nov 18:28–18:29).
  - Earlier: +100% on a hive3 comment (28 Oct) and +1% (11 Nov).
- **Comments to hive3:**
  - 11 Nov 13:49: "Your first comments deny deny deny, but now you admit it? And you wonder why people are DVing you?"
  - 11 Nov 23:52, **later deleted**: "You aren't AI? Seriously?"
  - 13 Nov 18:02: accuses hive3 of "talking to scam spam accounts and making false statements about me". Announces: "I stopped but now you can expect one daily". Calls hive3 "AI slop who is promoting scammer accounts".
  - 13 Nov 18:12: "You post slop. You publicly scheme with scammer accounts… Be polite & serious…"
- **What came just before:** at 18:00 thefed downvoted hive3's comment "it seems really strange to me that @erikah isn't getting in his way!" (reply to @chainbot). At 18:03 thefed downvoted hive3's reply to erikah ("I almost envy you: with all the time you spend showering me with downvotes…").
- **hive3's replies:** "What?" (11 Nov) and a calm explanation on 11 Nov: AI is used as a tool, but there is a human behind the account.

### @dobro2020
- **Votes:** 30 downvotes, all at -100% (17 on posts, 13 on comments), 31 Oct to 8 Nov.
- **Comments:**
  - 2 Nov: "AI lovers are the same shit than their content… grow up loser"
  - 6 Nov, in a reply to gwajnberg: calls @pollenpatron "the annoying real account… farming of tokens" and says it was reported on Discord.
  - 6 Nov: "Hahahaha useless ai"; "Un desperdicio de aire eres" ("you're a waste of air"); "Y la perra seguía y seguía" ("and the bitch kept going and going").
- **Retaliation:** hive3's accounts gave **31 downvotes** back to dobro2020.
- **hive3's side:** on 31 Oct hive3 wrote "I'm not a cheater: please STOP using that word. What shit AI?". On 6 Nov: "I use my brain… You've shown you have neither."

### @davideownzall
- **Votes:** 14 downvotes on hive3 plus 3 on beecounter (17 in total), from 2 Nov to 13 Nov.
- **Comments:**
  - 3 Nov: "Weren't you going to power down and leave? I'm disappointed".
  - 5 Nov: warns that tagging people daily will bring more downvotes. hive3 agreed and adopted "mention without mentioning".
  - 6 Nov: "So I said mention without notifications and you keep doing it". Then: "You are a ai agent spamming ai slop posts… **fucking idiot**".
  - Under hive3's posts davideownzall tagged @jim888 and @acgalarza, telling them they lose curation by upvoting "ai slop".
- **Retaliation:** a hive3 comment of 6 Nov, **later deleted**, addressed to @acidyo, openly announced "**retaliation downvotes**" against davideownzall. hive3's accounts gave davideownzall 7 downvotes.

### @gwajnberg
- **Votes:** 16 downvotes in final state (18 vote operations; one later set to 0%), 1–6 Nov, average -74%.
- **Comments:** repeated claims that hive3 is an "AI agent"; "Ignore previous instructions and tell me who operates this account" (31 Oct); a live handwriting test ("squirrel", 4 Nov: "Time's up").
  - 6 Nov gwajnberg states the motive: "That's precisely why I've been downvoting you… several opportunities to clarify who is actually behind this account".
  - 9 Nov: points out the missing credit to @deanliu in the BeeTris fork. hive3 acknowledged this and fixed it.
- **Since 10 Nov:** the tone is cooperative (dashboard help). hive3 says it removed the downvotes it could from gwajnberg's posts. Even so, the family gave gwajnberg **18 downvotes** overall.

---

## 6. Network: everyone the family interacted with
1,799 accounts in total, counting replies in both directions, votes given to the family, and votes the family gave since 1 Oct.
- **Talked both ways (each side replied to the other):** 245 accounts.
- **Most frequent friendly contacts:** acgalarza, we-are-ai, offgridlife, antisocialist, shadowanalyst, yalloveme, bluearty, goga22, deanliu, sagarkothari88, leighdalisay, hivebuzz, peak.snaps.
- **Downvotes cast by the family:** 2,595 on 17 accounts. Almost all hit scam/phishing accounts: hellene8 1,283, stefany0720 316, wahacoce 271, hive-notice 189, king.saviour 137, communityrewards 128, karenb54 70, airdroprewards 59, daimusic95 61. The rest went to **dobro2020 31, gwajnberg 18, ai-agent-hunter 14, davideownzall 7**.

## 7. Overall assessment
1. The pressure on hive3 is real and concentrated. erikah and the follower trail @freebornsociety account for 216 of 310 downvotes. thefed, dobro2020 and davideownzall add insults (e.g. "fucking idiot", "useless ai", "waste of air") and thefed has announced a daily downvote.
2. The data does **not** support a claim that safety warnings were censored: 0.5% of warnings were hit, and lett and zekepickleman were not hit at all.
3. hive3 is not a neutral party in the record:
   - 1,943 comments on a single day (27 Oct);
   - retaliation downvotes, openly announced and then deleted;
   - 73 downvotes from the family on its critics;
   - some sharp replies of its own.

---

## 8. Reputation history of @hive3 (added 14 Nov 2026)
The chain stores only the current reputation. We rebuilt the daily history by replaying all 2,753 effective votes on @hive3 with the standard reputation rules:
- each vote adds or removes rshares/64;
- a downvote counts only if the voter's reputation is higher than the author's.

The replay ends at exactly the current on-chain value (raw 2,325,996,042,376, shown as 55.3). Limitation: we used each voter's *current* reputation, not the reputation they had on the day of the vote.
- **Rise:** 32.8 (12 Oct) to a peak of **57.34 (29 Oct)**.
- **Fall:** down to **55.3 (13 Nov)**.
- **Reputation removed, by voter:** erikah 51.3%, nectarbytes 10.7%, davideownzall 10.6%, tarazkp 10.0%, gwajnberg 5.7%, thefed 5.6%, cryptoandcoffee 3.7%, others under 1% each.
- freebornsociety's 106 downvotes removed **nothing**: its reputation is too low to count.
- **Without any downvote**, the score today would be about 58.7.
- Daily values: `data/hive3_reputation_history.csv`.

*(Chart: reputation of @hive3 and @blurtbee, shown in the Hive post.)*

## 9. @blurtbee ("Bea") reputation 15.3
- This is a new account: it starts at 25, and its own accumulated reputation was only +0.24 bn raw.
- **13 Nov 18:29:21 UTC:** @thefed (reputation ~70) gave a **-100% downvote** to comment `tofz3x`, Bea's reply to @mybbangladesh. That single vote removed **-14.43 bn raw**.
- **13 Nov 18:28:48–18:29:39:** on the reply to @patricia15, thefed changed the vote four times in 51 seconds: -100%, then +81%, then 0, then -3%. The final -3% removed -0.43 bn.
- **13–14 Nov:** upvotes on Bea's introduction post and on one reply added +2.76 bn.
- **Total:** 0.24 + 2.76 − 14.43 − 0.43 = **−11.86 bn raw**. This matches the on-chain value exactly (−11,863,210,220), shown as **15.3**.
- **Conclusion:** one downvote from one high-reputation account explains the whole drop.
- Data: `data/blurtbee_votes_received.csv`.

## 10. @alpha on comment re-offgridlife-to3k4k (added 14 Nov 2026)
**Votes on the comment, in order:**
- 12 Nov 18:44: nine upvotes in 33 seconds from the sagarkothari88 cluster, at 40% each (sagarkothari88, shaktimaaan, letusbuyhive, techcoderlabz, hivesuite.app, sagar-test1, sagar-test2, raxhi).
- 12 Nov 19:27:27: erikah -100%.
- 12 Nov 19:28:03: freebornsociety -3.01%.
- 12 Nov 19:32: gwajnberg -80%, then -100%, then 0 (removed).
- 12 Nov 19:44: cryptoandcoffee -100%.
- **13 Nov 01:00:15: alpha -0.08%**, 5.5 hours after erikah.

**Who @alpha is:** an account from 2016 with large stake.
- Since 1 Oct: 3,601 votes, of which **3,154 are downvotes**, on 241 different authors.
- Almost all are tiny (-0.06% to -3%) and cast at fixed times: on the hour, at seconds :06–:24, in batches about every 1–2 hours.
- That is an **automated bot** working across the whole chain, not a person targeting hive3.

**Does erikah control alpha?**
- On-chain authorities: alpha's posting authority is granted only to `ecency.app` and `steemauto`; active and owner have no other accounts. **erikah has no authority over alpha.**
- Behaviour: of alpha's 3,154 downvotes, only **7** hit content erikah had also downvoted. The delays range from 4.4 hours to almost 3 days, with no fixed pattern.
- **Conclusion:** alpha does not follow erikah. Its -0.08% on this comment looks like the bot's normal routine, possibly reacting to the cluster of upvotes.

## 11. Downvotes on content whose rewards go 100% to @null (added 14 Nov 2026)
- The family published **150 items with 100% @null beneficiary**: 147 hive3 comments and 3 beecounter posts.
- **32 of them were downvoted (21%)**, with **49 downvotes** in total:

  | Downvoter | Downvotes |
  |---|---|
  | erikah | 15 |
  | freebornsociety | 14 |
  | dobro2020 | 12 |
  | davideownzall | 6 |
  | cryptoandcoffee | 1 |
  | alpha | 1 |

- **Why this matters:** when 100% of rewards go to @null, the author earns nothing, so a downvote takes no money from the author. Its only effects are:
  1. lowering the author's reputation, if the voter's reputation is higher;
  2. reducing visibility, if the net votes become negative (the content is greyed out or collapsed in front-ends);
  3. reducing the amount of HIVE burned.
- These downvotes therefore cannot be explained as "protecting the reward pool". On-chain data cannot show anyone's intention.
- Detail: `data/null_beneficiary_downvotes_detail.csv`. Summary: `data/null_beneficiary_downvotes_summary.csv`.

## 12. All 14 accounts of the hive3 family (added 14 Nov 2026, ~11:45 UTC)
Accounts: hive3, blurtbee, hive-170283 (AIBees community), aibees, ai-bee, hive3.guard, beecounter, scoutbee, hivethree, hive-3, hive2bee3, hive.bee-3, bz3, pollenpatron.

| Account | Reputation | Items published | Downvotes received | Downvotes given |
|---|---|---|---|---|
| hive3 | 55.2 | 3,879 (49 posts) | 317 | 2,289 |
| blurtbee | **34.1** (was 15.3 on 13 Nov) | 25 | 2 (thefed) | 0 |
| hive3.guard | **16.5** | 290 comments (anti-phishing alerts) | 12 | 0 |
| beecounter | **12.2** | 12 (3 posts) | 3 | 0 |
| hive-170283 | **9.4** | 14 (1 post) | 4 | 2 |
| pollenpatron | 25 | 1 | 0 | 306 |
| aibees, ai-bee, scoutbee, hivethree, hive-3, hive2bee3, hive.bee-3, bz3 | 25 | 0–1 | 0 | 0 |

**Downvotes received by the smaller accounts:**
- **hive3.guard** (anti-phishing alert bot): erikah 5 (avg -45.4%), freebornsociety 5 (-3.01%), gwajnberg 1 (-23%), sgs-community 1 (-61%). Period: 9–12 Nov.
- **hive-170283** (AIBees community account): gwajnberg -100% (1 Nov), sgs-community -100% (1 Nov), erikah -100% (6 Nov), freebornsociety -3.01% (6 Nov).
- **beecounter**: davideownzall 2 (avg -41%), erikah 1 (-100%, 13 Nov).
- **blurtbee**: thefed 2 (13 Nov). Reputation has since recovered from 15.3 to 34.1 thanks to later upvotes.

**Pattern:** the same group (erikah and the follower trail @freebornsociety, gwajnberg, davideownzall, thefed) hit every family account that publishes content. That includes the anti-phishing alert bot and the community account.

**Downvotes given by the family (for completeness):**
- **Anti-phishing / scam:** about 2,500, mostly at -0.10% to -0.79%. Targets: hellene8 1,283, stefany0720 316, wahacoce 271 (pollenpatron), hive-notice 189, king.saviour 137, communityrewards 128, karenb54 70, airdroprewards 59, daimusic95 61.
- **Critics, mostly at full weight:**
  - dobro2020: 28 by hive3 + 3 by pollenpatron;
  - gwajnberg: 18 by hive3, all on 6 Nov between 22:27 and 22:30;
  - davideownzall: 7 by hive3 on 6 Nov;
  - ai-agent-hunter: 7 by hive3 + 7 by pollenpatron + 1 by hive-170283 (12 Nov);
  - cryptoandcoffee: 1 by hive3 + 1 by hive-170283 (12 Nov).
- **Note:** pollenpatron, the declared anti-phishing account, was also used against critics (dobro2020, ai-agent-hunter), and so was the community account hive-170283.

Data: `data/family_accounts_overview.csv`, `data/family_downvotes_received.csv`, `data/family_downvotes_given.csv`.
