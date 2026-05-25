"""WaveSpeedAI image generation backend.

Uses the ``wavespeed-cli`` wrapper to generate images via the
``wavespeed-ai/flux-schnell`` text-to-image model.

Requires:
    - ``WAVESPEED_API_KEY`` in environment
    - ``wavespeed-cli`` on PATH
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from shutil import which as _which
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

# Map Hermes aspect_ratio to Wavespeed size parameter
_ASPECT_TO_SIZE = {
    "landscape": "1280*720",
    "square": "1024*1024",
    "portrait": "720*1280",
}

DEFAULT_MODEL = "wavespeed-ai/flux-schnell"


class WaveSpeedImageGenProvider(ImageGenProvider):
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

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": DEFAULT_MODEL,
                "display": "FLUX.1 [schnell]",
                "speed": "~5s",
                "strengths": "Fast, high-quality text-to-image via WaveSpeedAI",
                "price": "see WaveSpeedAI catalog",
            },
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "WaveSpeedAI",
            "badge": "paid",
            "tag": "wavespeed-cli — text-to-image (FLUX.1 [schnell])",
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
            timeout=120,
            check=False,
            env=os.environ.copy(),
        )

        if proc.returncode != 0:
            raise RuntimeError(
                (proc.stderr or proc.stdout or "wavespeed-cli failed").strip()
            )

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"wavespeed-cli returned non-JSON output: {exc}"
            ) from exc

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
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

        # Map aspect ratio to size
        size = _ASPECT_TO_SIZE.get(aspect_ratio, _ASPECT_TO_SIZE[DEFAULT_ASPECT_RATIO])

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "size": size,
            "num_images": 1,
            "output_format": "jpeg",
        }

        # Ignore unknown kwargs (forward-compat)
        if kwargs:
            logger.debug(
                "WaveSpeedAI image_gen ignoring unknown kwargs: %s", sorted(kwargs)
            )

        try:
            result = self._run_cli(DEFAULT_MODEL, payload)
        except Exception as exc:
            return error_response(
                error=f"WaveSpeedAI image generation failed: {exc}",
                error_type="api_error",
                provider=self.name,
                model=DEFAULT_MODEL,
                prompt=prompt,
            )

        # Parse response: {"outputs": ["https://..."]}
        outputs = result.get("outputs") if isinstance(result, dict) else None
        image_url = None
        if isinstance(outputs, list) and outputs:
            image_url = outputs[0]

        if not isinstance(image_url, str) or not image_url.strip():
            return error_response(
                error="WaveSpeedAI returned no image URL in response",
                error_type="empty_response",
                provider=self.name,
                model=DEFAULT_MODEL,
                prompt=prompt,
            )

        return success_response(
            image=image_url,
            model=DEFAULT_MODEL,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            provider=self.name,
            extra={"backend": "wavespeed-cli"},
        )


def register(ctx) -> None:
    ctx.register_image_gen_provider(WaveSpeedImageGenProvider())
