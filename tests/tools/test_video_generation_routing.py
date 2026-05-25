"""Routing tests for the unified video_generate tool."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pytest

from agent import video_gen_registry
from agent.video_gen_provider import VideoGenProvider


@pytest.fixture(autouse=True)
def _reset_registry():
    video_gen_registry._reset_for_tests()
    yield
    video_gen_registry._reset_for_tests()


class _RecordingProvider(VideoGenProvider):
    def __init__(self, name: str):
        self._name = name
        self.last_kwargs: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    def default_model(self) -> Optional[str]:
        return f"{self._name}-model"

    def generate(self, prompt, **kwargs):
        self.last_kwargs = {"prompt": prompt, **kwargs}
        return {"success": True, "provider": self._name, "video": f"{self._name}.mp4", "model": kwargs.get("model", self.default_model()), "prompt": prompt, "modality": "image" if kwargs.get("image_url") else "text", "aspect_ratio": kwargs.get("aspect_ratio", ""), "duration": kwargs.get("duration") or 0}


class TestVideoRouting:
    def _run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from tools import video_generation_tool
        import hermes_cli.plugins as plugins_module

        saved_discover = plugins_module._ensure_plugins_discovered
        plugins_module._ensure_plugins_discovered = lambda *_a, **_k: None  # type: ignore
        try:
            raw = video_generation_tool._handle_video_generate(args)
        finally:
            plugins_module._ensure_plugins_discovered = saved_discover  # type: ignore
        return json.loads(raw)

    def test_default_routes_to_wavespeed(self):
        wavespeed = _RecordingProvider("wavespeed")
        hyperframes = _RecordingProvider("hyperframes")
        video_gen_registry.register_provider(wavespeed)
        video_gen_registry.register_provider(hyperframes)

        result = self._run({"prompt": "a dog running"})

        assert result["success"] is True
        assert result["provider"] == "wavespeed"
        assert wavespeed.last_kwargs["prompt"] == "a dog running"
        assert "composition_path" not in wavespeed.last_kwargs

    def test_institutional_routes_to_hyperframes(self):
        wavespeed = _RecordingProvider("wavespeed")
        hyperframes = _RecordingProvider("hyperframes")
        video_gen_registry.register_provider(wavespeed)
        video_gen_registry.register_provider(hyperframes)

        result = self._run({
            "prompt": "institutional teaser",
            "video_type": "institutional",
            "composition_path": "/tmp/example/index.html",
        })

        assert result["success"] is True
        assert result["provider"] == "hyperframes"
        assert hyperframes.last_kwargs["composition_path"] == "/tmp/example/index.html"
        assert "composition_path" not in wavespeed.last_kwargs
