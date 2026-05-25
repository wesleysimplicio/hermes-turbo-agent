"""Smoke tests for the Hyperframes video gen plugin."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from agent import video_gen_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    video_gen_registry._reset_for_tests()
    yield
    video_gen_registry._reset_for_tests()


def test_hyperframes_provider_registers():
    from plugins.video_gen.hyperframes import HyperframesVideoGenProvider, DEFAULT_MODEL

    provider = HyperframesVideoGenProvider()
    video_gen_registry.register_provider(provider)

    assert video_gen_registry.get_provider("hyperframes") is provider
    assert provider.display_name == "Hyperframes"
    assert provider.default_model() == DEFAULT_MODEL


def test_hyperframes_missing_composition_is_clear_error():
    from plugins.video_gen.hyperframes import HyperframesVideoGenProvider

    result = HyperframesVideoGenProvider().generate("institutional video")
    assert result["success"] is False
    assert result["error_type"] == "missing_composition"


def test_hyperframes_renders_with_cli(monkeypatch, tmp_path):
    import plugins.video_gen.hyperframes as hyperframes_plugin

    comp = tmp_path / "index.html"
    comp.write_text("<html><body data-composition-id='test'></body></html>")

    calls = []

    def fake_run(cmd, cwd, capture_output, text, timeout, check, env):
        calls.append({"cmd": cmd, "cwd": cwd})

        class R:
            returncode = 0
            stdout = json.dumps({"ok": True})
            stderr = ""

        return R()

    monkeypatch.setattr(hyperframes_plugin.subprocess, "run", fake_run)
    monkeypatch.setattr(hyperframes_plugin, "which", lambda _name: "/usr/bin/npx")

    result = hyperframes_plugin.HyperframesVideoGenProvider().generate(
        "institutional video",
        composition_path=str(comp),
    )

    assert result["success"] is True
    assert result["provider"] == "hyperframes"
    assert result["video"] == str(comp.parent / "renders" / "index.mp4")
    assert len(calls) == 3
    assert calls[0]["cmd"][2:4] == ["hyperframes", "lint"]
    assert calls[1]["cmd"][2:4] == ["hyperframes", "validate"]
    assert calls[2]["cmd"][2:4] == ["hyperframes", "render"]
