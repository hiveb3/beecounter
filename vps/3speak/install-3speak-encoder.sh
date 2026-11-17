#!/bin/bash
# 3Speak Encoder on the hive3 VPS - load check + install with hard CPU/RAM limits.
# Run as root:  bash install-3speak-encoder.sh          (check + install if compatible)
#               bash install-3speak-encoder.sh --check  (only the load check)
# Reports are written to /root/beecounter/3speak_*.txt (readable via bee-mailbox "report").
# AI-generated with Claude (Anthropic), reviewed by a human. MIT.
set -euo pipefail
DIR=/opt/3speakencoder
REP=/root/beecounter; mkdir -p "$REP"
PRE="$REP/3speak_precheck.txt"
HIVE_USER="${HIVE_USER:-hive3}"

# ---------- 1. LOAD CHECK ----------
NCPU=$(nproc)
LOAD1=$(cut -d' ' -f1 /proc/loadavg); LOAD15=$(cut -d' ' -f3 /proc/loadavg)
MEM_AVAIL_MB=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
MEM_TOTAL_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
DOCKER_ROOT=$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)
DISK_FREE_GB=$(df -BG --output=avail "$DOCKER_ROOT" | tail -1 | tr -dc 0-9)

# encoder gets 25% of cores (min 1, max 4), pinned to the LAST cores; IPFS 0.5 cpu
ENC_CPUS=$(( NCPU / 4 )); [ "$ENC_CPUS" -lt 1 ] && ENC_CPUS=1; [ "$ENC_CPUS" -gt 4 ] && ENC_CPUS=4
CPUSET="$(( NCPU - ENC_CPUS ))-$(( NCPU - 1 ))"
ENC_MEM=3g; [ "$MEM_AVAIL_MB" -lt 6000 ] && ENC_MEM=2g
IPFS_MEM=1g

{
  echo "=== 3Speak encoder precheck $(date -Is) ==="
  echo "CPU cores: $NCPU | load 1m: $LOAD1 | load 15m: $LOAD15"
  echo "RAM total: ${MEM_TOTAL_MB} MB | available: ${MEM_AVAIL_MB} MB"
  echo "Disk free ($DOCKER_ROOT): ${DISK_FREE_GB} GB"
  echo; echo "--- docker stats ---"; docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null || echo "docker non disponibile"
  echo; echo "--- top processes (CPU) ---"; ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -12
  echo; echo "--- ports 3001/3002/4001/5001 in use? ---"; ss -ltnup 2>/dev/null | grep -E ':(3001|3002|4001|5001)\b' || echo "liberi"
  echo; echo "Proposed limits: encoder ${ENC_CPUS} cpu (cpuset $CPUSET, low priority), RAM $ENC_MEM | IPFS 0.5 cpu, RAM $IPFS_MEM"
} | tee "$PRE"

FAIL=""
awk -v l="$LOAD15" -v n="$NCPU" 'BEGIN{exit !(l > n*0.6)}' && FAIL+="- load 15m ($LOAD15) oltre il 60% dei core ($NCPU)\n"
[ "$MEM_AVAIL_MB" -lt 4000 ] && FAIL+="- RAM disponibile ${MEM_AVAIL_MB} MB < 4000 MB\n"
[ "$DISK_FREE_GB" -lt 30 ] && FAIL+="- disco libero ${DISK_FREE_GB} GB < 30 GB\n"
[ "$NCPU" -lt 4 ] && FAIL+="- solo $NCPU core: troppo pochi accanto ai witness\n"
ss -ltn 2>/dev/null | grep -qE ':(3001|4001)\b' && [ ! -d "$DIR" ] && FAIL+="- porta 3001 o 4001 gia' occupata\n"
command -v docker >/dev/null || FAIL+="- docker non installato\n"

if [ -n "$FAIL" ]; then
  printf "\nRESULT: NOT COMPATIBLE\n$FAIL" | tee -a "$PRE"; exit 1
fi
echo -e "\nRESULT: COMPATIBLE" | tee -a "$PRE"
[ "${1:-}" = "--check" ] && exit 0

# ---------- 2. INSTALL ----------
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q https://github.com/Mantequilla-Soft/3speakencoder.git "$DIR"; fi
cd "$DIR"

if [ ! -f .env ]; then
  cat > .env <<EOF
HIVE_USERNAME=$HIVE_USER
ENCODER_PRIVATE_KEY=$(openssl rand -base64 32)
NODE_NAME=${HIVE_USER}-encoder
EMBED_SYSTEM_ENABLED=true
EMBED_SYSTEM_MODE=community
EMBED_GATEWAY_URL=https://embed.3speak.tv
DIRECT_API_ENABLED=false
MAX_CONCURRENT_JOBS=1
HARDWARE_ACCELERATION=false
ARIA2_CONNECTIONS=6
ENABLE_LOCAL_FALLBACK=false
DASHBOARD_PASSWORD=$(openssl rand -hex 12)
EOF
  chmod 600 .env
fi

# own compose file: dashboard only on localhost, no Direct API port, hard limits, witnesses win on CPU/RAM
cat > docker-compose.hive3.yml <<EOF
services:
  encoder:
    image: ghcr.io/mantequilla-soft/3speakencoder:latest
    build: { context: ., dockerfile: Dockerfile.production }
    container_name: 3speak-encoder
    restart: unless-stopped
    depends_on: [ipfs]
    env_file: [.env]
    environment:
      - IPFS_API_ADDR=/dns4/ipfs/tcp/5001
      - DASHBOARD_HOST=0.0.0.0
      - DASHBOARD_PORT=3001
      - TEMP_DIR=/app/work
    ports: ["127.0.0.1:3001:3001"]
    volumes: [encoder_data:/app/data, encoder_work:/app/work]
    cpus: ${ENC_CPUS}
    cpuset: "${CPUSET}"
    cpu_shares: 128
    mem_limit: ${ENC_MEM}
    memswap_limit: ${ENC_MEM}
    oom_score_adj: 800
    pids_limit: 512
    logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }
  ipfs:
    image: ipfs/kubo:v0.43.1
    container_name: 3speak-ipfs
    restart: unless-stopped
    environment: [IPFS_PROFILE=server, GOMEMLIMIT=800MiB]
    ports: ["4001:4001", "4001:4001/udp"]
    volumes: [ipfs_data:/data/ipfs]
    cpus: 0.5
    cpu_shares: 128
    mem_limit: ${IPFS_MEM}
    memswap_limit: ${IPFS_MEM}
    oom_score_adj: 800
    logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }
volumes: { encoder_data: {}, encoder_work: {}, ipfs_data: {} }
networks: { default: { name: 3speak-network } }
EOF

docker compose -f docker-compose.hive3.yml pull -q encoder 2>/dev/null \
  || GIT_COMMIT=$(git rev-parse HEAD) nice -n 19 docker compose -f docker-compose.hive3.yml build encoder
docker compose -f docker-compose.hive3.yml up -d

# keep IPFS light: few connections
sleep 15
docker exec 3speak-ipfs ipfs config --json Swarm.ConnMgr.LowWater 50 >/dev/null 2>&1 || true
docker exec 3speak-ipfs ipfs config --json Swarm.ConnMgr.HighWater 150 >/dev/null 2>&1 || true
docker restart 3speak-ipfs >/dev/null

# stats every 10 min -> /root/beecounter/3speak_stats.txt (last 500 lines)
cat > /usr/local/bin/3speak-stats.sh <<'EOF'
#!/bin/bash
F=/root/beecounter/3speak_stats.txt
{ echo "$(date -Is) load=$(cut -d' ' -f1-3 /proc/loadavg)"; docker stats --no-stream --format '  {{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}}'; } >> "$F"
tail -n 500 "$F" > "$F.tmp" && mv "$F.tmp" "$F"
EOF
chmod +x /usr/local/bin/3speak-stats.sh
echo "*/10 * * * * root /usr/local/bin/3speak-stats.sh" > /etc/cron.d/3speak-stats

sleep 30
{
  echo "=== 3Speak encoder status $(date -Is) ==="
  docker ps --filter name=3speak --format '{{.Names}}  {{.Status}}'
  echo; docker logs --tail 40 3speak-encoder 2>&1 | sed -E 's/(ENCODER_PRIVATE_KEY=)[^ ]+/\1***/'
} > "$REP/3speak_status.txt"
cat "$REP/3speak_status.txt"
echo
echo "3SPEAK ENCODER INSTALLATO ✅  (dashboard: ssh -L 3001:127.0.0.1:3001 root@169.58.182.112 -> http://localhost:3001)"
echo "Password dashboard: $(grep DASHBOARD_PASSWORD .env | cut -d= -f2)"
echo "Per fermarlo: cd $DIR && docker compose -f docker-compose.hive3.yml down"
