#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# Publish a draft you have checked.  Usage: ./approve.sh out/daily-2026-10-27 daily
set -e
cd /root/beecounter
set -a; . ./.env; set +a
. ./lib.sh
pub "$1" --publish
if [ "$2" = "daily" ]; then echo $(( $(cat counter.daily 2>/dev/null || echo 0) + 1 )) > counter.daily; fi
