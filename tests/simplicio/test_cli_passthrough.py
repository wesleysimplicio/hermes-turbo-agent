"""Tests for the ``hermes simplicio`` passthrough wrapper.

No network and no real lazy installs: the embedding ``ensure`` hook is
monkeypatched, and the only command actually forwarded (``smoke``) fails fast
on the missing model/key before any SDK call.
"""

import sys

import pytest

from hermes_cli import simplicio_cmd
import tools.lazy_deps as lazy_deps


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("SIMPLICIO_MODEL", "SIMPLICIO_BASE_URL", "SIMPLICIO_API_KEY",
              "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)


def test_lazy_dep_feature_registered():
    specs = lazy_deps.LAZY_DEPS["simplicio.embeddings"]
    assert any(s.startswith("sentence-transformers") for s in specs)
    assert any(s.startswith("numpy") for s in specs)


def test_maybe_ensure_called_for_embedding_subcommands(monkeypatch):
    calls = []
    monkeypatch.setattr(lazy_deps, "ensure", lambda feature, **kw: calls.append(feature))
    for sub in ("index", "task", "bench"):
        simplicio_cmd._maybe_ensure_embeddings([sub, "--root", "."])
    assert calls == ["simplicio.embeddings"] * 3


def test_maybe_ensure_skipped_for_non_embedding(monkeypatch):
    calls = []
    monkeypatch.setattr(lazy_deps, "ensure", lambda feature, **kw: calls.append(feature))
    # Plain non-embedding subcommands, and help requests even on embedding
    # subcommands, must not trigger an install.
    for args in (["smoke"], ["--help"], [], ["-h"], ["task", "-h"], ["index", "--help"]):
        simplicio_cmd._maybe_ensure_embeddings(args)
    assert calls == []


def test_maybe_ensure_swallows_feature_unavailable(monkeypatch, capsys):
    def boom(feature, **kw):
        raise lazy_deps.FeatureUnavailable(feature, ("numpy>=1.23",), "offline")

    monkeypatch.setattr(lazy_deps, "ensure", boom)
    # Must not raise — the user still gets a hint and delegation proceeds.
    simplicio_cmd._maybe_ensure_embeddings(["task"])
    assert "simplicio" in capsys.readouterr().err.lower()


def test_run_simplicio_smoke_returns_nonzero_without_model(capsys):
    rc = simplicio_cmd.run_simplicio(["smoke"])
    assert rc == 1
    assert "SIMPLICIO_MODEL" in capsys.readouterr().err


def test_run_simplicio_help_returns_zero():
    assert simplicio_cmd.run_simplicio(["--help"]) == 0


def test_run_simplicio_restores_argv():
    sentinel = ["original", "argv"]
    saved = sys.argv
    sys.argv = list(sentinel)
    try:
        simplicio_cmd.run_simplicio(["smoke"])
        assert sys.argv == sentinel
    finally:
        sys.argv = saved
