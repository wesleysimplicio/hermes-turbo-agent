from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_cli import tota_update_prompt as prompt


def test_version_tuple_accepts_tags():
    assert prompt._version_tuple("v0.14.3") == (0, 14, 3)
    assert prompt._version_tuple("Tota Agent v1.2.0") == (1, 2, 0)


def test_latest_release_update_ignores_current_or_older(monkeypatch):
    monkeypatch.setattr(
        prompt,
        "_fetch_latest_release",
        lambda: {"tag_name": "v0.14.2", "html_url": "https://example.test", "name": "same"},
    )
    assert prompt.latest_release_update("0.14.2") is None


def test_latest_release_update_returns_newer(monkeypatch):
    monkeypatch.setattr(
        prompt,
        "_fetch_latest_release",
        lambda: {"tag_name": "v0.14.3", "html_url": "https://example.test", "name": "new"},
    )
    assert prompt.latest_release_update("0.14.2")["tag_name"] == "v0.14.3"


def test_prompt_throttle_is_per_release(tmp_path, monkeypatch):
    cache = tmp_path / "cache.json"
    monkeypatch.setattr(prompt, "_cache_path", lambda: cache)

    assert prompt._should_prompt("v0.14.3", now=1000) is True
    prompt._record_prompt("v0.14.3", "n")
    data = json.loads(cache.read_text(encoding="utf-8"))
    data["prompt"]["last_prompted_at"] = 1000
    cache.write_text(json.dumps(data), encoding="utf-8")

    assert prompt._should_prompt("v0.14.3", now=1001) is False
    assert prompt._should_prompt("v0.14.4", now=1001) is True


def test_update_command_uses_module_update_for_git_checkout(monkeypatch, tmp_path):
    fake_module = tmp_path / "hermes_cli" / "tota_update_prompt.py"
    fake_module.parent.mkdir()
    fake_module.write_text("", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    monkeypatch.setattr(prompt, "__file__", str(fake_module))
    assert prompt.update_command() == [sys.executable, "-m", "hermes_cli.main", "update", "--yes"]


def test_update_command_uses_tota_git_url_for_packaged_install(monkeypatch, tmp_path):
    fake_module = tmp_path / "hermes_cli" / "tota_update_prompt.py"
    fake_module.parent.mkdir()
    fake_module.write_text("", encoding="utf-8")

    monkeypatch.setattr(prompt, "__file__", str(fake_module))
    monkeypatch.setattr(prompt.shutil, "which", lambda name: None)
    assert prompt.update_command() == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        f"git+{prompt.TOTA_GIT_URL}",
    ]
