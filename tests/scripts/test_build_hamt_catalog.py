"""Tests for the HAMT catalog builder (#102)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_hamt_catalog.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_hamt_catalog", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_hamt_catalog"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


SAMPLE = """
### My Agent

- yool_id: `agent.dev.python`
- authority: dev | ops | review | audit
- lane: fast | slow | background
- agent_terms:
    cpu_quota_pct: 60
    disk_quota_mb: 100
    timeout_s: 300

### Other Agent

- yool_id: `agent.ops.shell`
- authority: ops
- lane: background
- agent_terms:
    cpu_quota_pct: 40
    disk_quota_mb: 50
    timeout_s: 120

### Bad Agent

- yool_id: `agent.dev.bad`
- authority: dev
- lane: fast
"""


def test_constants_match_spec(mod) -> None:
    assert mod.BITS_PER_LEVEL == 5
    assert mod.BRANCH == 32
    assert mod.MAX_LEVELS == 6
    assert mod.HASH_BITS == 30


def test_hash_in_range(mod) -> None:
    h = mod.hash30("agent.dev.python")
    assert 0 <= h < (1 << 30)


def test_parse_skips_missing_guardrails(mod, capsys: pytest.CaptureFixture[str]) -> None:
    caps = mod.parse_capabilities(SAMPLE)
    ids = {c["yool_id"] for c in caps}
    assert ids == {"agent.dev.python", "agent.ops.shell"}
    # Bad agent skipped with warning.
    captured = capsys.readouterr()
    assert "agent.dev.bad" in captured.err


def test_build_and_lookup(mod) -> None:
    caps = mod.parse_capabilities(SAMPLE)
    catalog = mod.build_catalog(caps)
    assert catalog["count"] == 2
    assert catalog["branch_factor"] == 32
    assert catalog["hash_bits"] == 30
    found = mod.lookup_catalog(catalog, "agent.dev.python")
    assert found is not None
    assert found["agent_terms"]["cpu_quota_pct"] == 60
    assert mod.lookup_catalog(catalog, "agent.missing") is None


def test_list_returns_sorted_ids(mod) -> None:
    caps = mod.parse_capabilities(SAMPLE)
    catalog = mod.build_catalog(caps)
    assert mod.list_catalog(catalog) == ["agent.dev.python", "agent.ops.shell"]


def test_main_writes_catalog(mod, tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(SAMPLE, encoding="utf-8")
    out = tmp_path / "out" / "hamt.json"
    rc = mod.main(["--agents", str(agents), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    import json
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["count"] == 2
    assert payload["branch_factor"] == 32
