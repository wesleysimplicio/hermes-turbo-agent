"""Smoke tests for the WaveSpeedAI video gen plugin."""

from __future__ import annotations

import json
import subprocess

import pytest

from agent import video_gen_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    video_gen_registry._reset_for_tests()
    yield
    video_gen_registry._reset_for_tests()


def test_wavespeed_provider_registers():
    from plugins.video_gen.wavespeed import WaveSpeedVideoGenProvider, DEFAULT_MODEL

    provider = WaveSpeedVideoGenProvider()
    video_gen_registry.register_provider(provider)

    assert video_gen_registry.get_provider("wavespeed") is provider
    assert provider.display_name == "WaveSpeedAI"
    assert provider.default_model() == DEFAULT_MODEL


def test_wavespeed_unavailable_without_key(monkeypatch):
    from plugins.video_gen.wavespeed import WaveSpeedVideoGenProvider

    monkeypatch.delenv("WAVESPEED_API_KEY", raising=False)
    monkeypatch.setattr("plugins.video_gen.wavespeed._which", lambda _name: "/usr/bin/wavespeed-cli")
    assert WaveSpeedVideoGenProvider().is_available() is False


def test_wavespeed_generate_shells_out_and_parses_json(monkeypatch):
    import plugins.video_gen.wavespeed as wavespeed_plugin

    monkeypatch.setenv("WAVESPEED_API_KEY", "ws-test")
    monkeypatch.setattr(wavespeed_plugin, "_which", lambda _name: "/usr/bin/wavespeed-cli")

    calls = {}

    def fake_run(cmd, capture_output, text, timeout, check, env, cwd=None):
        calls["cmd"] = cmd
        calls["env_key"] = env.get("WAVESPEED_API_KEY")
        calls["cwd"] = cwd

        class R:
            returncode = 0
            stdout = json.dumps({"video": {"url": "https://example.com/video.mp4"}})
            stderr = ""

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = wavespeed_plugin.WaveSpeedVideoGenProvider().generate(
        "animate this",
        image_url="https://example.com/image.png",
        model="wavespeed-ai/seedance-v2",
    )

    assert result["success"] is True
    assert result["provider"] == "wavespeed"
    assert result["video"] == "https://example.com/video.mp4"
    assert calls["cmd"][0].endswith("wavespeed-cli")
    assert calls["cmd"][1:3] == ["run", "wavespeed-ai/seedance-v2"]
    payload = json.loads(calls["cmd"][3])
    assert payload["image"] == "https://example.com/image.png"
    assert calls["env_key"] == "ws-test"
