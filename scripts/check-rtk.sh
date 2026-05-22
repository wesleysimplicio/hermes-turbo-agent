#!/usr/bin/env bash
# check-rtk.sh — show which token-saver backend the Hermes Turbo RTK bridge
# will use. See docs/integrations/rtk-bridge.md.
#
# Exit: 0 rtk active, 1 native fallback, 2 backend=rtk but rtk missing.
set -euo pipefail

BACKEND="${HERMES_TOKEN_SAVER:-auto}"

if command -v rtk >/dev/null 2>&1; then
  RTK_PATH="$(command -v rtk)"
  RTK_AVAILABLE=1
else
  RTK_PATH=""
  RTK_AVAILABLE=0
fi

case "$BACKEND" in
  native) EFFECTIVE="native" ;;
  rtk)
    if [ "$RTK_AVAILABLE" -eq 1 ]; then
      EFFECTIVE="rtk"
    else
      echo "ERROR: HERMES_TOKEN_SAVER=rtk but \`rtk\` is not on PATH." >&2
      echo "Install https://github.com/rtk-ai/rtk or switch to native/auto." >&2
      exit 2
    fi
    ;;
  auto|*)
    BACKEND="auto"
    [ "$RTK_AVAILABLE" -eq 1 ] && EFFECTIVE="rtk" || EFFECTIVE="native"
    ;;
esac

printf 'backend=%s\nrtk_available=%s\nrtk_path=%s\neffective=%s\n' \
  "$BACKEND" "$RTK_AVAILABLE" "$RTK_PATH" "$EFFECTIVE"

[ "$EFFECTIVE" = "rtk" ] && exit 0 || exit 1
