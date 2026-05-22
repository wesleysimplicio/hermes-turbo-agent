"""Tests for the token-saver backend selector (#94)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.token_saver.backend import (
    ENV_BACKEND,
    BackendChoice,
    BackendError,
    resolve_backend,
    saver,
)


class TestResolveBackend:
    def test_native_explicit_ignores_missing_rtk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: None)
        decision = resolve_backend("native")
        assert decision.chosen is BackendChoice.NATIVE
        assert decision.rtk_available is False

    def test_rtk_explicit_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: None)
        with pytest.raises(BackendError):
            resolve_backend("rtk")

    def test_rtk_explicit_resolves_when_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: "/usr/bin/rtk")
        decision = resolve_backend("rtk")
        assert decision.chosen is BackendChoice.RTK
        assert decision.rtk_path == "/usr/bin/rtk"

    def test_auto_prefers_rtk_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: "/x/rtk")
        decision = resolve_backend("auto")
        assert decision.chosen is BackendChoice.RTK

    def test_auto_falls_back_native(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: None)
        decision = resolve_backend("auto")
        assert decision.chosen is BackendChoice.NATIVE
        assert decision.rtk_available is False

    def test_env_variable_drives_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_BACKEND, "native")
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: "/x/rtk")
        decision = resolve_backend()
        assert decision.chosen is BackendChoice.NATIVE

    def test_invalid_value_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: None)
        with pytest.raises(BackendError):
            resolve_backend("turbo")


class TestSaverFallback:
    def test_native_path_truncates_long_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: None)
        text = "\n".join(f"line-{i}" for i in range(2000))
        result = saver(text, backend="native", storage_dir=tmp_path / "ts")
        assert result.truncated is True
        assert result.handle is not None
        assert "truncated" in result.text

    def test_rtk_failure_falls_back_to_native(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: "/x/rtk")
        monkeypatch.setattr(
            "agent.token_saver.backend.compress_with_rtk", lambda *a, **kw: None
        )
        text = "\n".join(f"row-{i}" for i in range(2000))
        result = saver(text, backend="rtk", storage_dir=tmp_path / "ts")
        # Fell back to native, which truncates this volume.
        assert result.truncated is True
        assert (result.meta or {}).get("backend") != "rtk"

    def test_rtk_success_uses_rtk_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("agent.token_saver.backend.detect_rtk", lambda *_: "/x/rtk")
        monkeypatch.setattr(
            "agent.token_saver.backend.compress_with_rtk",
            lambda *a, **kw: "compressed",
        )
        text = "\n".join(f"r-{i}" for i in range(2000))
        result = saver(text, backend="rtk", storage_dir=tmp_path / "ts")
        assert result.text == "compressed"
        assert result.meta["backend"] == "rtk"
