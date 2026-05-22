#!/usr/bin/env bash
# check-rtk.sh — detect optional RTK CLI (https://github.com/rtk-ai/rtk).
#
# Exits 0 with the resolved binary path when `rtk` is on PATH.
# Exits 1 with an install hint otherwise. Never blocks the repo: RTK is
# optional, every command in this repo has a plain fallback.
#
# See: docs/dev/rtk-cli.md
set -euo pipefail

if bin="$(command -v rtk 2>/dev/null)"; then
  echo "rtk: ok ($bin)"
  rtk --version 2>/dev/null || true
  exit 0
fi

cat >&2 <<'HINT'
rtk: not found on PATH (optional)

Install: https://github.com/rtk-ai/rtk
Guide:   docs/dev/rtk-cli.md

This repo works without rtk. The check exits non-zero only to signal absence
to callers that want to gate on it.
HINT
exit 1
