#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# Daily supply snapshot from our own hived node at 00:00:05 UTC. Usage: bash install_snapshot_timer.sh
set -e
cat > /etc/systemd/system/beecounter-snapshot.service <<'UNIT'
[Unit]
Description=BeeCounter supply snapshot from the local hived node
[Service]
Type=oneshot
WorkingDirectory=/root/beecounter
ExecStart=/usr/bin/python3 /root/beecounter/supply_snapshot.py
StandardOutput=append:/root/beecounter/supply.log
StandardError=append:/root/beecounter/supply.log
UNIT
cat > /etc/systemd/system/beecounter-snapshot.timer <<'UNIT'
[Unit]
Description=BeeCounter supply snapshot (every day, 00:00:05 UTC)
[Timer]
OnCalendar=*-*-* 00:00:05 UTC
AccuracySec=1s
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload && systemctl enable --now beecounter-snapshot.timer
python3 /root/beecounter/supply_snapshot.py && echo "Test OK: snapshot saved in /root/beecounter/supply/"
systemctl list-timers 'beecounter-*' --no-pager
