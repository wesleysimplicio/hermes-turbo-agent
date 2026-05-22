"""Weekly Token Savings Report (issue #138).

Builds on top of :mod:`agent.telemetry.token_savings` and
:mod:`agent.telemetry.gain_analytics`. Adds:

* Time-window filtering (last N days, default 7)
* Per-adapter cost estimation (USD) using a small pricing table that callers
  can override
* JSON / Markdown / plain-text output suitable for piping into Slack, email,
  or GitHub Step Summary

CLI usage::

    python -m agent.telemetry.savings_report --since 7d
    python -m agent.telemetry.savings_report --json
    python -m agent.telemetry.savings_report --markdown --out report.md

The CLI is also bound to ``hermes report savings``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from agent.telemetry.token_savings import default_log_path, iter_records


# Default $/1M tokens for the saved-tokens valuation. Conservative averages
# across input+output prices from public 2026-05 price lists. Callers can
# override via ``--prices path/to/prices.json`` or the API surface.
DEFAULT_PRICE_USD_PER_M = {
    "anthropic":    3.00,
    "openai":       2.50,
    "google":       1.25,
    "gemini":       1.25,
    "openrouter":   2.00,
    "default":      2.00,
}


_SINCE_RE = re.compile(r"^(\d+)([dhwm])$")


def parse_since(spec: str) -> timedelta:
    """Parse '7d', '24h', '2w', '30m' into a timedelta."""
    if spec is None:
        return timedelta(days=7)
    m = _SINCE_RE.match(spec.strip().lower())
    if not m:
        raise ValueError(f"invalid --since value {spec!r}; use Nd, Nh, Nw, Nm")
    n, unit = int(m.group(1)), m.group(2)
    return {
        "d": timedelta(days=n),
        "h": timedelta(hours=n),
        "w": timedelta(weeks=n),
        "m": timedelta(minutes=n),
    }[unit]


def _parse_ts(ts: str) -> Optional[datetime]:
    if not isinstance(ts, str) or len(ts) < 10:
        return None
    try:
        # Accept both '...Z' and '+00:00'
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _records_in_window(
    records: Iterable[dict],
    since: timedelta,
    now: Optional[datetime] = None,
) -> list[dict]:
    cutoff = (now or datetime.now(timezone.utc)) - since
    kept = []
    for rec in records:
        ts = _parse_ts(str(rec.get("ts") or ""))
        if ts is None or ts >= cutoff:
            kept.append(rec)
    return kept


def _int(rec: dict, key: str) -> int:
    try:
        return int(rec.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _adapter_price(adapter: str, prices: dict[str, float]) -> float:
    if not adapter:
        return prices.get("default", DEFAULT_PRICE_USD_PER_M["default"])
    key = adapter.lower().strip()
    if key in prices:
        return prices[key]
    # Heuristic: prefix-match (e.g. "openai-gpt5" → "openai")
    for known, price in prices.items():
        if known == "default":
            continue
        if key.startswith(known):
            return price
    return prices.get("default", DEFAULT_PRICE_USD_PER_M["default"])


def build_report(
    records: Iterable[dict],
    *,
    since: timedelta = timedelta(days=7),
    prices: Optional[dict[str, float]] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Aggregate records into a weekly-style report payload."""
    prices = {**DEFAULT_PRICE_USD_PER_M, **(prices or {})}
    now = now or datetime.now(timezone.utc)
    windowed = _records_in_window(records, since=since, now=now)

    total_raw = total_saved = total_calls = 0
    usd_saved = 0.0
    by_adapter: dict[str, dict[str, float]] = defaultdict(
        lambda: {"raw": 0, "saved": 0, "calls": 0, "usd": 0.0}
    )
    by_tool: dict[str, dict[str, int]] = defaultdict(
        lambda: {"raw": 0, "saved": 0, "calls": 0}
    )
    by_day: dict[str, dict[str, int]] = defaultdict(
        lambda: {"raw": 0, "saved": 0, "calls": 0}
    )

    for rec in windowed:
        raw = _int(rec, "raw_tokens")
        comp = _int(rec, "compressed_tokens")
        saved = _int(rec, "saved_tokens") or max(0, raw - comp)
        adapter = str(rec.get("adapter") or "unknown")
        tool = str(rec.get("tool") or "unknown")
        day = str(rec.get("ts") or "")[:10] or "unknown"
        price = _adapter_price(adapter, prices)
        per_record_usd = (saved / 1_000_000.0) * price

        total_raw += raw
        total_saved += saved
        total_calls += 1
        usd_saved += per_record_usd

        a = by_adapter[adapter]
        a["raw"] += raw
        a["saved"] += saved
        a["calls"] += 1
        a["usd"] += per_record_usd

        t = by_tool[tool]
        t["raw"] += raw
        t["saved"] += saved
        t["calls"] += 1

        d = by_day[day]
        d["raw"] += raw
        d["saved"] += saved
        d["calls"] += 1

    overall_pct = round(100.0 * total_saved / total_raw, 2) if total_raw else 0.0
    return {
        "window": {
            "since_days": round(since.total_seconds() / 86400, 2),
            "until": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "records": len(windowed),
        },
        "totals": {
            "raw_tokens": total_raw,
            "saved_tokens": total_saved,
            "compressed_tokens": max(0, total_raw - total_saved),
            "calls": total_calls,
            "overall_savings_pct": overall_pct,
            "estimated_usd_saved": round(usd_saved, 4),
        },
        "by_adapter": {k: {**v, "usd": round(v["usd"], 4)} for k, v in by_adapter.items()},
        "by_tool": {k: dict(v) for k, v in by_tool.items()},
        "by_day": {k: dict(v) for k, v in sorted(by_day.items())},
        "prices_usd_per_m": prices,
    }


def format_text(report: dict[str, Any]) -> str:
    t = report["totals"]
    w = report["window"]
    head = [
        "Hermes Turbo — Token Savings Report",
        "=" * 48,
        f"Window:            last {w['since_days']} days (until {w['until']})",
        f"Records:           {w['records']}",
        f"Raw tokens:        {t['raw_tokens']:>10}",
        f"Saved tokens:      {t['saved_tokens']:>10}",
        f"Compressed tokens: {t['compressed_tokens']:>10}",
        f"Overall savings:   {t['overall_savings_pct']}%",
        f"Estimated USD:     ${t['estimated_usd_saved']:.4f}",
    ]
    if report["by_adapter"]:
        head.append("")
        head.append("By adapter:")
        for name, v in sorted(report["by_adapter"].items(),
                              key=lambda kv: kv[1]["saved"], reverse=True):
            head.append(
                f"  - {name:<16} saved={v['saved']:>8}  "
                f"calls={v['calls']:>5}  usd=${v['usd']:.4f}"
            )
    if report["by_tool"]:
        head.append("")
        head.append("Top tools (by raw tokens):")
        items = sorted(report["by_tool"].items(),
                       key=lambda kv: kv[1]["raw"], reverse=True)[:5]
        for name, v in items:
            head.append(
                f"  - {name:<24} raw={v['raw']:>8}  saved={v['saved']:>8}  "
                f"calls={v['calls']:>5}"
            )
    return "\n".join(head)


def format_markdown(report: dict[str, Any]) -> str:
    t = report["totals"]
    w = report["window"]
    out: list[str] = []
    out.append("# Hermes Turbo — Token Savings Report")
    out.append("")
    out.append(f"Window: **last {w['since_days']} days** (until {w['until']})")
    out.append("")
    out.append(f"- **Saved tokens:** {t['saved_tokens']}")
    out.append(f"- **Overall savings:** {t['overall_savings_pct']}%")
    out.append(f"- **Estimated USD saved:** ${t['estimated_usd_saved']:.4f}")
    out.append(f"- **Records:** {w['records']}")
    if report["by_adapter"]:
        out.append("")
        out.append("## By adapter")
        out.append("")
        out.append("| Adapter | Saved tokens | Calls | USD |")
        out.append("| --- | ---: | ---: | ---: |")
        for name, v in sorted(report["by_adapter"].items(),
                              key=lambda kv: kv[1]["saved"], reverse=True):
            out.append(
                f"| {name} | {v['saved']} | {v['calls']} | ${v['usd']:.4f} |"
            )
    if report["by_tool"]:
        out.append("")
        out.append("## Top tools")
        out.append("")
        out.append("| Tool | Raw | Saved | Calls |")
        out.append("| --- | ---: | ---: | ---: |")
        items = sorted(report["by_tool"].items(),
                       key=lambda kv: kv[1]["raw"], reverse=True)[:5]
        for name, v in items:
            out.append(f"| {name} | {v['raw']} | {v['saved']} | {v['calls']} |")
    return "\n".join(out) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes-savings-report",
        description="Weekly Token Savings Report for Hermes Turbo.",
    )
    parser.add_argument(
        "--log", type=Path, default=None,
        help="Path to the JSONL savings log (default: ~/.hermes/telemetry/...).",
    )
    parser.add_argument(
        "--since", default="7d",
        help="Time window for the report. e.g. 7d, 24h, 4w. (default: 7d)",
    )
    parser.add_argument(
        "--prices", type=Path, default=None,
        help="Optional JSON file overriding USD/1M-token prices per adapter.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--markdown", action="store_true",
                        help="Emit Markdown (Slack/email/GH-friendly).")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write to file instead of stdout.")
    args = parser.parse_args(argv)

    prices: dict[str, float] = {}
    if args.prices and args.prices.exists():
        try:
            prices = json.loads(args.prices.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"warning: could not parse {args.prices}: {exc}", file=sys.stderr)

    try:
        since = parse_since(args.since)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    log_path = args.log or default_log_path()
    records = list(iter_records(log_path))
    report = build_report(records, since=since, prices=prices)

    if args.json:
        out = json.dumps(report, indent=2, sort_keys=True)
    elif args.markdown:
        out = format_markdown(report)
    else:
        out = format_text(report)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out + "\n", encoding="utf-8")
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
