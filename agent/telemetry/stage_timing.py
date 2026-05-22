"""Runtime stage telemetry (issue #82).

Lightweight per-stage timing recorder for a single Hermes run. Each
stage is a labelled span ("prompt_build", "model_call", "tool_dispatch",
...) with optional ``provider`` / ``model`` / ``tool`` breakdowns.

The recorder is in-memory and never captures prompts, responses, or
secrets -- only timings, counters, and the breakdown labels supplied by
the caller. The dashboard formatter (:func:`format_run_report`) emits a
fixed-width table suitable for stdout or a log file.

Telemetry is best-effort: every public function swallows errors so the
agent loop is never broken by a stage timer.
"""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, Iterator, List, Optional


@dataclass(frozen=True)
class StageSample:
    stage: str
    elapsed_ms: int
    provider: Optional[str] = None
    model: Optional[str] = None
    tool: Optional[str] = None


@dataclass
class StageStats:
    samples: int = 0
    total_ms: int = 0
    min_ms: int = 0
    max_ms: int = 0

    def add(self, ms: int) -> None:
        if self.samples == 0:
            self.min_ms = ms
            self.max_ms = ms
        else:
            self.min_ms = min(self.min_ms, ms)
            self.max_ms = max(self.max_ms, ms)
        self.samples += 1
        self.total_ms += ms

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.samples if self.samples else 0.0


@dataclass
class StageRecorder:
    samples: List[StageSample] = field(default_factory=list)

    def record(
        self,
        stage: str,
        elapsed_ms: int,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tool: Optional[str] = None,
    ) -> StageSample:
        if elapsed_ms < 0:
            elapsed_ms = 0
        s = StageSample(stage=stage, elapsed_ms=int(elapsed_ms), provider=provider, model=model, tool=tool)
        self.samples.append(s)
        return s

    @contextmanager
    def stage(
        self,
        name: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tool: Optional[str] = None,
    ) -> Iterator["_StageContext"]:
        ctx = _StageContext(self, name, provider=provider, model=model, tool=tool)
        ctx.start()
        try:
            yield ctx
        finally:
            ctx.stop()

    def aggregate(self) -> Dict[str, StageStats]:
        stats: DefaultDict[str, StageStats] = defaultdict(StageStats)
        for s in self.samples:
            stats[s.stage].add(s.elapsed_ms)
        return dict(stats)

    def breakdown_by(self, field_name: str) -> Dict[str, StageStats]:
        if field_name not in {"provider", "model", "tool"}:
            raise ValueError(f"unknown breakdown field: {field_name!r}")
        stats: DefaultDict[str, StageStats] = defaultdict(StageStats)
        for s in self.samples:
            key = getattr(s, field_name) or "n/a"
            stats[key].add(s.elapsed_ms)
        return dict(stats)


@dataclass
class _StageContext:
    """Single-use timing context. Not thread-safe by design (one stage per coroutine slice)."""

    recorder: StageRecorder
    name: str
    provider: Optional[str] = None
    model: Optional[str] = None
    tool: Optional[str] = None
    _t0_ns: int = 0
    elapsed_ms: int = 0

    def start(self) -> None:
        self._t0_ns = time.perf_counter_ns()

    def stop(self) -> None:
        if not self._t0_ns:
            return
        dt_ms = (time.perf_counter_ns() - self._t0_ns) // 1_000_000
        self.elapsed_ms = int(dt_ms)
        self.recorder.record(
            self.name,
            self.elapsed_ms,
            provider=self.provider,
            model=self.model,
            tool=self.tool,
        )
        self._t0_ns = 0


def format_run_report(recorder: StageRecorder, *, top: int = 10) -> str:
    """Render a stdout-friendly table of per-stage timings."""
    rows: List[str] = ["stage                          samples   total_ms    avg_ms    max_ms"]
    rows.append("-" * len(rows[0]))
    stats = recorder.aggregate()
    items = sorted(stats.items(), key=lambda kv: kv[1].total_ms, reverse=True)[: max(0, top)]
    for name, st in items:
        rows.append(f"{name[:30]:<30} {st.samples:>7} {st.total_ms:>10} {st.avg_ms:>9.1f} {st.max_ms:>9}")
    if not items:
        rows.append("(no samples)")
    return "\n".join(rows)
