#!/usr/bin/env node
// Adds @hive3 as an authority (posting, or active with --active) to every account of the hive3 swarm.
// Usage:  cd /root/beecounter && git pull && node grant-hive3.js [--active] [--dry]   (dhive is already installed for publish.js)
// For each account it asks for the ACTIVE key (or the OWNER key with --active): hidden input, never saved. Empty = skip.

const dhive = require('@hiveio/dhive');
const readline = require('readline');

const AUTHORITY = 'hive3';
// Every account of the hive3 swarm (checked on chain, Nov 2026)
const ACCOUNTS = [
  'hive-170283', 'aibees', 'ai-bee', 'hive3.guard', 'beecounter', 'scoutbee', // created by hive3
  'hivethree', 'hive-3', 'hive2bee3', 'hive.bee-3', 'bz3', 'pollenpatron',    // created by others
  'ant-thebeekeeper', 'blurtbee',                                             // the voices of the swarm
];
// --active: also gives @hive3 the ACTIVE authority (transfers, delegations...). Needs the OWNER key.
const ROLE = process.argv.includes('--active') ? 'active' : 'posting';
const SIGNER = ROLE === 'active' ? 'owner' : 'active';
const DRY = process.argv.includes('--dry');
// Non-interactive mode: WIF=<key> node grant-hive3.js --only=<account>  (used by grant-hive3.sh)
const ONLY = (process.argv.find((a) => a.startsWith('--only=')) || '').slice(7);
const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);

function askHidden(q) {
  return new Promise((res) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: true });
    rl.stdoutMuted = false;
    rl._writeToOutput = (s) => { if (!rl.stdoutMuted) rl.output.write(s); };
    rl.question(q, (a) => { rl.close(); process.stdout.write('\n'); res(a.trim()); });
    rl.stdoutMuted = true;
  });
}

(async () => {
  const accounts = await client.database.getAccounts(ACCOUNTS);
  for (const name of ACCOUNTS.filter((n) => !ONLY || n === ONLY)) {
    const acc = accounts.find((a) => a.name === name);
    if (!acc) { console.log(`✗ ${name}: does not exist, skipped`); continue; }

    const auth = JSON.parse(JSON.stringify(acc[ROLE]));
    if (auth.account_auths.some(([n]) => n === AUTHORITY)) {
      console.log(`= ${name}: @${AUTHORITY} already there`); continue;
    }
    auth.account_auths.push([AUTHORITY, auth.weight_threshold]); // hive3 alone is enough to sign
    auth.account_auths.sort((a, b) => (a[0] < b[0] ? -1 : 1));     // the chain wants alphabetical order

    if (DRY) { console.log(`~ ${name}: new ${ROLE} authority`, JSON.stringify(auth.account_auths)); continue; }

    const wif = process.env.WIF ? process.env.WIF.trim() : await askHidden(`${SIGNER.toUpperCase()} key of @${name} (enter = skip): `);
    if (!wif) { console.log(`- ${name}: skipped`); continue; }
    let key;
    try { key = dhive.PrivateKey.fromString(wif); } catch { console.log(`✗ ${name}: invalid key`); continue; }
    const pub = key.createPublic().toString();
    if (!acc[SIGNER].key_auths.some(([k]) => k === pub)) { console.log(`✗ ${name}: not the ${SIGNER} key of this account`); continue; }

    try {
      const r = await client.broadcast.updateAccount({
        account: name, [ROLE]: auth, memo_key: acc.memo_key, json_metadata: acc.json_metadata,
      }, key);
      console.log(`✓ ${name}: @${AUTHORITY} added as ${ROLE} (tx ${r.id})`);
    } catch (e) { console.log(`✗ ${name}: ${e.message}`); }
  }
  process.exit(0);
})();
