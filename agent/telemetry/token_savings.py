"""Token savings telemetry (JSONL, no secrets). See docs/perf/."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

_ENV = "HERMES_TOKEN_SAVINGS_LOG"
_REL = Path(".hermes") / "telemetry" / "token_savings.jsonl"


def default_log_path() -> Path:
    """Return the JSONL log path (env override or ``~/.hermes/...``)."""
    override = os.environ.get(_ENV)
    return Path(override).expanduser() if override else Path.home() / _REL


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class TokenSavingRecord:
    """A single token-savings event."""

    raw_tokens: int
    compressed_tokens: int
    tool: str = "unknown"
    command: str = "unknown"
    adapter: str = "unknown"
    session: str = "unknown"
    repo: str = "unknown"
    ts: str = field(default_factory=_utc_now)
    savings_pct: float = 0.0

    @property
    def saved_tokens(self) -> int:
        return max(0, self.raw_tokens - self.compressed_tokens)

    def to_json(self) -> str:
        payload = asdict(self)
        payload["saved_tokens"] = self.saved_tokens
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _pct(raw: int, comp: int) -> float:
    if raw <= 0:
        return 0.0
    return round(100.0 * max(0, raw - comp) / raw, 2)


def record_token_saving(
    raw_tokens: int,
    compressed_tokens: int,
    *,
    tool: str = "unknown",
    command: str = "unknown",
    adapter: str = "unknown",
    session: str = "unknown",
    repo: str = "unknown",
    log_path: Optional[Path] = None,
) -> TokenSavingRecord:
    """Append a savings entry. Silent on disk errors."""
    raw = max(0, int(raw_tokens))
    comp = min(max(0, int(compressed_tokens)), raw)
    record = TokenSavingRecord(
        raw_tokens=raw, compressed_tokens=comp,
        tool=tool, command=command, adapter=adapter, session=session, repo=repo,
        savings_pct=_pct(raw, comp),
    )
    path = Path(log_path) if log_path else default_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(record.to_json() + "\n")
    except OSError:
        pass  # Telemetry must never break the caller.
    return record


def iter_records(log_path: Optional[Path] = None) -> Iterator[dict]:
    """Yield each JSON object from the savings log. Skips malformed lines."""
    path = Path(log_path) if log_path else default_log_path()
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
