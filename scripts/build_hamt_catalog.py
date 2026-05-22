#!/usr/bin/env python3
"""Build a HAMT catalog of yool capabilities from AGENTS.md (issue #102).

Spec: https://github.com/wesleysimplicio/yool-tuple-hamt v0.2.
Constants (Bagwell 2001):
    BITS_PER_LEVEL = 5
    BRANCH         = 32
    MAX_LEVELS     = 6
    HASH_BITS      = 30
    hash           = blake2b truncated to 30 bits

The script scans ``AGENTS.md`` for capability blocks of the form::

    - yool_id: `agent.dev.python`
    - authority: dev | ops | review | audit
    - lane: fast | slow | background
    - agent_terms:
        cpu_quota_pct: 60
        disk_quota_mb: 100
        timeout_s: 300

and emits ``.catalog/hamt.json``. Mandatory guardrails (cpu_quota_pct,
disk_quota_mb) MUST be present per spec §11.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

BITS_PER_LEVEL = 5
BRANCH = 1 << BITS_PER_LEVEL  # 32
MAX_LEVELS = 6
HASH_BITS = BITS_PER_LEVEL * MAX_LEVELS  # 30
HASH_MASK = (1 << HASH_BITS) - 1

_YOOL_ID_RE = re.compile(r"yool_id:\s*`([a-z0-9._-]+)`", re.IGNORECASE)
_AUTHORITY_RE = re.compile(r"authority:\s*([a-z|\s]+)", re.IGNORECASE)
_LANE_RE = re.compile(r"lane:\s*([a-z|\s]+)", re.IGNORECASE)
_CPU_RE = re.compile(r"cpu_quota_pct:\s*(\d+)")
_DISK_RE = re.compile(r"disk_quota_mb:\s*(\d+)")
_TIMEOUT_RE = re.compile(r"timeout_s:\s*(\d+)")


def hash30(key: str) -> int:
    """Return a 30-bit unsigned hash of ``key``."""
    digest = hashlib.blake2b(key.encode("utf-8", "replace"), digest_size=8).digest()
    n = int.from_bytes(digest, "big")
    return n & HASH_MASK


def _slice(h: int, level: int) -> int:
    shift = level * BITS_PER_LEVEL
    return (h >> shift) & (BRANCH - 1)


def _new_node() -> Dict[str, Any]:
    return {"type": "internal", "children": {}}


def _insert(root: Dict[str, Any], key: str, value: Dict[str, Any]) -> None:
    h = hash30(key)
    node = root
    for level in range(MAX_LEVELS):
        idx = _slice(h, level)
        slot = node["children"].get(str(idx))
        if slot is None:
            node["children"][str(idx)] = {"type": "leaf", "key": key, "value": value, "hash": h}
            return
        if slot["type"] == "leaf":
            if slot["key"] == key:
                slot["value"] = value
                return
            if level == MAX_LEVELS - 1:
                # Collision at final level — degenerate bucket.
                bucket = slot.setdefault("bucket", [{"key": slot["key"], "value": slot["value"]}])
                bucket.append({"key": key, "value": value})
                slot["type"] = "bucket"
                return
            existing = slot
            replacement = _new_node()
            node["children"][str(idx)] = replacement
            other_idx = _slice(existing["hash"], level + 1)
            replacement["children"][str(other_idx)] = existing
            node = replacement
            continue
        if slot["type"] == "bucket":
            slot["bucket"].append({"key": key, "value": value})
            return
        node = slot
    raise RuntimeError("HAMT insert exceeded MAX_LEVELS")  # pragma: no cover


def _lookup(root: Dict[str, Any], key: str) -> Dict[str, Any] | None:
    h = hash30(key)
    node = root
    for level in range(MAX_LEVELS):
        idx = _slice(h, level)
        slot = node["children"].get(str(idx))
        if slot is None:
            return None
        if slot["type"] == "leaf":
            return slot["value"] if slot["key"] == key else None
        if slot["type"] == "bucket":
            for entry in slot["bucket"]:
                if entry["key"] == key:
                    return entry["value"]
            return None
        node = slot
    return None


def parse_capabilities(text: str) -> List[Dict[str, Any]]:
    """Pull capability blocks from AGENTS.md."""
    capabilities: List[Dict[str, Any]] = []
    # Scan in sliding windows: every yool_id introduces a block; we read
    # until the next yool_id or end of file.
    matches = list(_YOOL_ID_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        yool_id = m.group(1)
        authority = _first(_AUTHORITY_RE, chunk) or "dev"
        lane = _first(_LANE_RE, chunk) or "slow"
        cpu = _first_int(_CPU_RE, chunk)
        disk = _first_int(_DISK_RE, chunk)
        timeout = _first_int(_TIMEOUT_RE, chunk) or 300
        if cpu is None or disk is None:
            # Mandatory guardrails missing — spec §11. Skip with a warning.
            print(
                f"warning: capability {yool_id!r} missing mandatory cpu_quota_pct/disk_quota_mb; skipped",
                file=sys.stderr,
            )
            continue
        capabilities.append({
            "yool_id": yool_id,
            "authority": _take_first(authority),
            "lane": _take_first(lane),
            "agent_terms": {
                "cpu_quota_pct": cpu,
                "disk_quota_mb": disk,
                "timeout_s": timeout,
            },
        })
    return capabilities


def _first(pattern: re.Pattern[str], chunk: str) -> str | None:
    m = pattern.search(chunk)
    return m.group(1).strip() if m else None


def _first_int(pattern: re.Pattern[str], chunk: str) -> int | None:
    m = pattern.search(chunk)
    return int(m.group(1)) if m else None


def _take_first(value: str) -> str:
    # "dev | ops | review | audit" -> "dev"
    return value.split("|")[0].strip()


def build_catalog(capabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    root = _new_node()
    for cap in capabilities:
        _insert(root, cap["yool_id"], cap)
    return {
        "spec_version": "0.2",
        "branch_factor": BRANCH,
        "hash_bits": HASH_BITS,
        "count": len(capabilities),
        "root": root,
    }


def lookup_catalog(catalog: Dict[str, Any], yool_id: str) -> Dict[str, Any] | None:
    return _lookup(catalog["root"], yool_id)


def list_catalog(catalog: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    _walk(catalog["root"], out)
    return sorted(out)


def _walk(node: Dict[str, Any], out: List[str]) -> None:
    for child in node.get("children", {}).values():
        kind = child["type"]
        if kind == "leaf":
            out.append(child["key"])
        elif kind == "bucket":
            out.extend(e["key"] for e in child["bucket"])
        else:
            _walk(child, out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build-hamt-catalog", description=__doc__)
    parser.add_argument("--agents", type=Path, default=Path("AGENTS.md"))
    parser.add_argument("--out", type=Path, default=Path(".catalog") / "hamt.json")
    parser.add_argument("--print-list", action="store_true", help="Print discovered yool ids and exit.")
    args = parser.parse_args(argv)

    if not args.agents.exists():
        print(f"error: AGENTS.md not found at {args.agents}", file=sys.stderr)
        return 2
    text = args.agents.read_text(encoding="utf-8")
    capabilities = parse_capabilities(text)
    catalog = build_catalog(capabilities)

    if args.print_list:
        for yid in list_catalog(catalog):
            print(yid)
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(capabilities)} capabilities to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
