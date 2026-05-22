#!/usr/bin/env bash
# Opt-in live smoke against DeepSeek's prompt-cache endpoint.
#
# Sends the same stable system prefix twice in quick succession and
# asserts the second call reports a cache hit (DeepSeek surfaces
# `prompt_cache_hit_tokens` in the usage payload).
#
# Usage:
#   HERMES_LIVE=1 DEEPSEEK_API_KEY=sk-... ./live_check.sh
#
# Refs #96.

set -euo pipefail

if [[ "${HERMES_LIVE:-0}" != "1" ]]; then
  echo "[live_check] skipped (set HERMES_LIVE=1 to run)"
  exit 0
fi

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[live_check] DEEPSEEK_API_KEY missing — cannot run live check" >&2
  exit 2
fi

ENDPOINT="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}/chat/completions"
MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

PAYLOAD=$(cat <<JSON
{
  "model": "${MODEL}",
  "max_tokens": 32,
  "messages": [
    {"role": "system", "content": "You are Hermes. Identity stable across turns. Tools available: read_file, write_file, run_terminal. Respond with a single word."},
    {"role": "user", "content": "ping"}
  ]
}
JSON
)

call() {
  curl -sS \
    -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "$ENDPOINT"
}

echo "[live_check] warm-up call..."
RESP1=$(call)
echo "$RESP1" | python3 -c "import json,sys; d=json.load(sys.stdin); print('usage:', d.get('usage'))"

echo "[live_check] repeat call (expect prompt_cache_hit_tokens > 0)..."
RESP2=$(call)
HIT=$(echo "$RESP2" | python3 -c "import json,sys; d=json.load(sys.stdin); print((d.get('usage') or {}).get('prompt_cache_hit_tokens', 0))")
echo "[live_check] prompt_cache_hit_tokens=$HIT"

if [[ "$HIT" -gt 0 ]]; then
  echo "[live_check] OK — provider reported cache hit"
  exit 0
fi

echo "[live_check] WARN — no cache hit reported; check provider, TTL, or prompt drift" >&2
exit 1
