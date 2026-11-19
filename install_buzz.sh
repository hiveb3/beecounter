#!/bin/bash
# Installs the Buzz List: pg module + cron every 15 minutes. Logs in /root/beecounter/buzz.log
cd /root/beecounter
npm i pg --silent
LINE='*/15 * * * * /opt/hive-block-producer/run-with-key.sh /root/beecounter/buzz.js --live >> /root/beecounter/buzz.log 2>&1'
( crontab -l 2>/dev/null | grep -v 'beecounter/buzz.js'; echo "$LINE" ) | crontab -
echo "cron installed:"; crontab -l | grep buzz.js
