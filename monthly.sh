#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter Monthly Ledger: everything paid in the previous month (flows + content). Timer: 2nd of month, 04:00 UTC
# By hand: ./monthly.sh 2026-10
set -e
cd /root/beecounter
set -a; . ./.env; set +a
. ./lib.sh
trap './notify.sh --error "monthly ledger failed"' ERR
M=${1:-$(date -u -d "$(date -u +%Y-%m-01) -1 day" +%Y-%m)}
FROM=$(date -u -d "$M-01 -7 days" +%F)                                   # posts paid in the month = created 7 days earlier
TO=$(date -u -d "$(date -u -d "$M-01 +1 month" +%F) -8 days" +%F)
OUT=out/ledger-$M; mkdir -p "$OUT/content" "$OUT/flow"
echo "== $(date -u) monthly ledger $M (posts created $FROM .. $TO)"
python3 inflation.py "$M" > "$OUT/flow/inflation.log" && mv "inflation_$M.json" "$OUT/flow/data.json"
python3 collect.py "$FROM" "$TO" > "$OUT/content/collect.log" && mv "data_${FROM}_${TO}.json" "$OUT/content/data.json"
python3 render.py "$OUT/content/data.json" "$OUT/content" "$FROM" "$TO"
python3 render_inflation.py "$OUT/flow/data.json" "$OUT/flow"
python3 dhf_watch.py "$M" > "$OUT/flow/dhf.log" && mkdir -p "$OUT/dhf" && mv "dhf_$M.json" "$OUT/dhf/data.json"
PRICE=$(python3 -c "import json;d=json.load(open('$OUT/flow/data.json'));c=d['convert_hbd_to_hive'][0];print(c[1]/c[2] if c[2] else 0)")
python3 render_dhf.py "$OUT/dhf/data.json" "$OUT/dhf" "$PRICE"
python3 compose_ledger.py "$OUT"
if [ "$AUTO_PUBLISH" = "1" ]; then pub "$OUT" --publish
else pub "$OUT"; ./notify.sh "$OUT"; echo "DRAFT: check $OUT/final.md, then run:  ./approve.sh $OUT"; fi
