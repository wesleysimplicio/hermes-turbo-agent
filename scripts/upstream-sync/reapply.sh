#!/usr/bin/env bash
# reapply.sh - Applies a captured upstream patch series onto a dated sync
# branch, logging conflicts and skipped patches without aborting the run.
# Pair with capture-upstream.sh.
#
# Usage:
#   scripts/upstream-sync/reapply.sh <RUN_ID> [--base BRANCH] [--dry-run]
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
WORK_DIR="${ROOT_DIR}/.upstream-sync"
BASE_BRANCH="$(git -C "$ROOT_DIR" symbolic-ref --short HEAD 2>/dev/null || echo main)"
DRY_RUN=0
RUN_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE_BRANCH="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) RUN_ID="$1"; shift ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  echo "ERROR: missing RUN_ID (look under ${WORK_DIR}/)" >&2
  exit 2
fi

RUN_DIR="${WORK_DIR}/${RUN_ID}"
SERIES="${RUN_DIR}/series.patch"
MANIFEST="${RUN_DIR}/manifest.json"
LOG="${RUN_DIR}/reapply.log"
CONFLICTS="${RUN_DIR}/conflicts.txt"

if [[ ! -f "$SERIES" || ! -f "$MANIFEST" ]]; then
  echo "ERROR: missing series.patch or manifest.json in ${RUN_DIR}" >&2
  exit 1
fi

if ! git -C "$ROOT_DIR" diff --quiet || ! git -C "$ROOT_DIR" diff --cached --quiet; then
  echo "ERROR: dirty working tree; commit or stash first" >&2
  exit 1
fi

SYNC_BRANCH="upstream-sync/${RUN_ID}"
echo "base=${BASE_BRANCH} sync-branch=${SYNC_BRANCH} dry-run=${DRY_RUN}" | tee "$LOG"

if [[ "$DRY_RUN" -eq 1 ]]; then
  git -C "$ROOT_DIR" apply --check "$SERIES" 2>&1 | tee -a "$LOG" || true
  echo "dry-run complete; see $LOG"
  exit 0
fi

git -C "$ROOT_DIR" checkout -B "$SYNC_BRANCH" "$BASE_BRANCH" | tee -a "$LOG"

: > "$CONFLICTS"
if git -C "$ROOT_DIR" am --3way --keep-cr "$SERIES" >>"$LOG" 2>&1; then
  echo "all patches applied cleanly" | tee -a "$LOG"
else
  echo "conflicts detected; recording state" | tee -a "$LOG"
  git -C "$ROOT_DIR" status --porcelain | tee -a "$CONFLICTS" >>"$LOG"
  git -C "$ROOT_DIR" am --abort >>"$LOG" 2>&1 || true
  echo "WARN: conflicts logged at $CONFLICTS; operator must resolve manually" >&2
fi

echo "reapply finished branch=${SYNC_BRANCH} log=${LOG}"
