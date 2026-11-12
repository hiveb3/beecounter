#!/usr/bin/env node
// Aggiunge @hive3 come authority (posting o, con --active, active) a tutti gli account creati da @hive3.
// Uso:  cd /root/beecounter && git pull && node grant-hive3.js [--active] [--dry]   (dhive già installato per publish.js)
// Per ogni account chiede la ACTIVE key (o la OWNER key con --active), input nascosto, mai salvata. Invio vuoto = salta.

const dhive = require('@hiveio/dhive');
const readline = require('readline');

const AUTHORITY = 'hive3';
// Tutti gli account creati da @hive3 (verificato on-chain, 12 nov 2026)
const ACCOUNTS = ['hive-170283', 'aibees', 'ai-bee', 'hive3.guard', 'beecounter', 'scoutbee'];
// --active: dà a @hive3 anche l'autorità ACTIVE (trasferimenti, deleghe...). Richiede la OWNER key.
const ROLE = process.argv.includes('--active') ? 'active' : 'posting';
const SIGNER = ROLE === 'active' ? 'owner' : 'active';
const DRY = process.argv.includes('--dry');
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
  for (const name of ACCOUNTS) {
    const acc = accounts.find((a) => a.name === name);
    if (!acc) { console.log(`✗ ${name}: non esiste, salto`); continue; }

    const auth = JSON.parse(JSON.stringify(acc[ROLE]));
    if (auth.account_auths.some(([n]) => n === AUTHORITY)) {
      console.log(`= ${name}: @${AUTHORITY} già presente`); continue;
    }
    auth.account_auths.push([AUTHORITY, auth.weight_threshold]); // hive3 da solo basta a firmare
    auth.account_auths.sort((a, b) => (a[0] < b[0] ? -1 : 1));     // la blockchain vuole l'ordine alfabetico

    if (DRY) { console.log(`~ ${name}: nuova ${ROLE} authority`, JSON.stringify(auth.account_auths)); continue; }

    const wif = await askHidden(`${SIGNER.toUpperCase()} key di @${name} (invio = salta): `);
    if (!wif) { console.log(`- ${name}: saltato`); continue; }
    let key;
    try { key = dhive.PrivateKey.fromString(wif); } catch { console.log(`✗ ${name}: chiave non valida`); continue; }
    const pub = key.createPublic().toString();
    if (!acc[SIGNER].key_auths.some(([k]) => k === pub)) { console.log(`✗ ${name}: non è la ${SIGNER} key di questo account`); continue; }

    try {
      const r = await client.broadcast.updateAccount({
        account: name, [ROLE]: auth, memo_key: acc.memo_key, json_metadata: acc.json_metadata,
      }, key);
      console.log(`✓ ${name}: @${AUTHORITY} aggiunto come ${ROLE} (tx ${r.id})`);
    } catch (e) { console.log(`✗ ${name}: ${e.message}`); }
  }
})();
