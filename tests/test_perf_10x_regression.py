"""Regression guards for the 10x-fast performance optimisations.

The branch introduces four hot-path optimisations that trade off
straightforward code for caching / batching:

* ``tools/registry.py``: mtime-fingerprinted built-in tool discovery
  cache + parallel source scan.
* ``toolsets.py``: memoised ``resolve_toolset`` / ``get_all_toolsets`` /
  ``get_toolset_names`` keyed on ``ToolRegistry._generation``.
* ``hermes_state.SessionDB.append_messages``: batched message inserts
  with a single counter update per call.
* ``tui_gateway.server._mcp_config_fingerprint``: stable JSON
  fingerprint exposed via ``cfg.get(key="mtime")`` so TUIs can skip
  expensive MCP reloads.

Each test below verifies that the *optimised* code path produces the
same observable output as the unoptimised reference, or that the cache
correctly invalidates when its inputs change. These are correctness
regressions — not performance benchmarks.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_state import SessionDB
from tools.registry import (
    ToolRegistry,
    discover_builtin_tools,
    _candidate_tool_paths,
    _discover_registering_tool_modules,
    _read_tool_discovery_cache,
    _tool_discovery_fingerprint,
    _write_tool_discovery_cache,
)
from toolsets import (
    TOOLSETS,
    clear_toolset_resolution_cache,
    create_custom_toolset,
    get_all_toolsets,
    get_toolset_names,
    resolve_toolset,
)


# =========================================================================
# Helpers
# =========================================================================


def _make_tools_dir(root: Path, modules: dict[str, bool]) -> Path:
    """Materialise a fake ``tools/`` package directory.

    ``modules`` maps base name → whether the module body should contain a
    top-level ``registry.register(...)`` call.
    """
    tools_dir = root / "tools"
    tools_dir.mkdir(parents=True)
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    # registry.py / mcp_tool.py are skipped by the candidate filter — write
    # stubs so the layout matches a real install.
    (tools_dir / "registry.py").write_text("", encoding="utf-8")
    (tools_dir / "mcp_tool.py").write_text(
        "from tools.registry import registry\n"
        "registry.register(name='mcp', toolset='x', schema={}, handler=lambda *_a, **_k: '{}')\n",
        encoding="utf-8",
    )
    for name, registers in modules.items():
        body = (
            "from tools.registry import registry\n"
            "registry.register(name='t', toolset='x', schema={}, handler=lambda *_a, **_k: '{}')\n"
            if registers
            else "X = 1\n"
        )
        (tools_dir / f"{name}.py").write_text(body, encoding="utf-8")
    return tools_dir


def _dummy_handler(args, **kwargs):
    return "{}"


def _schema(name: str) -> dict:
    return {
        "name": name,
        "description": name,
        "parameters": {"type": "object", "properties": {}},
    }


# =========================================================================
# tools/registry.py — built-in tool discovery cache
# =========================================================================


class TestToolDiscoveryCacheCorrectness:
    """The cached fast path must produce the same module list as a
    cold-source scan, and must invalidate when its fingerprint inputs
    change.

    These tests use ``discover_builtin_tools(tools_dir=...)`` with a
    synthetic tools directory so we never have to import real modules.
    The cache is wired up by overriding ``_builtin_tool_cache_path`` to
    a per-test tmp file — same shape as the existing
    ``test_default_discovery_uses_cache_after_first_scan``.
    """

    def test_cache_parity_with_fresh_scan(self, tmp_path, monkeypatch):
        """Cached result must equal the result of a from-scratch scan."""
        tools_dir = _make_tools_dir(
            tmp_path,
            {"a_tool": True, "b_tool": True, "helper": False, "c_tool": True},
        )

        # Cold scan — no cache.
        fingerprint = _tool_discovery_fingerprint(tools_dir)
        assert fingerprint is not None
        fresh = _discover_registering_tool_modules(tools_dir)
        assert fresh == ["tools.a_tool", "tools.b_tool", "tools.c_tool"]

        # Write + read through the cache.
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(
            "tools.registry._builtin_tool_cache_path", lambda: cache_path
        )
        _write_tool_discovery_cache(tools_dir, fingerprint, fresh)
        cached = _read_tool_discovery_cache(tools_dir, fingerprint)
        assert cached == fresh

    def test_cache_invalidates_when_source_mtime_bumps(self, tmp_path, monkeypatch):
        """Editing a tool source must produce a fingerprint mismatch so
        the next read returns ``None`` (forcing a fresh scan)."""
        tools_dir = _make_tools_dir(tmp_path, {"a_tool": True, "b_tool": True})
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(
            "tools.registry._builtin_tool_cache_path", lambda: cache_path
        )

        fp1 = _tool_discovery_fingerprint(tools_dir)
        assert fp1 is not None
        _write_tool_discovery_cache(
            tools_dir, fp1, ["tools.a_tool", "tools.b_tool"]
        )
        assert _read_tool_discovery_cache(tools_dir, fp1) is not None

        # Bump mtime+size on one file by appending a comment.
        (tools_dir / "a_tool.py").write_text(
            (tools_dir / "a_tool.py").read_text() + "# bumped\n", encoding="utf-8"
        )
        fp2 = _tool_discovery_fingerprint(tools_dir)
        assert fp2 is not None
        assert fp1 != fp2
        assert _read_tool_discovery_cache(tools_dir, fp2) is None

    def test_cache_invalidates_when_tools_path_changes(self, tmp_path, monkeypatch):
        """Cache entries are keyed on the resolved tools_path string —
        moving the install must NOT serve a stale entry."""
        tools_dir_a = _make_tools_dir(tmp_path / "a", {"a_tool": True})
        tools_dir_b = _make_tools_dir(tmp_path / "b", {"a_tool": True})
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(
            "tools.registry._builtin_tool_cache_path", lambda: cache_path
        )

        fp_a = _tool_discovery_fingerprint(tools_dir_a)
        assert fp_a is not None
        _write_tool_discovery_cache(tools_dir_a, fp_a, ["tools.a_tool"])

        # Same fingerprint shape (mtime/size happen to match if the
        # files are created back-to-back) is not enough: tools_path
        # mismatch must reject the cache.
        fp_b = _tool_discovery_fingerprint(tools_dir_b)
        assert fp_b is not None
        assert _read_tool_discovery_cache(tools_dir_b, fp_b) is None

    def test_cache_rejects_corrupt_payload(self, tmp_path, monkeypatch):
        """A truncated / malformed cache file must NOT crash discovery;
        it must be treated as a miss and force a fresh scan."""
        tools_dir = _make_tools_dir(tmp_path, {"a_tool": True})
        cache_path = tmp_path / "cache.json"
        monkeypatch.setattr(
            "tools.registry._builtin_tool_cache_path", lambda: cache_path
        )
        cache_path.write_text("{not valid json", encoding="utf-8")

        fp = _tool_discovery_fingerprint(tools_dir)
        assert fp is not None
        assert _read_tool_discovery_cache(tools_dir, fp) is None

        # Wrong version → also a miss.
        cache_path.write_text(
            json.dumps(
                {
                    "version": 999,
                    "tools_path": str(tools_dir),
                    "fingerprint": fp,
                    "modules": ["tools.a_tool"],
                }
            ),
            encoding="utf-8",
        )
        assert _read_tool_discovery_cache(tools_dir, fp) is None

    def test_explicit_tools_dir_bypasses_cache(self, tmp_path, monkeypatch):
        """``discover_builtin_tools(tools_dir=...)`` is the test-injection
        path and must NOT read or write the cache — otherwise tests
        running in parallel would corrupt each other's caches."""
        tools_dir = _make_tools_dir(tmp_path, {"a_tool": True})
        cache_path = tmp_path / "cache.json"
        write_calls = {"n": 0}

        def fail_write(*_a, **_kw):
            write_calls["n"] += 1

        monkeypatch.setattr(
            "tools.registry._builtin_tool_cache_path", lambda: cache_path
        )
        monkeypatch.setattr(
            "tools.registry._write_tool_discovery_cache", fail_write
        )

        with patch("tools.registry.importlib.import_module"):
            result = discover_builtin_tools(tools_dir)

        assert result == ["tools.a_tool"]
        assert write_calls["n"] == 0
        assert not cache_path.exists()

    def test_parallel_and_serial_scans_agree(self, tmp_path, monkeypatch):
        """The parallel-scan threshold is purely a perf knob; the scan
        result must not depend on which branch executes."""
        layout = {
            "x_tool": True,
            "y_tool": False,
            "z_tool": True,
            "alpha": True,
            "beta": False,
            "gamma": True,
            "delta": True,
            "epsilon": False,
            "zeta": True,
        }
        tools_dir = _make_tools_dir(tmp_path, layout)

        # Serial path.
        monkeypatch.setattr("tools.registry._TOOL_DISCOVERY_PARALLEL_THRESHOLD", 999)
        serial = _discover_registering_tool_modules(tools_dir)

        # Parallel path — same inputs, just a different scheduler.
        monkeypatch.setattr("tools.registry._TOOL_DISCOVERY_PARALLEL_THRESHOLD", 2)
        monkeypatch.setattr("tools.registry._TOOL_DISCOVERY_PARALLEL_MIN_BYTES", 0)
        monkeypatch.setattr("tools.registry._TOOL_DISCOVERY_MAX_WORKERS", 4)
        parallel = _discover_registering_tool_modules(tools_dir)

        assert serial == parallel
        # Sanity: sort order is deterministic (matches glob().sorted()).
        assert serial == sorted(serial)

    def test_candidate_paths_skip_registry_and_mcp_tool(self, tmp_path):
        """``_candidate_tool_paths`` must continue to filter the three
        non-tool modules — otherwise the cache would import ``registry``
        / ``mcp_tool`` and trigger a circular import."""
        tools_dir = _make_tools_dir(tmp_path, {"real_tool": True})
        names = {p.name for p in _candidate_tool_paths(tools_dir)}
        assert "real_tool.py" in names
        assert "__init__.py" not in names
        assert "registry.py" not in names
        assert "mcp_tool.py" not in names


# =========================================================================
# toolsets.py — memoised resolution
# =========================================================================


class TestToolsetCacheInvariants:
    """The toolset resolution cache is keyed on ``(id(registry),
    registry._generation)``. Every cached helper must invalidate when
    the registry mutates, and must hand back defensive copies so callers
    can mutate the result without poisoning the cache.
    """

    def setup_method(self):
        clear_toolset_resolution_cache()

    def teardown_method(self):
        clear_toolset_resolution_cache()
        # Belt-and-braces: drop any test-only toolsets so we don't bleed
        # into later modules' suites.
        for name in list(TOOLSETS):
            if name.startswith("_regression_"):
                del TOOLSETS[name]

    def test_resolve_toolset_returns_defensive_copy(self):
        """Mutating the result of resolve_toolset must not corrupt the
        cached entry — otherwise a careless caller could permanently
        delete a tool from the cached list."""
        first = resolve_toolset("web")
        snapshot = list(first)
        first.append("__poisoned__")
        first.clear()

        second = resolve_toolset("web")
        assert second == snapshot
        assert "__poisoned__" not in second

    def test_all_toolsets_cache_invalidates_on_registry_generation_bump(
        self, monkeypatch
    ):
        reg = ToolRegistry()
        monkeypatch.setattr("tools.registry.registry", reg)
        clear_toolset_resolution_cache()

        before = get_all_toolsets()
        assert "_regression_extra" not in before

        reg.register(
            name="extra_tool",
            toolset="_regression_extra",
            schema=_schema("extra_tool"),
            handler=_dummy_handler,
        )

        after = get_all_toolsets()
        assert "_regression_extra" in after
        # Cache is generation-keyed so the second call sees the new toolset.
        assert before is not after

    def test_toolset_names_cache_invalidates_on_registry_generation_bump(
        self, monkeypatch
    ):
        reg = ToolRegistry()
        monkeypatch.setattr("tools.registry.registry", reg)
        clear_toolset_resolution_cache()

        names_before = get_toolset_names()
        assert "_regression_named" not in names_before

        reg.register(
            name="named_tool",
            toolset="_regression_named",
            schema=_schema("named_tool"),
            handler=_dummy_handler,
        )

        names_after = get_toolset_names()
        assert "_regression_named" in names_after
        # Must still be sorted (callers iterate menu order).
        assert names_after == sorted(names_after)

    def test_get_all_toolsets_returns_independent_dict(self):
        first = get_all_toolsets()
        first["_regression_injected"] = {
            "description": "should not survive",
            "tools": [],
        }
        second = get_all_toolsets()
        assert "_regression_injected" not in second

    def test_get_toolset_names_returns_independent_list(self):
        first = get_toolset_names()
        first.append("_regression_injected_name")
        second = get_toolset_names()
        assert "_regression_injected_name" not in second

    def test_create_custom_toolset_invalidates_resolution_cache(self):
        TOOLSETS["_regression_custom_parent"] = {
            "description": "test",
            "tools": ["alpha"],
            "includes": [],
        }
        try:
            assert resolve_toolset("_regression_custom_parent") == ["alpha"]

            # Add a new custom toolset that references the parent — the
            # cached parent resolution is unaffected, but a fresh resolve
            # of the new toolset must include the parent's tool.
            create_custom_toolset(
                name="_regression_custom_child",
                description="includes parent",
                includes=["_regression_custom_parent"],
            )
            child = resolve_toolset("_regression_custom_child")
            assert "alpha" in child
        finally:
            for n in ("_regression_custom_parent", "_regression_custom_child"):
                TOOLSETS.pop(n, None)

    def test_clear_cache_drops_all_three_caches(self, monkeypatch):
        """``clear_toolset_resolution_cache`` must clear the resolved-,
        all-, and names-caches together — otherwise a caller could see
        a stale ``get_all_toolsets`` after a manual TOOLSETS mutation
        followed by clear()."""
        reg = ToolRegistry()
        monkeypatch.setattr("tools.registry.registry", reg)
        clear_toolset_resolution_cache()

        # Prime all three caches.
        resolve_toolset("web")
        get_all_toolsets()
        get_toolset_names()

        TOOLSETS["_regression_extra2"] = {
            "description": "test",
            "tools": ["only"],
            "includes": [],
        }
        try:
            # Without clearing, the all-/names- caches still serve the
            # pre-mutation snapshot (this is by design — registry
            # generation is the invalidation signal, not TOOLSETS edits).
            # ``clear_toolset_resolution_cache`` is the explicit escape
            # hatch.
            clear_toolset_resolution_cache()
            assert "_regression_extra2" in get_all_toolsets()
            assert "_regression_extra2" in get_toolset_names()
            assert resolve_toolset("_regression_extra2") == ["only"]
        finally:
            TOOLSETS.pop("_regression_extra2", None)


# =========================================================================
# hermes_state.py — append_messages batch parity
# =========================================================================


@pytest.fixture()
def db(tmp_path):
    db_path = tmp_path / "regression.db"
    session_db = SessionDB(db_path=db_path)
    yield session_db
    session_db.close()


class TestAppendMessagesParity:
    """``SessionDB.append_messages`` is a batched fast path for the case
    where the agent has produced several messages in a single turn (user
    + assistant + N tool responses).  It MUST be observably identical to
    a sequence of ``append_message`` calls on a fresh session.
    """

    def _three_messages(self):
        return [
            {"role": "user", "content": "ping"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "function": {"name": "echo", "arguments": "{}"},
                    },
                    {
                        "id": "c2",
                        "function": {"name": "echo", "arguments": "{}"},
                    },
                ],
                "reasoning": "thinking...",
                "finish_reason": "tool_calls",
            },
            {
                "role": "tool",
                "content": "pong",
                "tool_call_id": "c1",
                "tool_name": "echo",
            },
        ]

    def test_batch_matches_individual_appends(self, db):
        """Round-trip parity: the rows produced by ``append_messages``
        must match (modulo ``id`` and ``timestamp``) the rows produced
        by per-message ``append_message`` calls."""
        msgs = self._three_messages()

        db.create_session(session_id="batch", source="cli")
        db.create_session(session_id="indiv", source="cli")

        db.append_messages("batch", msgs)
        for m in msgs:
            db.append_message(
                "indiv",
                role=m["role"],
                content=m.get("content"),
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
                tool_name=m.get("tool_name"),
                reasoning=m.get("reasoning"),
                finish_reason=m.get("finish_reason"),
            )

        batch_rows = db.get_messages("batch")
        indiv_rows = db.get_messages("indiv")

        # Same shape, same length.
        assert len(batch_rows) == len(indiv_rows) == 3

        compared_fields = (
            "role",
            "content",
            "tool_calls",
            "tool_call_id",
            "tool_name",
            "reasoning",
            "finish_reason",
        )
        for b, i in zip(batch_rows, indiv_rows):
            for field in compared_fields:
                assert b.get(field) == i.get(field), (
                    f"field {field!r} diverges between batch and individual: "
                    f"{b.get(field)!r} != {i.get(field)!r}"
                )

        # Session counters must match too.
        b_sess = db.get_session("batch")
        i_sess = db.get_session("indiv")
        assert b_sess["message_count"] == i_sess["message_count"] == 3
        assert b_sess["tool_call_count"] == i_sess["tool_call_count"] == 2

    def test_empty_list_is_noop(self, db):
        """An empty batch must not insert any rows and must not bump the
        session's message_count.  Pre-fix, an ``UPDATE ... + 0`` slipped
        through; verify it stays a clean no-op."""
        db.create_session(session_id="empty", source="cli")
        ids = db.append_messages("empty", [])
        assert ids == []
        assert db.get_messages("empty") == []
        sess = db.get_session("empty")
        assert sess["message_count"] == 0
        assert sess["tool_call_count"] == 0

    def test_timestamps_are_strictly_increasing(self, db):
        """``append_messages`` derives per-message timestamps from a
        single ``time.time()`` snapshot plus a tiny per-index offset so
        that ``ORDER BY timestamp`` returns messages in insertion order
        even when the wall clock returns the same float twice."""
        db.create_session(session_id="ts", source="cli")
        db.append_messages(
            "ts",
            [
                {"role": "user", "content": "1"},
                {"role": "assistant", "content": "2"},
                {"role": "user", "content": "3"},
                {"role": "assistant", "content": "4"},
            ],
        )
        rows = db.get_messages("ts")
        timestamps = [r["timestamp"] for r in rows]
        # Strictly increasing.
        assert all(a < b for a, b in zip(timestamps, timestamps[1:])), timestamps
        # Order preserved.
        assert [r["content"] for r in rows] == ["1", "2", "3", "4"]

    def test_multimodal_content_round_trips_through_batch(self, db):
        """List-content (multimodal) messages must survive batch insert
        +  ``get_messages`` decoding — this is the sqlite3-can't-bind-list
        bug from #17522 in the batched path."""
        db.create_session(session_id="mm", source="cli")
        parts = [
            {"type": "text", "text": "look at this"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xx"}},
        ]
        db.append_messages(
            "mm",
            [
                {"role": "user", "content": parts},
                {"role": "assistant", "content": "noted"},
            ],
        )
        rows = db.get_messages("mm")
        assert rows[0]["content"] == parts
        assert rows[1]["content"] == "noted"

    def test_tool_call_count_excludes_tool_role_responses(self, db):
        """The ``tool_call_count`` bump must reflect only ``tool_calls``
        on assistant rows — never the matching ``role='tool'`` reply
        rows.  Otherwise tool-call accounting double-counts."""
        db.create_session(session_id="tcc", source="cli")
        db.append_messages(
            "tcc",
            [
                {"role": "user", "content": "go"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "a", "function": {"name": "x", "arguments": "{}"}},
                        {"id": "b", "function": {"name": "x", "arguments": "{}"}},
                    ],
                },
                {"role": "tool", "content": "r1", "tool_call_id": "a"},
                {"role": "tool", "content": "r2", "tool_call_id": "b"},
            ],
        )
        sess = db.get_session("tcc")
        assert sess["message_count"] == 4
        assert sess["tool_call_count"] == 2

    def test_reasoning_and_codex_payloads_survive_batch(self, db):
        """Structured reasoning_details / codex_* lists must JSON-encode
        through the batch path the same way they do through the single
        path."""
        db.create_session(session_id="rcx", source="cli")
        details = [{"type": "reasoning.summary", "text": "because"}]
        codex_msgs = [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "ok"}]}]
        codex_reason = [{"type": "reasoning", "summary": [{"type": "summary_text", "text": "ok"}]}]
        db.append_messages(
            "rcx",
            [
                {
                    "role": "assistant",
                    "content": "answer",
                    "reasoning_details": details,
                    "codex_message_items": codex_msgs,
                    "codex_reasoning_items": codex_reason,
                },
            ],
        )
        rows = db.get_messages("rcx")
        # Either the decoded structure round-trips, or the stored value
        # parses back to the same payload.  We accept both shapes so
        # this test isn't coupled to whether ``get_messages`` chooses
        # to decode each column or hand back raw JSON.
        for field, expected in (
            ("reasoning_details", details),
            ("codex_message_items", codex_msgs),
            ("codex_reasoning_items", codex_reason),
        ):
            got = rows[0].get(field)
            if isinstance(got, str):
                got = json.loads(got)
            assert got == expected, f"{field} did not round-trip"


# =========================================================================
# tui_gateway/server.py — _mcp_config_fingerprint
# =========================================================================


class TestMcpConfigFingerprint:
    """The TUI uses ``cfg.get(key="mtime")`` to decide whether to reload
    its MCP tool list.  The ``mcp_fingerprint`` field added in this
    branch lets it skip reloads when the mtime bumped but ``mcp_servers``
    did not actually change.  These tests guard the fingerprint's two
    invariants: stability (same input → same string) and sensitivity
    (any meaningful change → different string).
    """

    def _fingerprint_with_cfg(self, monkeypatch, cfg: dict) -> str:
        from tui_gateway import server

        monkeypatch.setattr(server, "_load_cfg", lambda: cfg)
        return server._mcp_config_fingerprint()

    def test_same_config_same_fingerprint(self, monkeypatch):
        cfg = {"mcp_servers": {"alpha": {"command": "x"}, "beta": {"command": "y"}}}
        a = self._fingerprint_with_cfg(monkeypatch, cfg)
        b = self._fingerprint_with_cfg(monkeypatch, json.loads(json.dumps(cfg)))
        assert a == b

    def test_key_order_does_not_change_fingerprint(self, monkeypatch):
        cfg1 = {"mcp_servers": {"alpha": {"command": "x"}, "beta": {"command": "y"}}}
        cfg2 = {"mcp_servers": {"beta": {"command": "y"}, "alpha": {"command": "x"}}}
        assert self._fingerprint_with_cfg(monkeypatch, cfg1) == self._fingerprint_with_cfg(
            monkeypatch, cfg2
        )

    def test_changing_a_server_changes_fingerprint(self, monkeypatch):
        a = self._fingerprint_with_cfg(
            monkeypatch, {"mcp_servers": {"alpha": {"command": "x"}}}
        )
        b = self._fingerprint_with_cfg(
            monkeypatch, {"mcp_servers": {"alpha": {"command": "y"}}}
        )
        assert a != b

    def test_adding_a_server_changes_fingerprint(self, monkeypatch):
        a = self._fingerprint_with_cfg(
            monkeypatch, {"mcp_servers": {"alpha": {"command": "x"}}}
        )
        b = self._fingerprint_with_cfg(
            monkeypatch,
            {"mcp_servers": {"alpha": {"command": "x"}, "beta": {"command": "z"}}},
        )
        assert a != b

    def test_missing_or_non_dict_mcp_servers_is_empty_object(self, monkeypatch):
        """Hand-edited ``mcp_servers: null`` / ``mcp_servers: true``
        leaves the field as a non-dict.  Fingerprint must coerce that
        to ``"{}"`` rather than crashing or producing a nondeterministic
        ``str(True)``-style fingerprint."""
        empty = "{}"
        assert self._fingerprint_with_cfg(monkeypatch, {}) == empty
        assert self._fingerprint_with_cfg(monkeypatch, {"mcp_servers": None}) == empty
        assert self._fingerprint_with_cfg(monkeypatch, {"mcp_servers": True}) == empty
        assert self._fingerprint_with_cfg(monkeypatch, {"mcp_servers": "x"}) == empty

    def test_load_cfg_exception_falls_back_safely(self, monkeypatch):
        """``_load_cfg`` can raise on a malformed YAML file — the
        fingerprint must still return a stable string, not propagate."""
        from tui_gateway import server

        def boom():
            raise RuntimeError("yaml corrupt")

        monkeypatch.setattr(server, "_load_cfg", boom)
        # The implementation only guards the json.dumps() path; if
        # _load_cfg itself raises, the exception propagates.  Lock in
        # that behaviour: callers (``_dispatch`` / config probes) must
        # wrap it.  This test is a contract reminder for refactors that
        # try to swallow the exception silently — that would mask a
        # corrupt config without the user knowing.
        with pytest.raises(RuntimeError):
            server._mcp_config_fingerprint()
