#!/bin/bash
# Edits the five opt-in snaps of the swarm with their multilingual texts (snaps/*.md in this repo).
cd /root/beecounter && mkdir -p snaps
B=https://raw.githubusercontent.com/hiveb3/beecounter/main
curl -fsSLO $B/edit-comment.js
for pair in hive3:re-peaksnaps-torjbj ant-thebeekeeper:re-peaksnaps-tormgt blurtbee:re-peaksnaps-tormjk beecounter:re-peaksnaps-tormkh scoutbee:re-peaksnaps-tormm5; do
  A=${pair%%:*}; P=${pair#*:}
  curl -fsSL -o snaps/$A-optin.md $B/snaps/$A-optin.md && \
  /opt/hive-block-producer/run-with-key.sh /root/beecounter/edit-comment.js $A $P snaps/$A-optin.md 2>/dev/null | grep -v '^$'
  sleep 4
done
