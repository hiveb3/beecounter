#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# ntfy notification with an HTML preview of the draft.  Usage: ./notify.sh OUTDIR [daily]   or   ./notify.sh --error "text"
cd /root/beecounter
set -a; . ./.env; set +a
[ -z "$NTFY_TOPIC" ] && exit 0
URL="https://ntfy.sh/$NTFY_TOPIC"
if [ "$1" = "--error" ]; then
  curl -s -H "Title: BeeCounter: ERROR" -H "Priority: high" -H "Tags: warning" -d "$2 (see beecounter.log)" "$URL" >/dev/null
  exit 0
fi
OUT="$1"; KIND="$2"
python3 - "$OUT" <<'PY'
import sys, json, markdown
out = sys.argv[1]
md = open(f"{out}/final.md", encoding="utf-8").read()
md = "\n".join(l for l in md.splitlines() if l.strip() not in ("<center>", "</center>"))
html = markdown.markdown(md, extensions=["tables"])
css = ("body{font-family:sans-serif;max-width:760px;margin:auto;padding:12px;line-height:1.5;background:#fff8e7;color:#3b2a1a}"
       "img{max-width:100%;height:auto;display:block;margin:12px auto}table{border-collapse:collapse;font-size:13px;display:block;overflow-x:auto}"
       "td,th{border:1px solid #e8c77a;padding:4px 6px}a{color:#b5651d}h1{font-size:22px}")
open(f"{out}/preview.html", "w", encoding="utf-8").write(
    f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    f"<title>BeeCounter draft</title><style>{css}</style></head><body>{html}</body></html>")
PY
CMD="./approve.sh $OUT${KIND:+ $KIND}"
curl -s -H "Title: BeeCounter: draft ready" -H "Tags: bee" -H "Filename: preview.html" \
     -H "Message: Open the attachment to read it. To publish: $CMD" -T "$OUT/preview.html" "$URL" >/dev/null
echo "Notification sent"
