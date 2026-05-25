"""Append-only receipts (P7), inspired by ``llm-project-mapper`` `.receipts/`.

A receipt records one logical agent action: yool id, content hash of the
input, status, cost in tokens, optional reference to a token-saving event.
Receipts are content-addressable (sha256 of the canonical input blob), so
duplicate work can short-circuit by looking up the hash before re-executing.

Schema (JSON file at ``<dir>/<sha>.json``):

    {
      "sha":     "<sha256 hex>",
      "yool_id": "agent.<authority>.<slug>",
      "lane":    "fast|slow|background",
      "status":  "ok|error|skipped|cached",
      "cost":    {"tokens": int, "tokens_raw": int, "tokens_saved": int},
      "ts":      "<utc iso8601>",
      "meta":    {<free-form>}
    }

The ledger in ``token_savings.py`` remains the time-series log; receipts are
the content-addressed index. Both can coexist; ``record_receipt`` does not
delete or rotate existing rows in either store.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

_DIR_ENV = "HERMES_RECEIPTS_DIR"
_DEFAULT_REL = Path(".receipts")


def default_receipts_dir(root: Optional[str | Path] = None) -> Path:
    """Resolve the receipts directory (env override or ``<root>/.receipts``)."""

    override = os.environ.get(_DIR_ENV)
    if override:
        return Path(override).expanduser()
    base = Path(root).expanduser() if root else Path.cwd()
    return base / _DEFAULT_REL


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def content_hash(payload: str | bytes) -> str:
    """Return the canonical hex digest of ``payload``.

    Uses BLAKE2b at 32-byte digest length — same security level as sha256
    but faster on Python's stdlib implementation (blake2b is SIMD-friendly
    on most platforms). Hex output stays 64 chars so on-disk schema is
    unchanged.
    """

    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.blake2b(payload, digest_size=32).hexdigest()


@dataclass(frozen=True)
class Cost:
    tokens: int = 0
    tokens_raw: int = 0
    tokens_saved: int = 0


@dataclass(frozen=True)
class Receipt:
    sha: str
    yool_id: str = "unknown"
    lane: str = "fast"
    status: str = "ok"
    cost: Cost = field(default_factory=Cost)
    ts: str = field(default_factory=_utc_now)
    meta: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["meta"] = dict(self.meta)
        return data


def receipt_path(sha: str, directory: Optional[Path] = None) -> Path:
    """Return the on-disk path for receipt ``sha``."""

    base = directory or default_receipts_dir()
    return base / f"{sha}.json"


def record_receipt(
    *,
    payload: str | bytes,
    yool_id: str = "unknown",
    lane: str = "fast",
    status: str = "ok",
    tokens: int = 0,
    tokens_raw: int = 0,
    tokens_saved: int = 0,
    meta: Optional[Mapping[str, Any]] = None,
    directory: Optional[Path] = None,
) -> Receipt:
    """Compute the content hash of ``payload`` and persist a receipt.

    Append-only: if a receipt with the same sha already exists, the file is
    left untouched and the existing receipt is returned. This is what makes
    receipts cache-friendly — the second call with the same payload is a
    no-op.
    """

    sha = content_hash(payload)
    base = directory or default_receipts_dir()
    target = base / f"{sha}.json"

    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            cost = data.get("cost", {}) or {}
            return Receipt(
                sha=data.get("sha", sha),
                yool_id=data.get("yool_id", yool_id),
                lane=data.get("lane", lane),
                status=data.get("status", status),
                cost=Cost(
                    tokens=int(cost.get("tokens", 0)),
                    tokens_raw=int(cost.get("tokens_raw", 0)),
                    tokens_saved=int(cost.get("tokens_saved", 0)),
                ),
                ts=data.get("ts", _utc_now()),
                meta=data.get("meta", {}) or {},
            )
        except (OSError, json.JSONDecodeError):
            pass  # corrupt — fall through and overwrite below

    receipt = Receipt(
        sha=sha,
        yool_id=yool_id,
        lane=lane,
        status=status,
        cost=Cost(tokens=tokens, tokens_raw=tokens_raw, tokens_saved=tokens_saved),
        meta=dict(meta or {}),
    )

    try:
        base.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(receipt.to_dict(), separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # silent like token_savings: telemetry must never break the agent
        pass

    return receipt


def lookup_receipt(
    payload: str | bytes, directory: Optional[Path] = None
) -> Optional[Receipt]:
    """Return a previously-recorded receipt for ``payload``, or ``None``."""

    sha = content_hash(payload)
    target = (directory or default_receipts_dir()) / f"{sha}.json"
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    cost = data.get("cost", {}) or {}
    return Receipt(
        sha=data.get("sha", sha),
        yool_id=data.get("yool_id", "unknown"),
        lane=data.get("lane", "fast"),
        status=data.get("status", "ok"),
        cost=Cost(
            tokens=int(cost.get("tokens", 0)),
            tokens_raw=int(cost.get("tokens_raw", 0)),
            tokens_saved=int(cost.get("tokens_saved", 0)),
        ),
        ts=data.get("ts", _utc_now()),
        meta=data.get("meta", {}) or {},
    )
