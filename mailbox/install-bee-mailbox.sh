#!/bin/bash
# Bee Mailbox installer - run on the VPS as root:  bash install-bee-mailbox.sh
set -e
REPO_NAME="hiveb3/bee-mailbox"
read -rsp "Incolla il token GitHub (non si vede mentre scrivi) e premi Invio: " TOKEN; echo
[ -n "$TOKEN" ] || { echo "Token vuoto"; exit 1; }

mkdir -p /opt/bee-mailbox && cd /opt/bee-mailbox
cp "$(dirname "$0")/mailbox.py" /opt/bee-mailbox/mailbox.py 2>/dev/null || true
[ -f mailbox.py ] || { echo "mailbox.py non trovato accanto all'installer"; exit 1; }

# token saved only here, readable only by root, used only for this repo
printf 'https://x-access-token:%s@github.com\n' "$TOKEN" > /opt/bee-mailbox/.git-credentials
chmod 600 /opt/bee-mailbox/.git-credentials

rm -rf repo
git -c credential.helper="store --file=/opt/bee-mailbox/.git-credentials" clone -q "https://github.com/$REPO_NAME.git" repo
cd repo
git config credential.helper "store --file=/opt/bee-mailbox/.git-credentials"
git config user.name "bee-mailbox"; git config user.email "bee-mailbox@users.noreply.github.com"
git config pull.rebase true
mkdir -p requests results; touch requests/.keep results/.keep
cat > README.md <<'EOF'
# Bee Mailbox (private)
Claude writes `requests/<id>.json`, the VPS service answers in `results/<id>.json`. Read-only operations only.
EOF
git add -A && git commit -qm "init mailbox" || true
git push -q

python3 -c "import psycopg2" 2>/dev/null || pip3 install -q --break-system-packages psycopg2-binary

cat > /etc/systemd/system/bee-mailbox.service <<'EOF'
[Unit]
Description=Bee Mailbox - read-only fetcher for Claude via GitHub
After=network-online.target
[Service]
ExecStart=/usr/bin/python3 /opt/bee-mailbox/mailbox.py
Environment=MAILBOX_DIR=/opt/bee-mailbox/repo
Restart=always
RestartSec=10
Nice=10
CPUQuota=20%
MemoryMax=512M
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now bee-mailbox
sleep 3
systemctl is-active bee-mailbox && echo "BEE MAILBOX ATTIVA ✅"
