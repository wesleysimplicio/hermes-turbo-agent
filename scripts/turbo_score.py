#!/usr/bin/env python3
"""Compute the Hermes Turbo Score from existing benchmark JSON.

The Turbo Score is a single 0-100 number that combines five families of
measurements into one comparable figure of merit:

    Latency      — async scheduler, JSON dumps, tool-call parse  (lower is better)
    Throughput   — token estimate batch, message pipeline        (speedup vs stock)
    Memory       — RSS                                            (lower is better)
    Cold start   — fresh subprocess startup                       (lower is better)
    Token savings — telemetry log aggregate                       (higher is better)

The reference dataset is ``docs/tota-benchmark-hermes-0.14.0.json`` plus an
optional ``docs/turbo-score-baselines.json`` for memory/cold-start values that
the upstream benchmark does not include. If the baseline file is missing the
matching family is dropped from the score (with a note in the JSON output)
rather than failing the run.

Usage::

    python scripts/turbo_score.py                # ASCII report to stdout
    python scripts/turbo_score.py --json         # machine-readable JSON
    python scripts/turbo_score.py --markdown     # README-ready Markdown block

Designed to be invoked from CI without third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "docs" / "tota-benchmark-hermes-0.14.0.json"
DEFAULT_BASELINES = ROOT / "docs" / "turbo-score-baselines.json"


# Family weights — must sum to 100. Latency-heavy because that's what the
# users perceive in interactive sessions.
WEIGHTS = {
    "latency": 30,
    "throughput": 20,
    "memory": 15,
    "cold_start": 15,
    "token_savings": 20,
}


# Metric → family map. Each metric is expressed as a speedup ratio vs the
# stock Hermes baseline (>=1.0 means Turbo wins, <1.0 means Turbo loses).
LATENCY_METRICS = (
    "async_1000_task_ms",
    "json_dumps_short_us",
    "tool_call_parse_us",
)
THROUGHPUT_METRICS = (
    "token_estimate_batch_us",
)
COLD_START_METRICS = (
    "cold_start_ms",
)


@dataclass(frozen=True)
class FamilyScore:
    name: str
    weight: int
    raw_score: float          # 0..1 — speedup vs baseline, clamped
    weighted: float           # raw_score * weight
    metric_count: int
    notes: str = ""


@dataclass(frozen=True)
class TurboScore:
    score: float              # 0..100
    families: tuple[FamilyScore, ...]
    missing_families: tuple[str, ...] = field(default_factory=tuple)


def _speedup(metric: dict) -> float | None:
    """Read ``speedup`` from a metric entry. None if the run was blocked."""
    val = metric.get("speedup")
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _score_from_speedups(speedups: list[float]) -> float:
    """Convert a list of speedup ratios into a 0..1 family score.

    A speedup of 1.0 (tie) yields 0.5; >=2.0x yields 1.0; <=0.5x yields 0.0.
    Geometric mean is used so a single huge win doesn't mask a regression.
    """
    if not speedups:
        return 0.0
    # geometric mean
    log_sum = 0.0
    for s in speedups:
        log_sum += _log2(max(0.0625, min(16.0, s)))
    geo_mean = 2 ** (log_sum / len(speedups))
    # map [0.5x, 2.0x] linearly to [0.0, 1.0] with 1.0x at 0.5
    return _clamp((geo_mean - 0.5) / 1.5)


def _log2(x: float) -> float:
    # tiny stdlib-only helper to avoid importing math at module load time
    import math
    return math.log2(x)


def _ratio_score(value: float | None, baseline: float | None) -> float | None:
    """Score (lower is better): baseline / value → speedup-like."""
    if value is None or baseline is None or value <= 0:
        return None
    return baseline / value


def _family_latency(metrics: dict) -> FamilyScore:
    speedups = []
    for key in LATENCY_METRICS:
        if key in metrics:
            s = _speedup(metrics[key])
            if s is not None:
                speedups.append(s)
    raw = _score_from_speedups(speedups)
    return FamilyScore(
        name="latency",
        weight=WEIGHTS["latency"],
        raw_score=raw,
        weighted=raw * WEIGHTS["latency"],
        metric_count=len(speedups),
    )


def _family_throughput(metrics: dict) -> FamilyScore:
    speedups = []
    for key in THROUGHPUT_METRICS:
        if key in metrics:
            s = _speedup(metrics[key])
            if s is not None:
                speedups.append(s)
    raw = _score_from_speedups(speedups)
    return FamilyScore(
        name="throughput",
        weight=WEIGHTS["throughput"],
        raw_score=raw,
        weighted=raw * WEIGHTS["throughput"],
        metric_count=len(speedups),
    )


def _family_cold_start(metrics: dict) -> FamilyScore:
    speedups = []
    for key in COLD_START_METRICS:
        if key in metrics:
            s = _speedup(metrics[key])
            if s is not None:
                speedups.append(s)
    raw = _score_from_speedups(speedups)
    return FamilyScore(
        name="cold_start",
        weight=WEIGHTS["cold_start"],
        raw_score=raw,
        weighted=raw * WEIGHTS["cold_start"],
        metric_count=len(speedups),
    )


def _family_memory(baselines: dict) -> FamilyScore | None:
    memory = baselines.get("memory_rss_mb")
    if not memory:
        return None
    stock = memory.get("stock")
    local = memory.get("local")
    if stock in (None, 0) or local in (None, 0):
        return None
    speedup = float(stock) / float(local)
    raw = _score_from_speedups([speedup])
    return FamilyScore(
        name="memory",
        weight=WEIGHTS["memory"],
        raw_score=raw,
        weighted=raw * WEIGHTS["memory"],
        metric_count=1,
        notes=f"stock={stock}MB local={local}MB",
    )


def _family_token_savings(savings_pct: float | None) -> FamilyScore | None:
    if savings_pct is None:
        return None
    # 0% savings → 0.0; 50% savings → 1.0; clamp above
    raw = _clamp(float(savings_pct) / 50.0)
    return FamilyScore(
        name="token_savings",
        weight=WEIGHTS["token_savings"],
        raw_score=raw,
        weighted=raw * WEIGHTS["token_savings"],
        metric_count=1,
        notes=f"overall_savings_pct={savings_pct:.2f}",
    )


def _load_report(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_baselines(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_token_savings_pct() -> float | None:
    """Best-effort: ask gain_analytics for the overall savings_pct."""
    try:
        from agent.telemetry.token_savings import default_log_path, iter_records
        from agent.telemetry.gain_analytics import aggregate
    except Exception:
        return None
    log_path = default_log_path()
    if not log_path.exists():
        return None
    agg = aggregate(iter_records(log_path))
    return agg.get("overall_savings_pct")


def compute(
    report: dict,
    baselines: dict | None = None,
    savings_pct: float | None = None,
) -> TurboScore:
    """Compute the Turbo Score from a parsed report dict.

    ``report`` is the parsed contents of ``tota-benchmark-hermes-X.json``.
    ``baselines`` supplies memory/cold-start values not in ``report``.
    ``savings_pct`` is the overall token-savings percentage from telemetry.
    """
    metrics = (report or {}).get("metrics", {}) or {}
    baselines = baselines or {}

    families = []
    missing: list[str] = []

    families.append(_family_latency(metrics))
    families.append(_family_throughput(metrics))
    families.append(_family_cold_start(metrics))

    memory_family = _family_memory(baselines)
    if memory_family is None:
        missing.append("memory")
    else:
        families.append(memory_family)

    token_family = _family_token_savings(savings_pct)
    if token_family is None:
        missing.append("token_savings")
    else:
        families.append(token_family)

    total_weight = sum(f.weight for f in families) or 1
    score = sum(f.weighted for f in families) * (100.0 / total_weight)
    return TurboScore(
        score=round(score, 2),
        families=tuple(families),
        missing_families=tuple(missing),
    )


def format_text(turbo: TurboScore) -> str:
    lines = [
        "Hermes Turbo Score",
        "=" * 40,
        f"Score: {turbo.score:.2f} / 100",
        "",
        "Family breakdown:",
    ]
    for fam in turbo.families:
        marker = "✓" if fam.raw_score >= 0.5 else "·"
        lines.append(
            f"  {marker} {fam.name:<14}"
            f" weight={fam.weight:>3}"
            f"  raw={fam.raw_score:.2f}"
            f"  weighted={fam.weighted:.2f}"
            f"  metrics={fam.metric_count}"
        )
        if fam.notes:
            lines.append(f"      note: {fam.notes}")
    if turbo.missing_families:
        lines.append("")
        lines.append(
            "Missing families (dropped from total weight): "
            + ", ".join(turbo.missing_families)
        )
    return "\n".join(lines)


def format_markdown(turbo: TurboScore) -> str:
    rows = ["| Family | Weight | Raw | Weighted | Metrics |", "| --- | ---: | ---: | ---: | ---: |"]
    for fam in turbo.families:
        rows.append(
            f"| {fam.name} | {fam.weight} | {fam.raw_score:.2f}"
            f" | {fam.weighted:.2f} | {fam.metric_count} |"
        )
    body = "\n".join(rows)
    missing_line = ""
    if turbo.missing_families:
        missing_line = (
            f"\n\n_Missing families (dropped from total weight): "
            f"{', '.join(turbo.missing_families)}_"
        )
    return f"## Turbo Score: **{turbo.score:.2f} / 100**\n\n{body}{missing_line}\n"


def to_payload(turbo: TurboScore) -> dict[str, Any]:
    return {
        "score": turbo.score,
        "families": [
            {
                "name": f.name,
                "weight": f.weight,
                "raw_score": round(f.raw_score, 4),
                "weighted": round(f.weighted, 4),
                "metric_count": f.metric_count,
                "notes": f.notes,
            }
            for f in turbo.families
        ],
        "missing_families": list(turbo.missing_families),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT,
                        help="path to benchmark JSON")
    parser.add_argument("--baselines", type=Path, default=DEFAULT_BASELINES,
                        help="path to memory/cold-start baselines JSON")
    parser.add_argument("--savings-pct", type=float, default=None,
                        help="override token-savings percentage")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--markdown", action="store_true",
                        help="emit Markdown (README-ready)")
    parser.add_argument("--out", type=Path, default=None,
                        help="write output to file instead of stdout")
    args = parser.parse_args(argv)

    report = _load_report(args.report)
    baselines = _load_baselines(args.baselines)
    savings_pct = args.savings_pct
    if savings_pct is None:
        savings_pct = _load_token_savings_pct()

    turbo = compute(report, baselines, savings_pct)

    if args.json:
        out = json.dumps(to_payload(turbo), indent=2)
    elif args.markdown:
        out = format_markdown(turbo)
    else:
        out = format_text(turbo)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out + "\n", encoding="utf-8")
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
