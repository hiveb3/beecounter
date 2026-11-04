#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# Single monthly report (Monthly Ledger) on the 2nd at 04:00 UTC; removes the old separate timer.
set -e
sed -i 's/^OnCalendar=.*/OnCalendar=*-*-02 04:00:00 UTC/; s/^Description=.*/Description=BeeCounter monthly ledger (2nd of month, 04:00 UTC)/' /etc/systemd/system/beecounter-monthly.timer
systemctl disable --now beecounter-inflation.timer 2>/dev/null || true
rm -f /etc/systemd/system/beecounter-inflation.timer /etc/systemd/system/beecounter-inflation.service
systemctl daemon-reload && systemctl restart beecounter-monthly.timer
systemctl list-timers 'beecounter-*' --no-pager
