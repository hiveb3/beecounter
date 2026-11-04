#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter daily: posts created 8 days ago = paid out yesterday. Timer: 01:30 UTC
set -e
cd /root/beecounter
set -a; . ./.env; set +a
. ./lib.sh
trap './notify.sh --error "daily failed"' ERR
DAY=${1:-$(date -u -d '8 days ago' +%F)}
N=$(( $(cat counter.daily 2>/dev/null || echo 0) + 1 ))
OUT=out/daily-$DAY; mkdir -p "$OUT"
echo "== $(date -u) daily $DAY #$N"
python3 collect.py "$DAY" "$DAY" && mv "data_${DAY}_${DAY}.json" "$OUT/data.json"
python3 render.py "$OUT/data.json" "$OUT" "$DAY" "$DAY" "$N"
if [ "$AUTO_PUBLISH" = "1" ]; then
  pub "$OUT" --publish && echo "$N" > counter.daily
else
  pub "$OUT"
  ./notify.sh "$OUT" daily
  echo "DRAFT: check $OUT/final.md, then run:  ./approve.sh $OUT daily"
fi
