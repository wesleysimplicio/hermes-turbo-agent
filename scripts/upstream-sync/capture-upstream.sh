#!/usr/bin/env bash
# capture-upstream.sh - Clones/fetches upstream Hermes and emits the list of
# new commits and a patch series since the last sync tag recorded in
# scripts/upstream-sync/sync-state.json.
#
# Output:
#   .upstream-sync/<RUN_ID>/commits.txt   one-line commit summary
#   .upstream-sync/<RUN_ID>/series.patch  combined patch series
#   .upstream-sync/<RUN_ID>/manifest.json metadata for reapply.sh
#
# Usage:
#   scripts/upstream-sync/capture-upstream.sh [--upstream-url URL] [--branch BR]
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
STATE_FILE="${ROOT_DIR}/scripts/upstream-sync/sync-state.json"
WORK_DIR="${ROOT_DIR}/.upstream-sync"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="${WORK_DIR}/${RUN_ID}"

UPSTREAM_URL="https://github.com/NousResearch/hermes-agent.git"
UPSTREAM_BRANCH="main"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream-url) UPSTREAM_URL="$2"; shift 2 ;;
    --branch) UPSTREAM_BRANCH="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$STATE_FILE" ]]; then
  echo "ERROR: missing $STATE_FILE" >&2
  exit 1
fi

LAST_SYNC_SHA="$(python3 -c "import json,sys;print(json.load(open('${STATE_FILE}')).get('last_sync_sha',''))")"
if [[ -z "$LAST_SYNC_SHA" ]]; then
  echo "WARN: last_sync_sha empty in sync-state.json; capturing last 50 commits" >&2
fi

mkdir -p "$RUN_DIR"
MIRROR_DIR="${WORK_DIR}/upstream.git"

if [[ -d "$MIRROR_DIR" ]]; then
  git -C "$MIRROR_DIR" remote set-url origin "$UPSTREAM_URL"
  git -C "$MIRROR_DIR" fetch --prune origin "${UPSTREAM_BRANCH}:${UPSTREAM_BRANCH}"
else
  git clone --bare --single-branch --branch "$UPSTREAM_BRANCH" "$UPSTREAM_URL" "$MIRROR_DIR"
fi

HEAD_SHA="$(git -C "$MIRROR_DIR" rev-parse "$UPSTREAM_BRANCH")"
if [[ -n "$LAST_SYNC_SHA" ]] && git -C "$MIRROR_DIR" cat-file -e "${LAST_SYNC_SHA}^{commit}" 2>/dev/null; then
  RANGE="${LAST_SYNC_SHA}..${HEAD_SHA}"
else
  RANGE="${HEAD_SHA}~50..${HEAD_SHA}"
fi

git -C "$MIRROR_DIR" log --oneline "$RANGE" > "${RUN_DIR}/commits.txt"
git -C "$MIRROR_DIR" format-patch --stdout "$RANGE" > "${RUN_DIR}/series.patch" || true

COMMIT_COUNT="$(wc -l < "${RUN_DIR}/commits.txt" | tr -d ' ')"

cat > "${RUN_DIR}/manifest.json" <<EOF
{
  "run_id": "${RUN_ID}",
  "upstream_url": "${UPSTREAM_URL}",
  "upstream_branch": "${UPSTREAM_BRANCH}",
  "previous_sha": "${LAST_SYNC_SHA}",
  "head_sha": "${HEAD_SHA}",
  "commit_count": ${COMMIT_COUNT},
  "captured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "captured ${COMMIT_COUNT} commits into ${RUN_DIR}"
echo "manifest: ${RUN_DIR}/manifest.json"
