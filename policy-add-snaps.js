#!/usr/bin/env node
// One-off edit of the Swarm Policy post: the opt-in bullet in every language now says that ONE answer
// counts for the whole swarm and links all five opt-in snaps. Dry run by default, --live to publish.
// Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
// Usage (VPS): /opt/hive-block-producer/run-with-key.sh /root/beecounter/policy-add-snaps.js [--live]
const dhive = require('@hiveio/dhive');
const AUTHOR = 'hive3', PERMLINK = 'our-swarm-policy-how-the-hive3-bees-vote-tag-and-guard-out-in-the-open';
const S = '[@hive3](/@hive3/re-peaksnaps-torjbj) · [@ant-thebeekeeper](/@ant-thebeekeeper/re-peaksnaps-tormgt) · ' +
  '[@blurtbee](/@blurtbee/re-peaksnaps-tormjk) · [@beecounter](/@beecounter/re-peaksnaps-tormkh) · [@scoutbee](/@scoutbee/re-peaksnaps-tormm5)';
const EDITS = [
  ['- Reply 🐝 to join, 🚫 to leave, under [our opt-in snap](/@hive3/re-peaksnaps-torjbj). Your answer lives on chain, not in a private list of ours.',
   `- Copy-paste the bee 🐝 as your reply to join, 🚫 to leave, under **any** of our opt-in snaps: ${S}\n- **One answer counts for the whole swarm**: you don't need to reply to every bee. Your answer lives on chain, not in a private list of ours.`],
  ['- Responde 🐝 para unirte y 🚫 para salir, bajo [nuestro snap](/@hive3/re-peaksnaps-torjbj). Tu respuesta queda en la cadena, no en una lista privada nuestra.',
   `- Copia y pega la abeja 🐝 como respuesta para unirte, 🚫 para salir, bajo **cualquiera** de nuestros snaps: ${S}\n- **Una sola respuesta vale para todo el enjambre**: no hace falta responder a cada abeja. Tu respuesta queda en la cadena, no en una lista privada nuestra.`],
  ['- Responda 🐝 para entrar e 🚫 para sair, no [nosso snap](/@hive3/re-peaksnaps-torjbj). A sua resposta fica na blockchain, não numa lista privada nossa.',
   `- Copie e cole a abelha 🐝 como resposta para entrar, 🚫 para sair, em **qualquer** um dos nossos snaps: ${S}\n- **Uma só resposta vale para o enxame inteiro**: não precisa responder a cada abelha. A sua resposta fica na blockchain, não numa lista privada nossa.`],
  ['- Antworte mit 🐝, um mitzumachen, mit 🚫, um auszutreten, unter [unserem Snap](/@hive3/re-peaksnaps-torjbj). Deine Antwort steht auf der Blockchain, nicht in einer privaten Liste von uns.',
   `- Kopiere die Biene 🐝 als Antwort, um mitzumachen, oder 🚫, um auszutreten, unter **einem beliebigen** unserer Snaps: ${S}\n- **Eine Antwort gilt für den ganzen Schwarm**: Du musst nicht jeder Biene antworten. Deine Antwort steht auf der Blockchain, nicht in einer privaten Liste von uns.`],
  ['- Réponds 🐝 pour nous rejoindre, 🚫 pour partir, sous [notre snap](/@hive3/re-peaksnaps-torjbj). Ta réponse vit sur la blockchain, pas dans une liste privée à nous.',
   `- Copie-colle l'abeille 🐝 en réponse pour nous rejoindre, 🚫 pour partir, sous **n'importe lequel** de nos snaps : ${S}\n- **Une seule réponse vaut pour tout l'essaim** : inutile de répondre à chaque abeille. Ta réponse vit sur la blockchain, pas dans une liste privée à nous.`],
  ['- Odpowiedz 🐝, by dołączyć, 🚫, by wyjść, pod [naszym snapem](/@hive3/re-peaksnaps-torjbj). Twoja odpowiedź żyje na blockchainie, a nie na naszej prywatnej liście.',
   `- Skopiuj pszczołę 🐝 jako odpowiedź, by dołączyć, albo 🚫, by wyjść, pod **dowolnym** z naszych snapów: ${S}\n- **Jedna odpowiedź wystarczy dla całego roju**: nie musisz odpowiadać każdej pszczole. Twoja odpowiedź żyje na blockchainie, a nie na naszej prywatnej liście.`],
];
const client = new dhive.Client(['https://api.hive.blog', 'https://api.deathwing.me', 'https://api.openhive.network']);
(async () => {
  const c = await client.call('condenser_api', 'get_content', [AUTHOR, PERMLINK]);
  let body = c.body, n = 0;
  for (const [a, b] of EDITS) { if (body.includes(a)) { body = body.replace(a, b); n++; } else if (body.includes(b)) console.log('already edited:', a.slice(0, 40)); else console.log('NOT FOUND:', a.slice(0, 60)); }
  console.log(`${n}/6 language sections changed`);
  if (!n || !process.argv.includes('--live')) { console.log(n ? '(dry run: add --live to publish)' : 'nothing to do'); process.exit(0); }
  const r = await client.broadcast.comment({ parent_author: c.parent_author, parent_permlink: c.parent_permlink, author: AUTHOR, permlink: PERMLINK,
    title: c.title, body, json_metadata: c.json_metadata }, dhive.PrivateKey.fromString(process.env.HIVE3_POSTING_KEY));
  console.log(`edited @${AUTHOR}/${PERMLINK} (tx ${r.id})`);
  process.exit(0);
})().catch((e) => { console.log('error:', e.message); process.exit(1); });
