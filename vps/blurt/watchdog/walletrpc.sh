#!/bin/bash
# Helpers to drive the Blurt cli_wallet (inside the blurtd container) through its HTTP JSON-RPC daemon mode.
# Source this file:  . /opt/blurt-watchdog/walletrpc.sh
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
WR_C=${WR_C:-blurtd}
WR_WS=${WR_WS:-ws://127.0.0.1:8190}
WR_WALLET=${WR_WALLET:-/blurtd/watchdog-wallet.json}
WR_PORT=${WR_PORT:-8197}

wr_stop() {
  docker top "$WR_C" -eo pid,args 2>/dev/null | awk -v p="$WR_PORT" '$0 ~ "cli_wallet" && $0 ~ p {print $1}' | xargs -r kill 2>/dev/null || true
}

wr_start() {
  wr_stop
  docker exec -d "$WR_C" cli_wallet -s "$WR_WS" -w "$WR_WALLET" -d \
    --rpc-http-endpoint "127.0.0.1:$WR_PORT" --rpc-http-allowip 127.0.0.1
  for _ in $(seq 1 30); do
    curl -s -m 2 -o /dev/null "http://127.0.0.1:$WR_PORT" -d '{"jsonrpc":"2.0","id":0,"method":"is_new","params":[]}' && return 0
    sleep 0.5
  done
  echo "cli_wallet daemon did not start" >&2; return 1
}

# wr_call <method> <json-params-array>
wr_call() {
  curl -s -m 60 "http://127.0.0.1:$WR_PORT" -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$1\",\"params\":$2}"
}
