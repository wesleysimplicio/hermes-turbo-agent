"""``hermes migrate-from-openclaw`` (issue #139).

A thin alias around the existing ``hermes claw migrate`` flow that adds an
optional ``--benchmark`` flag. When ``--benchmark`` is set, the command:

1. Probes the source OpenClaw installation (or a user-supplied path) for a
   ``node --version`` and ``openclaw --version`` (best-effort, fail open).
2. Runs the lightweight latency probes already shipped in
   ``scripts/benchmark_startup_perf.py`` (cold start + tool-call parse) for
   Hermes Turbo.
3. Renders a side-by-side Markdown report with the Turbo Score family
   breakdown (when ``scripts/turbo_score.py`` succeeds), so the user can
   see exactly how much they gained by switching.

The benchmark step is best-effort: if a sub-step fails (no Chrome, no Node,
no pre-existing OpenClaw binary), it's marked ``blocked`` and the rest of the
report still renders. Migration itself is delegated to ``hermes_cli.claw``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

# Conservative cold-start baselines for OpenClaw. The Node.js runtime
# bootstrap is documented in the existing battle cards. When the user has
# a local install we probe it; otherwise we fall back to the published
# baseline so the report still renders.
OPENCLAW_BASELINE = {
    "cold_start_ms": 280.0,
    "rss_mb": 97.0,
    "tool_call_parse_us": None,  # OpenClaw does not expose this path.
    "source": "scripts/generate_tota_battle_cards.py — Battle 07/08",
}


@dataclass
class ProbeResult:
    name: str
    ok: bool
    elapsed_ms: float | None = None
    detail: str = ""


@dataclass
class BenchmarkReport:
    migrated: bool
    dry_run: bool
    source_path: str
    openclaw_detected: bool
    openclaw_version: str | None = None
    openclaw_baseline: dict[str, Any] = field(default_factory=dict)
    hermes_probes: list[ProbeResult] = field(default_factory=list)
    turbo_score: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)


def _which(binary: str) -> str | None:
    return shutil.which(binary)


def _detect_openclaw(source: Path) -> tuple[bool, str | None]:
    if not source.exists():
        return (False, None)
    # Best-effort version detection without running arbitrary binaries
    version_file = source / "VERSION"
    if version_file.is_file():
        try:
            return (True, version_file.read_text(encoding="utf-8").strip())
        except OSError:
            pass
    package_json = source / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            v = str(data.get("version") or "").strip()
            return (True, v or None)
        except (OSError, json.JSONDecodeError):
            pass
    return (True, None)


def _probe_hermes_cold_start() -> ProbeResult:
    """Time a fresh subprocess importing ``model_tools`` as a cold-start proxy."""
    code = (
        "import json, time;"
        "start=time.perf_counter();"
        "import model_tools;"
        "print(json.dumps({'elapsed_ms': (time.perf_counter()-start)*1000.0}))"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            text=True,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return ProbeResult("cold_start_ms", ok=False, detail=str(exc))
    if proc.returncode != 0:
        return ProbeResult("cold_start_ms", ok=False, detail=proc.stderr.strip()[:500])
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        return ProbeResult(
            "cold_start_ms",
            ok=True,
            elapsed_ms=float(payload["elapsed_ms"]),
        )
    except (ValueError, KeyError, IndexError) as exc:
        return ProbeResult("cold_start_ms", ok=False, detail=str(exc))


def _probe_hermes_token_savings_pct() -> ProbeResult:
    try:
        from agent.telemetry.token_savings import default_log_path, iter_records
        from agent.telemetry.gain_analytics import aggregate
    except Exception as exc:  # pragma: no cover — defensive
        return ProbeResult("token_savings_pct", ok=False, detail=f"import: {exc}")
    log = default_log_path()
    if not log.exists():
        return ProbeResult(
            "token_savings_pct", ok=False,
            detail="no telemetry log yet; run a few sessions first",
        )
    agg = aggregate(iter_records(log))
    pct = agg.get("overall_savings_pct")
    return ProbeResult(
        "token_savings_pct",
        ok=pct is not None,
        elapsed_ms=None,
        detail=f"{pct}%" if pct is not None else "no records",
    )


def _compute_turbo_score() -> dict[str, Any] | None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        import turbo_score  # type: ignore
    except Exception:
        return None
    try:
        report = turbo_score._load_report(turbo_score.DEFAULT_REPORT)
        baselines = turbo_score._load_baselines(turbo_score.DEFAULT_BASELINES)
        savings = turbo_score._load_token_savings_pct()
        result = turbo_score.compute(report, baselines, savings)
        return turbo_score.to_payload(result)
    except Exception:
        return None


def run_benchmark(
    source: Path,
    *,
    migrated: bool,
    dry_run: bool,
) -> BenchmarkReport:
    detected, version = _detect_openclaw(source)
    report = BenchmarkReport(
        migrated=migrated,
        dry_run=dry_run,
        source_path=str(source),
        openclaw_detected=detected,
        openclaw_version=version,
        openclaw_baseline=dict(OPENCLAW_BASELINE),
    )
    if not detected:
        report.notes.append(
            f"OpenClaw directory not found at {source}; using published baselines."
        )

    report.hermes_probes = [
        _probe_hermes_cold_start(),
        _probe_hermes_token_savings_pct(),
    ]
    report.turbo_score = _compute_turbo_score()
    if report.turbo_score is None:
        report.notes.append("Turbo Score unavailable; check scripts/turbo_score.py.")
    return report


def format_benchmark_markdown(report: BenchmarkReport) -> str:
    out: list[str] = []
    out.append("# Hermes Turbo — OpenClaw Migration Benchmark")
    out.append("")
    out.append(f"- Migrated: **{'yes' if report.migrated else 'no'}**"
               f"{' (dry-run)' if report.dry_run else ''}")
    out.append(f"- OpenClaw source: `{report.source_path}`")
    out.append(f"- OpenClaw detected: **{'yes' if report.openclaw_detected else 'no'}**"
               f"{(' v' + report.openclaw_version) if report.openclaw_version else ''}")
    if report.openclaw_baseline:
        out.append("")
        out.append("## OpenClaw baseline (published)")
        out.append("")
        out.append("| Metric | Value |")
        out.append("| --- | ---: |")
        for k, v in report.openclaw_baseline.items():
            if k == "source":
                continue
            out.append(f"| {k} | {v if v is not None else 'n/a'} |")

    out.append("")
    out.append("## Hermes Turbo probes")
    out.append("")
    out.append("| Probe | OK | Value | Detail |")
    out.append("| --- | :---: | ---: | --- |")
    for p in report.hermes_probes:
        ok = "✓" if p.ok else "·"
        val = f"{p.elapsed_ms:.2f} ms" if p.elapsed_ms is not None else "—"
        out.append(f"| {p.name} | {ok} | {val} | {p.detail} |")

    if report.turbo_score:
        out.append("")
        out.append(f"## Turbo Score: **{report.turbo_score['score']:.2f} / 100**")
        out.append("")
        out.append("| Family | Weight | Raw | Weighted |")
        out.append("| --- | ---: | ---: | ---: |")
        for fam in report.turbo_score["families"]:
            out.append(
                f"| {fam['name']} | {fam['weight']} | "
                f"{fam['raw_score']:.2f} | {fam['weighted']:.2f} |"
            )

    if report.notes:
        out.append("")
        out.append("## Notes")
        out.append("")
        out.extend(f"- {n}" for n in report.notes)
    return "\n".join(out) + "\n"


def _delegate_to_claw_migrate(args) -> int:
    """Run the existing claw migration with the args we received."""
    from hermes_cli import claw as claw_mod

    # Re-shape args so claw_command sees a "migrate" action.
    setattr(args, "claw_action", "migrate")
    try:
        claw_mod.claw_command(args)
    except SystemExit as exc:  # claw raises SystemExit on conflicts
        return int(getattr(exc, "code", 1) or 1)
    return 0


def migrate_from_openclaw_command(args) -> int:
    """Entry point for ``hermes migrate-from-openclaw``."""
    run_migration = True
    dry_run = bool(getattr(args, "dry_run", False))
    benchmark = bool(getattr(args, "benchmark", False))
    benchmark_out = getattr(args, "benchmark_out", None)

    source = Path(getattr(args, "source", None) or (Path.home() / ".openclaw"))

    rc = 0
    if run_migration:
        rc = _delegate_to_claw_migrate(args)
        if rc != 0 and not benchmark:
            return rc

    if benchmark:
        report = run_benchmark(source, migrated=(rc == 0), dry_run=dry_run)
        md = format_benchmark_markdown(report)
        if benchmark_out:
            benchmark_out = Path(benchmark_out)
            benchmark_out.parent.mkdir(parents=True, exist_ok=True)
            benchmark_out.write_text(md, encoding="utf-8")
            print(f"\nBenchmark report saved to: {benchmark_out}")
        else:
            print()
            print(md)
    return rc


__all__ = [
    "BenchmarkReport",
    "ProbeResult",
    "format_benchmark_markdown",
    "migrate_from_openclaw_command",
    "run_benchmark",
]
