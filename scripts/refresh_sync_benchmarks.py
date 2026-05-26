#!/usr/bin/env python3
"""Refresh benchmark artifacts after an upstream sync."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(cmd, cwd=cwd, env=merged_env, check=True, text=True)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_value(metric: dict[str, Any], key: str) -> float | None:
    value = metric.get(key)
    return None if value is None else float(value)


def build_delta_lines(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if not previous:
        return ["- First measured refresh in this checkout; no prior benchmark JSON was available for delta comparison."]
    lines: list[str] = []
    old_metrics = previous.get("metrics", {})
    new_metrics = current.get("metrics", {})
    for key in sorted(new_metrics):
        current_metric = new_metrics[key]
        previous_metric = old_metrics.get(key)
        if not previous_metric:
            lines.append(f"- `{key}` added in this refresh.")
            continue
        old_local = _metric_value(previous_metric, "local")
        new_local = _metric_value(current_metric, "local")
        if old_local is None or new_local is None:
            continue
        diff = new_local - old_local
        unit = current_metric.get("unit", "")
        if abs(diff) < 1e-9:
            lines.append(f"- `{key}` unchanged at `{new_local:.3f} {unit}`.")
            continue
        direction = "improved" if current_metric.get("lower_is_better", True) == (diff < 0) else "regressed"
        lines.append(
            f"- `{key}` {direction}: `{old_local:.3f} -> {new_local:.3f} {unit}` "
            f"({diff:+.3f} {unit})."
        )
    return lines or ["- Benchmark refresh completed, but there were no comparable measured rows for delta output."]


def build_pr_body_section(status: dict[str, Any]) -> str:
    lines = [
        "## Benchmark refresh",
        "",
        f"- Status: `{status['status']}`",
        f"- Generated at: `{status['generated_at']}`",
        f"- Benchmark JSON: `{status['benchmark_json']}`",
        f"- Benchmark Markdown: `{status['benchmark_markdown']}`",
        f"- Stale claims: `{status['stale']}`",
        "",
        "### Deltas",
        "",
    ]
    lines.extend(status.get("delta_lines", []))
    if status.get("error"):
        lines.extend(["", "### Refresh error", "", "```text", status["error"], "```"])
    return "\n".join(lines) + "\n"


def write_refresh_status(repo_root: Path, status: dict[str, Any]) -> None:
    status_json = repo_root / "docs" / "benchmark-refresh-status.json"
    status_md = repo_root / "docs" / "benchmark-refresh-status.md"
    status_json.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status_md.write_text(build_pr_body_section(status), encoding="utf-8")


def refresh(repo_root: Path, python_bin: str) -> dict[str, Any]:
    benchmark_json = repo_root / "docs" / "hermes-turbo-benchmark-hermes-0.14.0.json"
    benchmark_md = repo_root / "docs" / "hermes-turbo-benchmark-hermes-0.14.0.md"
    previous = _load_json(benchmark_json)
    local_python = python_bin
    if not Path(local_python).is_absolute():
        local_python = shutil.which(local_python) or local_python
    try:
        _run(
            [
                python_bin,
                "scripts/benchmark_hermes_turbo_vs_hermes_0140.py",
                "--local-python",
                local_python,
                "--output-json",
                str(benchmark_json),
                "--output-md",
                str(benchmark_md),
            ],
            cwd=repo_root,
        )
        _run([python_bin, "scripts/generate_hermes_turbo_battle_cards.py"], cwd=repo_root)
        _run([python_bin, "scripts/generate_hermes_turbo_benchmark_report.py"], cwd=repo_root)
        current = _load_json(benchmark_json)
        if not current:
            raise RuntimeError("benchmark refresh did not produce JSON output")
        status = {
            "status": "ok",
            "stale": False,
            "generated_at": _now(),
            "benchmark_json": str(benchmark_json.relative_to(repo_root)),
            "benchmark_markdown": str(benchmark_md.relative_to(repo_root)),
            "delta_lines": build_delta_lines(previous, current),
        }
        write_refresh_status(repo_root, status)
        return status
    except Exception as exc:
        status = {
            "status": "failed",
            "stale": True,
            "generated_at": _now(),
            "benchmark_json": str(benchmark_json.relative_to(repo_root)),
            "benchmark_markdown": str(benchmark_md.relative_to(repo_root)),
            "delta_lines": ["- Benchmark refresh failed before measured deltas could be trusted."],
            "error": str(exc),
        }
        write_refresh_status(repo_root, status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        status = refresh(repo_root, args.python)
    except Exception:
        failed = _load_json(repo_root / "docs" / "benchmark-refresh-status.json") or {
            "status": "failed",
            "stale": True,
        }
        print(json.dumps(failed, indent=2, sort_keys=True))
        return 1
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
