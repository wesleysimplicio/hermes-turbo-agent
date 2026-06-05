"""Gain analytics CLI for token savings telemetry. See docs/perf/."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Optional

from agent.telemetry.token_savings import default_log_path, iter_records


def _int(rec: dict, key: str) -> int:
    try:
        return int(rec.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _day(ts: str) -> str:
    return ts[:10] if isinstance(ts, str) and len(ts) >= 10 else "unknown"


def aggregate(records: Iterable[dict]) -> dict:
    total_raw = total_comp = count = 0
    by_tool: dict[str, dict[str, int]] = defaultdict(lambda: {"raw": 0, "saved": 0, "calls": 0})
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"raw": 0, "saved": 0, "calls": 0})
    by_adapter: dict[str, int] = defaultdict(int)

    for rec in records:
        raw, comp = _int(rec, "raw_tokens"), _int(rec, "compressed_tokens")
        saved = _int(rec, "saved_tokens") or max(0, raw - comp)
        total_raw += raw
        total_comp += comp
        count += 1
        for bucket, key in ((by_tool, str(rec.get("tool") or "unknown")),
                            (by_day, _day(str(rec.get("ts") or "")))):
            bucket[key]["raw"] += raw
            bucket[key]["saved"] += saved
            bucket[key]["calls"] += 1
        by_adapter[str(rec.get("adapter") or "unknown")] += saved

    saved_total = max(0, total_raw - total_comp)
    pct = round(100.0 * saved_total / total_raw, 2) if total_raw else 0.0
    return {
        "records": count,
        "total_raw_tokens": total_raw,
        "total_compressed_tokens": total_comp,
        "total_saved_tokens": saved_total,
        "overall_savings_pct": pct,
        "by_tool": dict(by_tool),
        "by_day": dict(by_day),
        "by_adapter": dict(by_adapter),
    }


def top_wasteful_tools(agg: dict, limit: int = 5) -> list[tuple[str, int, int]]:
    """Return (tool, raw_tokens, saved_tokens) sorted by raw desc."""
    items = [(t, v["raw"], v["saved"]) for t, v in agg.get("by_tool", {}).items()]
    items.sort(key=lambda r: r[1], reverse=True)
    return items[: max(0, limit)]


def trend(agg: dict) -> list[tuple[str, int, int]]:
    """Return (day, raw, saved) sorted by day ascending."""
    items = [(d, v["raw"], v["saved"]) for d, v in agg.get("by_day", {}).items()]
    items.sort(key=lambda r: r[0])
    return items


def _format_report(agg: dict, top_n: int) -> str:
    head = [
        "Hermes Turbo - Token Savings Report", "-" * 40,
        f"Records:           {agg['records']}",
        f"Raw tokens:        {agg['total_raw_tokens']}",
        f"Compressed tokens: {agg['total_compressed_tokens']}",
        f"Saved tokens:      {agg['total_saved_tokens']}",
        f"Overall savings:   {agg['overall_savings_pct']}%", "",
        f"Top {top_n} tools by raw tokens spent:",
    ]
    head += [f"  - {t:<24} raw={r:>8} saved={s:>8}" for t, r, s in top_wasteful_tools(agg, top_n)]
    head += ["", "Daily trend:"]
    head += [f"  {d}  raw={r:>8}  saved={s:>8}" for d, r, s in trend(agg)]
    return "\n".join(head)


def run(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes-token-savings",
        description="Aggregate Hermes Turbo token-savings telemetry.",
    )
    parser.add_argument("--log", type=Path, default=None, help="JSONL log path.")
    parser.add_argument("--top", type=int, default=5, help="How many tools to list.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    agg = aggregate(iter_records(args.log or default_log_path()))
    if args.json:
        json.dump(agg, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(_format_report(agg, args.top) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
