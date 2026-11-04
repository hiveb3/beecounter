#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# Encrypts the posting key with systemd-creds, deletes the plain-text copy and installs systemd timers.
# Usage (once): bash secure.sh
set -e
cd /root/beecounter
CRED=/etc/credstore.encrypted/beecounter-posting-key.cred
mkdir -p /etc/credstore.encrypted && chmod 700 /etc/credstore.encrypted
KEY=$(grep -s '^BEECOUNTER_POSTING_KEY=' .env | cut -d= -f2- || true)
if [ -z "$KEY" ] || [ "$KEY" = "PASTE_POSTING_KEY_HERE" ]; then
  read -rsp "Paste the bot posting key (hidden): " KEY; echo
fi
case "$KEY" in 5*) ;; *) echo "Invalid key (must start with 5)"; exit 1;; esac
printf '%s' "$KEY" | systemd-creds encrypt --name=beecounter-posting-key - "$CRED"
chmod 600 "$CRED"; unset KEY
# check
systemd-creds decrypt --name=beecounter-posting-key "$CRED" - | grep -q '^5' && echo "Key encrypted and verified: $CRED"
# .env without the key
AUTO=$(grep -s '^AUTO_PUBLISH=' .env | cut -d= -f2- || echo 0)
shred -u .env 2>/dev/null || rm -f .env
printf 'AUTO_PUBLISH=%s\n' "${AUTO:-0}" > .env; chmod 600 .env
# systemd timers instead of cron
for kind in daily monthly; do
cat > /etc/systemd/system/beecounter-$kind.service <<UNIT
[Unit]
Description=BeeCounter $kind report
After=network-online.target
[Service]
Type=oneshot
WorkingDirectory=/root/beecounter
LoadCredentialEncrypted=beecounter-posting-key:$CRED
ExecStart=/root/beecounter/$kind.sh
StandardOutput=append:/root/beecounter/beecounter.log
StandardError=append:/root/beecounter/beecounter.log
Nice=10
UNIT
done
cat > /etc/systemd/system/beecounter-daily.timer <<'UNIT'
[Unit]
Description=BeeCounter daily report (01:30 UTC)
[Timer]
OnCalendar=*-*-* 01:30:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
UNIT
cat > /etc/systemd/system/beecounter-monthly.timer <<'UNIT'
[Unit]
Description=BeeCounter monthly ledger (2nd of month, 04:00 UTC)
[Timer]
OnCalendar=*-*-02 04:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
UNIT
crontab -l 2>/dev/null | grep -v beecounter | crontab - || true
systemctl daemon-reload
systemctl enable --now beecounter-daily.timer beecounter-monthly.timer
systemctl list-timers 'beecounter-*' --no-pager
echo "Done: key encrypted, no plain-text copy, timers active."
