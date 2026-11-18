#!/bin/bash
# Installs the Blurt witness watchdog (alerts now, auto-disable prepared but OFF).
# Run as root:  bash install.sh
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
set -euo pipefail
BASE=https://raw.githubusercontent.com/hiveb3/beecounter/${REF:-main}/vps/blurt/watchdog
mkdir -p /opt/blurt-watchdog /root/beecounter
curl -sfL -o /opt/blurt-watchdog/watchdog.py "$BASE/watchdog.py"
chmod 755 /opt/blurt-watchdog/watchdog.py

# ---------- discovery (no secrets printed) ----------
D=/root/beecounter/blurt_watchdog_discovery.txt
{
  echo "=== discovery $(date -Is) ==="
  echo "--- containers ---"; docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}'
  C=$(docker ps --format '{{.Names}} {{.Image}}' | grep -i blurt | head -1 | cut -d' ' -f1 || true)
  echo "Blurt container: ${C:-NOT FOUND}"
  if [ -n "$C" ]; then
    echo "--- network mode / published ports ---"; docker inspect -f '{{.HostConfig.NetworkMode}} {{json .HostConfig.PortBindings}}' "$C"
    echo "--- binaries in container ---"; docker exec "$C" sh -c 'ls /usr/local/bin /usr/bin 2>/dev/null | grep -Ei "wallet|blurtd|steemd" | sort -u' || true
    echo "--- config.ini (keys redacted) ---"
    docker exec "$C" sh -c 'for f in $(find / -name config.ini -path "*blurt*" 2>/dev/null | head -3); do echo "# $f"; grep -E "^(webserver|plugin|witness|p2p-endpoint|shared-file|private-key)" "$f"; done' 2>/dev/null \
      | sed -E 's/(private-key *= *).*/\1<REDACTED>/' || true
  fi
  echo "--- listening ports on host ---"; ss -ltnp 2>/dev/null | grep -Ei 'blurt|8090|8091|8093|8095|8751|1776' || true
} > "$D" 2>&1
cat "$D"

# ---------- config (kept if it already exists) ----------
if [ ! -f /etc/blurt-watchdog.json ]; then
  TOPIC="bea-witness-$(openssl rand -hex 6)"
  cat > /etc/blurt-watchdog.json <<EOF
{
  "account": "blurtbee",
  "local_rpc": "",
  "ntfy_topic": "$TOPIC",
  "miss_threshold": 3,
  "miss_window_min": 30,
  "auto_disable": false,
  "disable_cmd": ""
}
EOF
  chmod 600 /etc/blurt-watchdog.json
fi

cat > /etc/systemd/system/blurt-watchdog.service <<'EOF'
[Unit]
Description=Blurt witness watchdog (@blurtbee)
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/blurt-watchdog/watchdog.py
Nice=10
EOF
cat > /etc/systemd/system/blurt-watchdog.timer <<'EOF'
[Unit]
Description=Run the Blurt witness watchdog every minute
[Timer]
OnBootSec=2min
OnUnitActiveSec=60s
AccuracySec=5s
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now blurt-watchdog.timer >/dev/null
python3 /opt/blurt-watchdog/watchdog.py -v || true

TOPIC=$(python3 -c "import json;print(json.load(open('/etc/blurt-watchdog.json'))['ntfy_topic'])")
curl -s -H "Title: Bea watchdog is on" -d "Alerts for @blurtbee are active 🐝" "https://ntfy.sh/$TOPIC" >/dev/null || true
echo
echo "BLURT WATCHDOG ATTIVO ✅  (controllo ogni minuto, spegnimento automatico ancora OFF)"
echo "Notifiche: installa l'app ntfy sul telefono e iscriviti al topic:  $TOPIC"
echo "Hai appena ricevuto una notifica di prova su quel topic."
