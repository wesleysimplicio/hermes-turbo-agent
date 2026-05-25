"""WaveSpeedAI video generation backend.

Routes text-to-video and image-to-video through the bundled `wavespeed-cli`
wrapper. This provider intentionally starts small: it delegates execution to
the existing CLI rather than reimplementing the REST API in the plugin.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from shutil import which as _which
from typing import Any, Dict, List, Optional

from agent.video_gen_provider import VideoGenProvider, error_response, success_response

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "wavespeed-ai/seedance-v2"
DEFAULT_DURATION = 5
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "720p"


class WaveSpeedVideoGenProvider(VideoGenProvider):
    @property
    def name(self) -> str:
        return "wavespeed"

    @property
    def display_name(self) -> str:
        return "WaveSpeedAI"

    def is_available(self) -> bool:
        return bool(os.environ.get("WAVESPEED_API_KEY", "").strip()) and bool(
            self._cli_path()
        )

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "wavespeed-ai/seedance-v2",
                "display": "Seedance v2",
                "speed": "~5-10s",
                "strengths": "Cinematic camera moves, image-to-video scene motion",
                "price": "see WaveSpeedAI catalog",
                "modalities": ["image"],
            },
            {
                "id": "wavespeed-ai/kling-v2.6-pro",
                "display": "Kling v2.6 Pro",
                "speed": "~10s",
                "strengths": "Top-tier people/fabrics, image-to-video character motion",
                "price": "see WaveSpeedAI catalog",
                "modalities": ["image"],
            },
            {
                "id": "wavespeed-ai/veo-3.1",
                "display": "Veo 3.1",
                "speed": "~10s",
                "strengths": "Hero text-to-video with audio",
                "price": "see WaveSpeedAI catalog",
                "modalities": ["text"],
            },
        ]

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": ["16:9", "9:16", "1:1", "4:3", "3:4"],
            "resolutions": ["480p", "720p", "1080p"],
            "max_duration": 15,
            "min_duration": 1,
            "supports_audio": True,
            "supports_negative_prompt": False,
            "max_reference_images": 7,
        }

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "WaveSpeedAI",
            "badge": "paid",
            "tag": "wavespeed-cli — text-to-video & image-to-video",
            "env_vars": [
                {
                    "key": "WAVESPEED_API_KEY",
                    "prompt": "WaveSpeedAI API key",
                    "url": "https://wavespeed.ai/accesskey",
                },
            ],
        }

    def _cli_path(self) -> Optional[str]:
        return _which("wavespeed-cli")

    def _run_cli(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cli = self._cli_path()
        if not cli:
            raise FileNotFoundError("wavespeed-cli not found on PATH")
        proc = subprocess.run(
            [cli, "run", model, json.dumps(payload, ensure_ascii=False)],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
            env=os.environ.copy(),
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "wavespeed-cli failed").strip())
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"wavespeed-cli returned non-JSON output: {exc}") from exc

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        duration: Optional[int] = None,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        resolution: str = DEFAULT_RESOLUTION,
        negative_prompt: Optional[str] = None,
        audio: Optional[bool] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.is_available():
            return error_response(
                error="WAVESPEED_API_KEY not set or wavespeed-cli missing from PATH.",
                error_type="auth_required",
                provider=self.name,
                prompt=prompt,
            )

        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="prompt is required.",
                error_type="missing_prompt",
                provider=self.name,
                prompt=prompt,
            )

        model_id = model or DEFAULT_MODEL
        payload: Dict[str, Any] = {"prompt": prompt}
        if image_url:
            payload["image"] = image_url
        if reference_image_urls:
            payload["reference_images"] = reference_image_urls
        if duration is not None:
            payload["duration"] = duration
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if resolution:
            payload["resolution"] = resolution
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if audio is not None:
            payload["audio"] = audio
        if seed is not None:
            payload["seed"] = seed

        if kwargs:
            logger.debug("WaveSpeedAI ignoring unknown kwargs: %s", sorted(kwargs))

        try:
            result = self._run_cli(model_id, payload)
        except Exception as exc:
            return error_response(
                error=f"WaveSpeedAI video generation failed: {exc}",
                error_type="api_error",
                provider=self.name,
                model=model_id,
                prompt=prompt,
            )

        video = result.get("video") if isinstance(result, dict) else None
        if isinstance(video, dict):
            video = video.get("url") or video.get("path")
        if not isinstance(video, str) or not video.strip():
            return error_response(
                error="WaveSpeedAI returned no video URL/path in response",
                error_type="empty_response",
                provider=self.name,
                model=model_id,
                prompt=prompt,
            )

        return success_response(
            video=video,
            model=model_id,
            prompt=prompt,
            modality="image" if image_url else "text",
            aspect_ratio=aspect_ratio,
            duration=duration or 0,
            provider=self.name,
            extra={"backend": "wavespeed-cli"},
        )


def register(ctx) -> None:
    ctx.register_video_gen_provider(WaveSpeedVideoGenProvider())
