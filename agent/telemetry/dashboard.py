"""CLI dashboard: reads the telemetry JSONL and prints per-stage percentiles.

Usage:
    python -m agent.telemetry.dashboard [--log PATH] [--group-by stage|provider|model|tool]

Outputs an ASCII table with count, p50, p95, p99, and mean (milliseconds) per
group key. Pure stdlib; safe to run offline against a captured log.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .stage_timer import get_log_path


GROUP_KEYS = ("stage", "provider", "model", "tool")


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    # Nearest-rank percentile (no interpolation, stdlib only).
    k = max(0, min(len(sorted_values) - 1, int(round(pct / 100.0 * (len(sorted_values) - 1)))))
    return sorted_values[k]


def _iter_events(path: Path) -> Iterable[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def summarize(path: Path, group_by: str = "stage") -> list[dict]:
    """Aggregate JSONL events into per-group percentile rows."""
    if group_by not in GROUP_KEYS:
        raise ValueError(f"group_by must be one of {GROUP_KEYS}, got {group_by!r}")
    buckets: dict[str, list[float]] = defaultdict(list)
    errors: dict[str, int] = defaultdict(int)
    for event in _iter_events(path):
        key = event.get(group_by) or "(none)"
        try:
            buckets[key].append(float(event.get("duration_ms", 0.0)))
        except (TypeError, ValueError):
            continue
        if not event.get("ok", True):
            errors[key] += 1
    rows: list[dict] = []
    for key, durations in buckets.items():
        durations.sort()
        count = len(durations)
        rows.append(
            {
                "key": key,
                "count": count,
                "errors": errors.get(key, 0),
                "p50_ms": round(_percentile(durations, 50), 2),
                "p95_ms": round(_percentile(durations, 95), 2),
                "p99_ms": round(_percentile(durations, 99), 2),
                "mean_ms": round(sum(durations) / count, 2) if count else 0.0,
            }
        )
    rows.sort(key=lambda r: r["p95_ms"], reverse=True)
    return rows


def format_table(rows: list[dict], group_by: str) -> str:
    header = (group_by, "count", "errors", "p50_ms", "p95_ms", "p99_ms", "mean_ms")
    widths = [max(len(h), 8) for h in header]
    str_rows = []
    for r in rows:
        cells = (
            str(r["key"]),
            str(r["count"]),
            str(r["errors"]),
            f"{r['p50_ms']:.2f}",
            f"{r['p95_ms']:.2f}",
            f"{r['p99_ms']:.2f}",
            f"{r['mean_ms']:.2f}",
        )
        str_rows.append(cells)
        for i, c in enumerate(cells):
            widths[i] = max(widths[i], len(c))
    sep_line = "+".join("-" * (w + 2) for w in widths)
    sep_line = f"+{sep_line}+"

    def fmt(cells: tuple[str, ...]) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

    lines = [sep_line, fmt(header), sep_line]
    lines.extend(fmt(c) for c in str_rows)
    lines.append(sep_line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes runtime telemetry dashboard")
    parser.add_argument("--log", type=Path, default=None, help="path to telemetry JSONL")
    parser.add_argument(
        "--group-by",
        choices=GROUP_KEYS,
        default="stage",
        help="group events by this field (default: stage)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of table")
    args = parser.parse_args(argv)

    path = args.log or get_log_path()
    rows = summarize(path, group_by=args.group_by)
    if not rows:
        print(f"no telemetry events found at {path}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"telemetry: {path}  ({sum(r['count'] for r in rows)} events)")
        print(format_table(rows, args.group_by))
    return 0


if __name__ == "__main__":
    sys.exit(main())
