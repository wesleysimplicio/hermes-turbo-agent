"""ClawBench-style agent evaluation runner.

Loads JSON task specs from ``eval/clawbench/tasks/``, invokes a pluggable agent
callable, and scores the agent's output against the expected result using the
scorers in :mod:`eval.clawbench.scorer`.

Designed to be standard-library only so it runs in CI without extra deps.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

# Allow running as a plain script without package install.
sys.path.insert(0, str(Path(__file__).parent))

from scorer import score  # noqa: E402

TASKS_DIR = Path(__file__).parent / "tasks"


def load_tasks(tasks_dir: Path = TASKS_DIR) -> Iterable[Dict[str, Any]]:
    """Yield task specs from JSON files in *tasks_dir* (sorted by name)."""
    for path in sorted(tasks_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fp:
            task = json.load(fp)
        task["_path"] = str(path)
        yield task


def echo_agent(task: Dict[str, Any]) -> str:
    """Stub agent used for --dry-run. Returns the task's expected output."""
    return str(task.get("expected", ""))


def run(
    agent: Callable[[Dict[str, Any]], str] = echo_agent,
    tasks_dir: Path = TASKS_DIR,
) -> Dict[str, Any]:
    """Run *agent* against every task in *tasks_dir* and return a report."""
    results = []
    for task in load_tasks(tasks_dir):
        started = time.time()
        try:
            output = agent(task)
            error = None
        except Exception as exc:  # noqa: BLE001
            output = ""
            error = repr(exc)
        elapsed_ms = int((time.time() - started) * 1000)
        scoring = score(
            output,
            task.get("expected", ""),
            mode=task.get("scorer", "exact"),
        )
        results.append(
            {
                "id": task.get("id"),
                "kind": task.get("kind"),
                "elapsed_ms": elapsed_ms,
                "scorer": task.get("scorer", "exact"),
                "score": scoring,
                "error": error,
            }
        )
    passed = sum(1 for r in results if r["score"] >= 1.0)
    total = len(results)
    return {
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": (passed / total) if total else 0.0,
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Use stub echo agent (no external calls).")
    parser.add_argument("--tasks-dir", default=str(TASKS_DIR),
                        help="Directory containing task JSON specs.")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON report.")
    args = parser.parse_args(argv)

    report = run(agent=echo_agent, tasks_dir=Path(args.tasks_dir))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        s = report["summary"]
        print(f"clawbench: {s['passed']}/{s['total']} passed "
              f"({s['pass_rate'] * 100:.1f}%)")
        for r in report["results"]:
            mark = "ok" if r["score"] >= 1.0 else "FAIL"
            print(f"  [{mark}] {r['id']:<28} scorer={r['scorer']:<6} "
                  f"score={r['score']:.2f} elapsed_ms={r['elapsed_ms']}")
    return 0 if report["summary"]["passed"] == report["summary"]["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
