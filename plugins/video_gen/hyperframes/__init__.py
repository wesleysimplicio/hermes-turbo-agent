"""Hyperframes HTML-to-video backend for institutional renders.

This provider expects a local HTML composition file and shells out to the
Hyperframes CLI for lint/validate/render.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Any, Dict, List, Optional

from agent.video_gen_provider import VideoGenProvider, error_response, success_response

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "hyperframes-html"


class HyperframesVideoGenProvider(VideoGenProvider):
    @property
    def name(self) -> str:
        return "hyperframes"

    @property
    def display_name(self) -> str:
        return "Hyperframes"

    def is_available(self) -> bool:
        return bool(which("npx")) and bool(which("node"))

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": DEFAULT_MODEL,
                "display": "Hyperframes HTML render",
                "speed": "depends on composition",
                "strengths": "Institutional videos, storyboard renders, deterministic HTML-to-video",
                "price": "local render",
                "modalities": ["text", "image"],
            }
        ]

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": ["16:9", "9:16", "1:1", "4:3", "3:4"],
            "resolutions": ["1080p", "4k", "square", "portrait"],
            "max_duration": 600,
            "min_duration": 1,
            "supports_audio": True,
            "supports_negative_prompt": False,
            "max_reference_images": 0,
        }

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Hyperframes",
            "badge": "local",
            "tag": "HTML composition renderer for institutional videos",
            "env_vars": [],
        }

    def _resolve_composition_path(self, kwargs: Dict[str, Any]) -> Optional[Path]:
        for key in ("composition_path", "storyboard_path", "html_path"):
            raw = kwargs.get(key)
            if isinstance(raw, str) and raw.strip():
                path = Path(raw.strip()).expanduser()
                if path.exists():
                    return path
        return None

    def _run(self, *args: str, cwd: Path) -> None:
        proc = subprocess.run(
            ["npx", "--yes", "hyperframes", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
            env=os.environ.copy(),
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "hyperframes failed").strip())

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        duration: Optional[int] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "1080p",
        negative_prompt: Optional[str] = None,
        audio: Optional[bool] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        composition = self._resolve_composition_path(kwargs)
        if composition is None:
            return error_response(
                error=(
                    "Hyperframes requires composition_path, storyboard_path, "
                    "or html_path for institutional renders."
                ),
                error_type="missing_composition",
                provider=self.name,
                prompt=prompt,
            )

        try:
            self._run("lint", str(composition.parent), cwd=composition.parent)
            self._run("validate", str(composition.parent), cwd=composition.parent)
            output_dir = composition.parent / "renders"
            output_dir.mkdir(exist_ok=True)
            output = output_dir / f"{composition.stem}.mp4"
            self._run("render", str(composition.parent), "-c", str(composition), "-o", str(output), cwd=composition.parent)
        except Exception as exc:
            return error_response(
                error=f"Hyperframes render failed: {exc}",
                error_type="api_error",
                provider=self.name,
                model=model or DEFAULT_MODEL,
                prompt=prompt,
            )

        return success_response(
            video=str(output),
            model=model or DEFAULT_MODEL,
            prompt=prompt,
            modality="image" if image_url else "text",
            aspect_ratio=aspect_ratio,
            duration=duration or 0,
            provider=self.name,
            extra={"composition": str(composition)},
        )


def register(ctx) -> None:
    ctx.register_video_gen_provider(HyperframesVideoGenProvider())
