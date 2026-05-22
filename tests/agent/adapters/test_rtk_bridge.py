"""Unit tests for the RTK compatibility bridge."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.adapters import rtk_bridge  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv(rtk_bridge.ENV_BACKEND, raising=False)


def _which(value):
    return lambda name: value if name == "rtk" else None


def test_is_rtk_available_true(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which("/usr/local/bin/rtk"))
    assert rtk_bridge.is_rtk_available() is True


def test_is_rtk_available_false(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which(None))
    assert rtk_bridge.is_rtk_available() is False


def test_resolve_backend_default_and_env(monkeypatch):
    assert rtk_bridge.resolve_backend() == rtk_bridge.BACKEND_AUTO
    monkeypatch.setenv(rtk_bridge.ENV_BACKEND, "native")
    assert rtk_bridge.resolve_backend() == rtk_bridge.BACKEND_NATIVE
    assert rtk_bridge.resolve_backend("rtk") == rtk_bridge.BACKEND_RTK
    assert rtk_bridge.resolve_backend("garbage") == rtk_bridge.BACKEND_AUTO


def test_wrap_native_passthrough(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which("/usr/local/bin/rtk"))
    assert rtk_bridge.wrap_command(["git", "status"], backend="native") == ["git", "status"]


def test_wrap_rtk_available(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which("/usr/local/bin/rtk"))
    assert rtk_bridge.wrap_command(["git", "status"], backend="rtk") == ["rtk", "git", "status"]


def test_wrap_rtk_missing_raises(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which(None))
    with pytest.raises(rtk_bridge.RtkNotInstalledError):
        rtk_bridge.wrap_command(["git", "status"], backend="rtk")


def test_wrap_auto_compatible(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which("/usr/local/bin/rtk"))
    assert rtk_bridge.wrap_command(["git", "log"], backend="auto") == ["rtk", "git", "log"]


def test_wrap_auto_skips_incompatible(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which("/usr/local/bin/rtk"))
    assert rtk_bridge.wrap_command(["psql", "-c", "select 1"], backend="auto") == ["psql", "-c", "select 1"]


def test_wrap_auto_no_rtk(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which(None))
    assert rtk_bridge.wrap_command(["grep", "x", "f"], backend="auto") == ["grep", "x", "f"]


def test_wrap_empty_argv():
    assert rtk_bridge.wrap_command([], backend="rtk") == []


def test_describe(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which("/opt/rtk/rtk"))
    info = rtk_bridge.describe()
    assert info == {
        "backend": "auto",
        "rtk_available": True,
        "rtk_path": "/opt/rtk/rtk",
        "effective": "rtk",
    }


def test_describe_native_fallback(monkeypatch):
    monkeypatch.setattr(rtk_bridge.shutil, "which", _which(None))
    info = rtk_bridge.describe()
    assert info["rtk_available"] is False
    assert info["effective"] == "native"


def test_iter_compatible_sorted():
    cmds = list(rtk_bridge.iter_compatible_commands())
    assert cmds == sorted(cmds)
    assert "git" in cmds
