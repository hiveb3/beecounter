#!/bin/bash
# Prepares (and TESTS, without broadcasting) the automatic "disable witness" command for @blurtbee.
# - creates a dedicated cli_wallet file inside the blurtd container, holding ONLY the block signing key
#   (the same key that is already in config.ini; no active/owner key is ever stored)
# - builds a witness_set_properties tx that sets the signing key to the null key, with broadcast=false
# - writes the test output to /root/beecounter/blurt_watchdog_test.txt for review
# auto_disable stays OFF: it is switched on only after the test output has been checked.
# Run as root:  bash setup-disable.sh
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
set -euo pipefail
C=blurtd; ACC=blurtbee; WS=ws://127.0.0.1:8190; WALLET=/blurtd/watchdog-wallet.json
NULL=BLT1111111111111111111111111111111114T1Anm
CFG=/etc/blurt-watchdog.json; OUT=/root/beecounter/blurt_watchdog_test.txt

PW=$(python3 -c "import json;print(json.load(open('$CFG')).get('wallet_pw',''))")
if [ -z "$PW" ] || ! docker exec "$C" test -f "$WALLET"; then
  PW=$(openssl rand -hex 16)
  WIF=$(docker exec "$C" sh -c "grep -E '^private-key' /blurtd/config.ini | head -1 | sed -E 's/^private-key *= *//; s/[\"[:space:]]//g'")
  [ -n "$WIF" ] || { echo "signing key not found in config.ini"; exit 1; }
  docker exec "$C" rm -f "$WALLET"
  printf 'set_password %s\nunlock %s\nimport_key %s\n' "$PW" "$PW" "$WIF" \
    | docker exec -i "$C" cli_wallet -s "$WS" -w "$WALLET" >/dev/null 2>&1 || true
  unset WIF
  docker exec "$C" chmod 600 "$WALLET"
  python3 - "$CFG" "$PW" <<'EOF'
import json, sys
p, pw = sys.argv[1], sys.argv[2]
c = json.load(open(p)); c['wallet_pw'] = pw
json.dump(c, open(p, 'w'), indent=1)
EOF
fi

# disable script used by the watchdog (broadcast=true)
cat > /opt/blurt-watchdog/disable.sh <<EOF
#!/bin/bash
# Sets @$ACC's block signing key to the null key (stops block production, no more missed blocks).
PW=\$(python3 -c "import json;print(json.load(open('$CFG'))['wallet_pw'])")
OUT=\$(printf 'unlock %s\nupdate_witness_properties $ACC {"new_signing_key":"$NULL"} true\n' "\$PW" | docker exec -i $C cli_wallet -s $WS -w $WALLET 2>&1)
echo "\$OUT" | tail -n 30
echo "\$OUT" | grep -q '"witness_set_properties"' && ! echo "\$OUT" | grep -qiE 'error|exception'
EOF
chmod 700 /opt/blurt-watchdog/disable.sh

# dry run: same command with broadcast=false
TEST=$(printf 'unlock %s\nlist_keys\nupdate_witness_properties %s {"new_signing_key":"%s"} false\n' "$PW" "$ACC" "$NULL" \
  | docker exec -i "$C" cli_wallet -s "$WS" -w "$WALLET" 2>&1 | sed -E 's/(5[HJK][1-9A-HJ-NP-Za-km-z]{49})/<WIF-REDACTED>/g')
{
  echo "=== dry run $(date -Is) (broadcast=false, nothing sent to the chain) ==="
  echo "$TEST" | tail -n 60
  if echo "$TEST" | grep -q '"witness_set_properties"' && ! echo "$TEST" | grep -qiE 'error|exception'; then
    echo "RESULT: DRY RUN OK"
  else
    echo "RESULT: DRY RUN FAILED"
  fi
} > "$OUT"
cat "$OUT"

# local Blurt RPC + disable command in the config (auto_disable stays as it is)
python3 - "$CFG" <<'EOF'
import json, sys
p = sys.argv[1]; c = json.load(open(p))
c['local_rpc'] = 'http://127.0.0.1:8191'
c['disable_cmd'] = '/opt/blurt-watchdog/disable.sh'
c.setdefault('auto_disable', False)
json.dump(c, open(p, 'w'), indent=1)
print('config:', {k: v for k, v in c.items() if k != 'wallet_pw'})
EOF
