#!/bin/bash
# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter install (once). Usage: bash setup.sh
set -e
cd /root/beecounter
apt-get install -y python3-psycopg2 python3-matplotlib python3-networkx python3-pil python3-markdown nodejs npm fonts-dejavu-core
npm install --no-audit --no-fund @hiveio/dhive@1
[ -f .env ] || printf 'AUTO_PUBLISH=0\n' > .env
chmod 600 .env; chmod +x *.sh
echo "Done. Now: bash secure.sh  (stores the posting key encrypted and installs the timers)"
