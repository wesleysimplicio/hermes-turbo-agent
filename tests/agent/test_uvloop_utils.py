import sys
import types

from agent import uvloop_utils


def test_install_uvloop_policy_uses_available_uvloop(monkeypatch):
    installed = []

    class FakePolicy:
        pass

    fake_uvloop = types.SimpleNamespace(EventLoopPolicy=FakePolicy)
    monkeypatch.setitem(sys.modules, "uvloop", fake_uvloop)
    monkeypatch.setattr(uvloop_utils.asyncio, "get_event_loop_policy", lambda: object())
    monkeypatch.setattr(
        uvloop_utils.asyncio,
        "set_event_loop_policy",
        lambda policy: installed.append(policy),
    )
    monkeypatch.setattr(uvloop_utils, "_INSTALLED", False)
    monkeypatch.delenv("HERMES_DISABLE_UVLOOP", raising=False)

    assert uvloop_utils.install_uvloop_policy() is True
    assert isinstance(installed[0], FakePolicy)


def test_install_uvloop_policy_respects_disable_env(monkeypatch):
    monkeypatch.setenv("HERMES_DISABLE_UVLOOP", "1")
    monkeypatch.setattr(uvloop_utils, "_INSTALLED", False)

    assert uvloop_utils.install_uvloop_policy() is False
