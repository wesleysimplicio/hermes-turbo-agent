#!/usr/bin/env python3
"""Run a small stable benchmark subset and compare results against perf budgets.

Issue #79: non-blocking CI regression warnings.

The budgets file lives at ``scripts/perf_budgets.json`` and documents which
cases we track, the unit (seconds, median across samples), and generous
warning thresholds.  Exit code is **always 0**: this script is informational
only, it never blocks CI.  Warnings are emitted to stdout and a structured
JSON artifact is written for downstream upload.

Usage
-----

    python scripts/perf_budgets.py \\
        --samples 3 \\
        --output perf-budgets-report.json \\
        --summary perf-budgets-summary.md

Outputs
-------

* ``--output`` (JSON) — machine-readable report: per-case median + budget +
  status (``ok`` / ``over_budget`` / ``error``).
* ``--summary`` (Markdown) — short human summary; same data, table form.

How budgets map to runners
--------------------------

* ``import_model_tools``, ``get_tool_definitions``, ``session_append_messages_batch``
  are produced by ``scripts/benchmark_startup_perf.py``.
* ``parallel_guard_read_files``, ``openrouter_metadata_disk_cache`` are
  produced by ``scripts/benchmark_runtime_usage.py``.

The benchmark runners emit ``--json`` keyed by case name with a ``median``
field per case.  We honour that contract; if a case is missing we mark it
``error`` and continue.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BUDGETS_FILE = Path(__file__).resolve().parent / "perf_budgets.json"


# Which runner script produces which cases.
_STARTUP_CASES = {
    "import_model_tools",
    "get_tool_definitions",
    "session_append_messages_batch",
}
_RUNTIME_CASES = {
    "parallel_guard_read_files",
    "openrouter_metadata_disk_cache",
}


def _load_budgets() -> dict:
    with BUDGETS_FILE.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _run_benchmark(script: str, cases: list[str], samples: int) -> dict:
    """Invoke a benchmark runner in ``--json`` mode for the given cases."""
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / script), "--json", "-n", str(samples)]
    for case in cases:
        cmd += ["--case", case]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "_ok": False,
            "_stderr": proc.stderr.strip()[-4000:],
            "_stdout": proc.stdout.strip()[-2000:],
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"_ok": False, "_error": str(exc), "_stdout": proc.stdout.strip()[-2000:]}


def _evaluate(case: str, budget: float, runner_output: dict) -> dict:
    """Compare a runner result against the budget. Status: ok / over_budget / error."""
    entry = runner_output.get(case) if isinstance(runner_output, dict) else None
    if not entry or not entry.get("ok"):
        return {
            "case": case,
            "status": "error",
            "budget_seconds": budget,
            "median_seconds": None,
            "reason": "benchmark did not produce a result",
        }
    median = entry.get("median")
    if median is None:
        return {
            "case": case,
            "status": "error",
            "budget_seconds": budget,
            "median_seconds": None,
            "reason": "benchmark output missing median field",
        }
    over = median > budget
    return {
        "case": case,
        "status": "over_budget" if over else "ok",
        "budget_seconds": budget,
        "median_seconds": median,
        "ratio": (median / budget) if budget else None,
    }


def _write_summary(report: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append("# Hermes performance budgets — regression report")
    lines.append("")
    lines.append(f"Samples per case: {report['samples']}")
    lines.append("")
    lines.append("| case | median (s) | budget (s) | ratio | status |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for row in report["cases"]:
        median = row.get("median_seconds")
        ratio = row.get("ratio")
        median_str = f"{median:.4f}" if isinstance(median, (int, float)) else "n/a"
        ratio_str = f"{ratio:.2f}x" if isinstance(ratio, (int, float)) else "n/a"
        lines.append(
            f"| {row['case']} | {median_str} | {row['budget_seconds']:.4f} | "
            f"{ratio_str} | {row['status']} |"
        )
    if report["warnings"]:
        lines.append("")
        lines.append("## Warnings")
        for w in report["warnings"]:
            lines.append(f"- {w}")
    lines.append("")
    lines.append("> Budgets are non-blocking regression alarms, not targets.")
    lines.append("> See `docs/adr/0004-perf-budgets.md` to update.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--samples", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("perf-budgets-report.json"))
    parser.add_argument("--summary", type=Path, default=Path("perf-budgets-summary.md"))
    parser.add_argument(
        "--skip-runtime",
        action="store_true",
        help="Skip the runtime benchmark runner (useful when only startup paths changed).",
    )
    parser.add_argument(
        "--skip-startup",
        action="store_true",
        help="Skip the startup benchmark runner.",
    )
    args = parser.parse_args()

    budgets = _load_budgets()
    case_budgets: dict[str, float] = {
        name: float(meta["budget"]) for name, meta in budgets["cases"].items()
    }

    startup_cases = [c for c in _STARTUP_CASES if c in case_budgets]
    runtime_cases = [c for c in _RUNTIME_CASES if c in case_budgets]

    runner_output: dict = {}
    if startup_cases and not args.skip_startup:
        out = _run_benchmark("benchmark_startup_perf.py", startup_cases, args.samples)
        runner_output.update(out if isinstance(out, dict) else {})
    if runtime_cases and not args.skip_runtime:
        out = _run_benchmark("benchmark_runtime_usage.py", runtime_cases, args.samples)
        runner_output.update(out if isinstance(out, dict) else {})

    rows = [_evaluate(case, budget, runner_output) for case, budget in case_budgets.items()]
    warnings: list[str] = []
    for row in rows:
        if row["status"] == "over_budget":
            warnings.append(
                f"{row['case']}: median {row['median_seconds']:.4f}s > "
                f"budget {row['budget_seconds']:.4f}s "
                f"({row['ratio']:.2f}x)"
            )
        elif row["status"] == "error":
            warnings.append(f"{row['case']}: {row.get('reason', 'unknown error')}")

    report = {
        "schema_version": budgets.get("_schema_version", 1),
        "samples": args.samples,
        "cases": rows,
        "warnings": warnings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    _write_summary(report, args.summary)

    # Emit a compact line for CI logs.
    print(json.dumps({"warnings": warnings, "cases": len(rows)}))
    # Always exit 0 — non-blocking by design (see ADR-0004).
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
