#!/usr/bin/env bash
# Refresh benchmark suite after upstream sync.
# Writes machine-readable results to ${BENCHMARK_RESULTS_DIR}/<UTC date>.json.
# Marks the run as "stale" if the underlying benchmark script fails.
set -euo pipefail

RESULTS_DIR="${BENCHMARK_RESULTS_DIR:-benchmarks/results}"
DATE_UTC="$(date -u +%F)"
COMMIT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
REF_NAME="${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)}"
OUT_FILE="${RESULTS_DIR}/${DATE_UTC}.json"

mkdir -p "${RESULTS_DIR}"

STATUS="ok"
RAW_OUTPUT=""
if command -v python >/dev/null 2>&1 && [ -f scripts/refresh_sync_benchmarks.py ]; then
  if RAW_OUTPUT="$(python scripts/refresh_sync_benchmarks.py --python python 2>&1)"; then
    STATUS="ok"
  else
    STATUS="stale"
  fi
else
  STATUS="stale"
  RAW_OUTPUT="benchmark runner unavailable: missing python or scripts/refresh_sync_benchmarks.py"
fi

ESCAPED_OUTPUT="$(printf '%s' "${RAW_OUTPUT}" | python -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""')"

cat >"${OUT_FILE}" <<EOF
{
  "date": "${DATE_UTC}",
  "commit": "${COMMIT_SHA}",
  "ref": "${REF_NAME}",
  "status": "${STATUS}",
  "runner": "scripts/benchmarks/refresh.sh",
  "log": ${ESCAPED_OUTPUT}
}
EOF

echo "Wrote ${OUT_FILE} (status=${STATUS})"
if [ "${STATUS}" = "stale" ]; then
  echo "::warning::Benchmark refresh marked stale; see ${OUT_FILE}"
fi
