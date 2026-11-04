# Open source (MIT) · AI-generated with Claude (Anthropic), reviewed by a human · https://github.com/hiveb3/beecounter
# BeeCounter: loads the encrypted posting key (systemd-creds). Sourced by the scripts.
# pub: runs publish.js and judges success from its output (Ubuntu's Node 18 may crash on exit)
pub() {
  local log; log=$(node publish.js "$@" 2>&1 || true); echo "$log"
  if [[ " $* " == *" --publish "* ]]; then grep -q "PUBLISHED:\|Already published" <<<"$log"; else grep -q "Draft ready" <<<"$log"; fi
}
CRED=/etc/credstore.encrypted/beecounter-posting-key.cred
if [ -z "$BEECOUNTER_POSTING_KEY" ]; then
  if [ -n "$CREDENTIALS_DIRECTORY" ] && [ -f "$CREDENTIALS_DIRECTORY/beecounter-posting-key" ]; then
    export BEECOUNTER_POSTING_KEY="$(cat "$CREDENTIALS_DIRECTORY/beecounter-posting-key")"
  elif [ -f "$CRED" ]; then
    # run by hand: re-run inside systemd, which decrypts the key in memory only
    exec systemd-run --quiet --wait --pipe --collect -p WorkingDirectory=/root/beecounter \
      -p LoadCredentialEncrypted=beecounter-posting-key:$CRED "$(readlink -f "$0")" "$@"
  fi
fi
