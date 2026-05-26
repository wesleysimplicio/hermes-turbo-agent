#!/usr/bin/env bash
# sync-upstream.sh — Incorporates updates from NousResearch/hermes-agent
# without overwriting customizations in hermes-agent-100x-fast.
#
# Protected files are listed in .gitattributes with `merge=ours`. The
# `merge.ours.driver=true` git config (set by this script if missing)
# makes those entries effective.
#
# Usage:
#   ./scripts/sync-upstream.sh              # rebase onto upstream/main
#   ./scripts/sync-upstream.sh --no-rebase  # fetch only, print delta
set -euo pipefail

UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
OUR_BRANCH="codex/hermes-agent-100x-fast"
SNAPSHOT_TAG="pre-sync-$(date +%Y%m%d-%H%M%S)"
NO_REBASE=0

for arg in "$@"; do
  case "$arg" in
    --no-rebase) NO_REBASE=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

echo "=== Hermes2 Upstream Sync ==="
echo "Upstream: NousResearch/hermes-agent @ $UPSTREAM_BRANCH"
echo "Ours:     wesleysimplicio/hermes-agent-100x-fast @ $OUR_BRANCH"
echo ""

git config merge.ours.driver true

git checkout "$OUR_BRANCH"
if ! git diff --quiet; then
  echo "ERROR: Dirty working tree. Commit or stash changes first."
  exit 1
fi

git tag "$SNAPSHOT_TAG"
echo "Snapshot tag: $SNAPSHOT_TAG"

echo "Fetching upstream..."
git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH"

UPSTREAM_COMMITS=$(git rev-list --count "HEAD..upstream/$UPSTREAM_BRANCH" || echo 0)
echo "Upstream commits ahead: $UPSTREAM_COMMITS"
git log "HEAD..upstream/$UPSTREAM_BRANCH" --oneline | head -20 || true

if [[ "$NO_REBASE" == "1" ]]; then
  echo ""
  echo "--no-rebase: stopping after fetch. Rollback with: git tag -d $SNAPSHOT_TAG"
  exit 0
fi

echo "Rebasing onto upstream/$UPSTREAM_BRANCH ..."
git rebase "upstream/$UPSTREAM_BRANCH"

echo ""
echo "=== Post-sync checklist ==="
echo "[ ] venv/bin/python -m pytest tests/ -x -q   (if tests exist)"
echo "[ ] hermes2 --version"
echo "[ ] hermes2 status"
echo "[ ] launchctl kickstart -k gui/\$(id -u)/ai.hermes2.gateway"
echo "[ ] tail -20 ~/.hermes2/logs/gateway.log"
echo "[ ] git push origin $OUR_BRANCH --force-with-lease"
echo ""
echo "Sync complete. Snapshot tag: $SNAPSHOT_TAG"
echo "Rollback: git reset --hard $SNAPSHOT_TAG"
