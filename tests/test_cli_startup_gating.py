"""Tests for the agent-side-effects subcommand gating in ``hermes_cli/main.py``.

Closes Copilot review on PR #61: bootstrap + auto-mapper must NOT run for
cheap utility subcommands (``hermes --help``, ``hermes config``, etc.).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_gating():
    """Load the gating function out of ``hermes_cli/main.py`` without running its top-level side effects."""
    src = (REPO_ROOT / "hermes_cli" / "main.py").read_text()
    # The function and its constants are above any expensive imports.
    namespace: dict = {"os": __import__("os"), "sys": __import__("sys")}
    # Grab the function definition + the _AGENT_SUBCOMMANDS / _CHEAP_SUBCOMMANDS constants.
    start = src.index("_AGENT_SUBCOMMANDS = frozenset")
    end = src.index("if _should_run_agent_side_effects():")
    exec(src[start:end], namespace)
    return namespace["_should_run_agent_side_effects"]


@pytest.fixture
def gating(monkeypatch):
    func = _load_gating()

    def _set_argv(args):
        monkeypatch.setattr(sys, "argv", ["hermes"] + list(args))
        return func()

    return _set_argv


def test_bare_command_runs_hooks(gating):
    assert gating([]) is True


def test_help_skips_hooks(gating):
    assert gating(["--help"]) is False
    assert gating(["-h"]) is False
    assert gating(["help"]) is False


def test_version_skips_hooks(gating):
    assert gating(["--version"]) is False
    assert gating(["version"]) is False


def test_cheap_utilities_skip_hooks(gating):
    for cmd in ("config", "status", "doctor", "logout", "update", "tools", "skills"):
        assert gating([cmd]) is False, f"Expected {cmd} to skip hooks"


def test_agent_subcommands_run_hooks(gating):
    for cmd in ("chat", "gateway", "cron", "acp", "kanban", "send"):
        assert gating([cmd]) is True, f"Expected {cmd} to run hooks"


def test_explicit_disable_overrides_subcommand(gating, monkeypatch):
    monkeypatch.setenv("HERMES_TURBO_SKIP_STARTUP_HOOKS", "1")
    assert gating(["chat"]) is False
    assert gating([]) is False


def test_unknown_subcommand_defaults_to_run(gating):
    # New / unrecognised subcommands default to running hooks rather than
    # silently skipping them on a new addition.
    assert gating(["whatever-new"]) is True
