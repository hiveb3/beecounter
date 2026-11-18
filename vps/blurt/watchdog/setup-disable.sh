#!/bin/bash
# Prepares (and TESTS, without broadcasting) the automatic "disable witness" command for @blurtbee.
# - creates a dedicated cli_wallet file inside the blurtd container, holding ONLY the block signing key
#   (the same key that is already in config.ini; no active/owner key is ever stored)
# - builds a witness_set_properties tx that sets the signing key to the null key, with broadcast=false
# - writes the test output to /root/beecounter/blurt_watchdog_test.txt for review
# auto_disable stays OFF: it is switched on only after the test output has been checked.
# Run as root:  REF=<commit> bash setup-disable.sh
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
set -euo pipefail
BASE=https://raw.githubusercontent.com/hiveb3/beecounter/${REF:-main}/vps/blurt/watchdog
curl -sfL -o /opt/blurt-watchdog/walletrpc.sh "$BASE/walletrpc.sh"
curl -sfL -o /opt/blurt-watchdog/props.py "$BASE/props.py"
. /opt/blurt-watchdog/walletrpc.sh
ACC=blurtbee; NULL=BLT1111111111111111111111111111111114T1Anm
CFG=/etc/blurt-watchdog.json; OUT=/root/beecounter/blurt_watchdog_test.txt
RED='s/(5[HJK][1-9A-HJ-NP-Za-km-z]{49})/<WIF-REDACTED>/g'
trap wr_stop EXIT

# (re)create the dedicated wallet: new password, signing key only
PW=$(openssl rand -hex 16)
WIF=$(docker exec "$WR_C" sh -c "grep -E '^private-key' /blurtd/config.ini | head -1 | sed -E 's/^private-key *= *//; s/[\"[:space:]]//g'")
[ -n "$WIF" ] || { echo "signing key not found in config.ini"; exit 1; }
docker exec "$WR_C" rm -f "$WR_WALLET"
wr_start
S1=$(wr_call set_password "[\"$PW\"]")
S2=$(wr_call unlock "[\"$PW\"]")
S3=$(wr_call import_key "[\"$WIF\"]")
unset WIF
S4=$(wr_call list_keys "[]" | sed -E "$RED")
wr_stop
docker exec "$WR_C" chmod 600 "$WR_WALLET" 2>/dev/null || true
python3 - "$CFG" "$PW" <<'EOF'
import json, sys
p, pw = sys.argv[1], sys.argv[2]
c = json.load(open(p)); c['wallet_pw'] = pw
json.dump(c, open(p, 'w'), indent=1)
EOF

# disable script used by the watchdog (broadcast=true)
cat > /opt/blurt-watchdog/disable.sh <<EOF
#!/bin/bash
# Sets @$ACC's block signing key to the null key (stops block production, no more missed blocks).
. /opt/blurt-watchdog/walletrpc.sh
trap wr_stop EXIT
PW=\$(python3 -c "import json;print(json.load(open('$CFG'))['wallet_pw'])")
wr_start || exit 1
U=\$(wr_call unlock "[\"\$PW\"]")
P=\$(python3 /opt/blurt-watchdog/props.py $ACC $NULL true) || exit 1
R=\$(wr_call update_witness_properties "\$P")
echo "\$R" | head -c 600
echo "\$R" | grep -q 'witness_set_properties' && ! echo "\$R" | grep -q '"error"' && ! echo "\$R" | grep -q '"signatures":\\[\\]'
EOF
chmod 700 /opt/blurt-watchdog/disable.sh

# dry run: same call with broadcast=false
wr_start
D1=$(wr_call unlock "[\"$PW\"]")
P=$(python3 /opt/blurt-watchdog/props.py "$ACC" "$NULL" false)
D2=$(wr_call update_witness_properties "$P")
wr_stop
{
  echo "=== wallet setup ==="
  echo "set_password: $S1"; echo "unlock: $S2"; echo "import_key: $(echo "$S3" | sed -E "$RED")"; echo "list_keys: $S4"
  echo "=== dry run $(date -Is) (broadcast=false, nothing sent to the chain) ==="
  echo "unlock: $D1"
  echo "params: $P"
  echo "update_witness_properties: $(echo "$D2" | head -c 1500)"
  if echo "$D2" | grep -q '"new_signing_key","0000000000000000000000000000000000000000000000000000000000000000' \
     && ! echo "$D2" | grep -q '"key","0000000000000000000000000000000000000000000000000000000000000000' \
     && ! echo "$D2" | grep -q '"signatures":\[\]' && ! echo "$D2" | grep -q '"error"'; then
    echo "RESULT: DRY RUN OK"
  else
    echo "RESULT: DRY RUN FAILED"
  fi
} > "$OUT"
cat "$OUT"

python3 - "$CFG" <<'EOF'
import json, sys
p = sys.argv[1]; c = json.load(open(p))
c['local_rpc'] = 'http://127.0.0.1:8191'
c['disable_cmd'] = '/opt/blurt-watchdog/disable.sh'
c.setdefault('auto_disable', False)
json.dump(c, open(p, 'w'), indent=1)
print('config:', {k: v for k, v in c.items() if k != 'wallet_pw'})
EOF
