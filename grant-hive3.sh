#!/usr/bin/env bash
# Asks each active key with bash (hidden), then runs grant-hive3.js for that single account.
# Usage: bash grant-hive3.sh
cd "$(dirname "$0")"
for A in hive-170283 aibees ai-bee hive3.guard beecounter scoutbee hivethree hive-3 hive2bee3 hive.bee-3 bz3 pollenpatron ant-thebeekeeper blurtbee; do
  read -rsp "ACTIVE key of @$A (enter = skip): " K; echo
  [ -z "$K" ] && { echo "- $A: skipped"; continue; }
  WIF="$K" timeout 60 node grant-hive3.js --only="$A" || echo "✗ $A: timeout or error"
  unset K
done
