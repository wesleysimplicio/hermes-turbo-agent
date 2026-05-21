"""Unit tests for ``agent.token_saver.proxy``."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agent.token_saver.proxy import (
    DEFAULT_HEAD,
    DEFAULT_MAX_LINES,
    DEFAULT_TAIL,
    TokenSaverProxy,
    truncate_output,
)


def _make_lines(n: int) -> str:
    return "\n".join(f"line-{i:04d}" for i in range(n))


class TestTruncateOutput:
    def test_under_threshold_returns_unchanged(self, tmp_path: Path) -> None:
        text = _make_lines(10)
        result = truncate_output(
            text, max_lines=50, head=10, tail=10, storage_dir=tmp_path
        )
        assert result.truncated is False
        assert result.text == text
        assert result.handle is None
        assert result.full_path is None
        assert result.original_line_count == 10
        assert result.kept_line_count == 10
        assert list(tmp_path.iterdir()) == []

    def test_exact_threshold_is_not_truncated(self, tmp_path: Path) -> None:
        text = _make_lines(50)
        result = truncate_output(
            text, max_lines=50, head=10, tail=10, storage_dir=tmp_path
        )
        assert result.truncated is False
        assert result.text == text

    def test_above_threshold_keeps_head_and_tail(self, tmp_path: Path) -> None:
        text = _make_lines(500)
        result = truncate_output(
            text, max_lines=100, head=20, tail=30, storage_dir=tmp_path
        )
        assert result.truncated is True
        kept_lines = result.text.split("\n")
        assert len(kept_lines) == 20 + 1 + 30
        assert kept_lines[0] == "line-0000"
        assert kept_lines[19] == "line-0019"
        assert kept_lines[-1] == "line-0499"
        assert kept_lines[-30] == "line-0470"
        marker = kept_lines[20]
        assert "truncated" in marker
        assert "<handle:" in marker
        assert result.meta == {"head": 20, "tail": 30, "elided": 450}

    def test_handle_points_to_file_with_full_output(self, tmp_path: Path) -> None:
        text = _make_lines(300)
        result = truncate_output(
            text, max_lines=50, head=10, tail=10, storage_dir=tmp_path
        )
        assert result.handle is not None
        assert result.full_path is not None
        match = re.match(r"^<handle:(.+)>$", result.handle)
        assert match is not None
        assert match.group(1) == result.full_path
        assert Path(result.full_path).read_text(encoding="utf-8") == text

    def test_head_only_no_tail(self, tmp_path: Path) -> None:
        text = _make_lines(100)
        result = truncate_output(
            text, max_lines=30, head=30, tail=0, storage_dir=tmp_path
        )
        assert result.truncated is True
        kept = result.text.split("\n")
        assert kept[:30] == [f"line-{i:04d}" for i in range(30)]
        assert kept[-1].startswith("... [token-saver] truncated")

    def test_tail_only_no_head(self, tmp_path: Path) -> None:
        text = _make_lines(100)
        result = truncate_output(
            text, max_lines=30, head=0, tail=30, storage_dir=tmp_path
        )
        assert result.truncated is True
        kept = result.text.split("\n")
        assert kept[0].startswith("... [token-saver] truncated")
        assert kept[-30:] == [f"line-{i:04d}" for i in range(70, 100)]

    def test_invalid_args_raise(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            truncate_output("x", max_lines=0, storage_dir=tmp_path)
        with pytest.raises(ValueError):
            truncate_output(
                "x", max_lines=10, head=-1, tail=5, storage_dir=tmp_path
            )
        with pytest.raises(ValueError):
            truncate_output(
                "x", max_lines=10, head=8, tail=8, storage_dir=tmp_path
            )


class TestTokenSaverProxy:
    def test_wrap_and_resolve_round_trip(self, tmp_path: Path) -> None:
        proxy = TokenSaverProxy(
            max_lines=20, head=5, tail=5, storage_dir=tmp_path
        )
        text = _make_lines(200)
        result = proxy.wrap(text)
        assert result.truncated is True
        assert result.handle is not None
        assert proxy.resolve(result.handle) == text

    def test_resolve_rejects_bad_handle(self, tmp_path: Path) -> None:
        proxy = TokenSaverProxy(storage_dir=tmp_path)
        with pytest.raises(ValueError):
            proxy.resolve("not-a-handle")
        with pytest.raises(FileNotFoundError):
            proxy.resolve("<handle:/nonexistent/path/output.txt>")

    def test_defaults_are_reasonable(self) -> None:
        assert DEFAULT_MAX_LINES > 0
        assert DEFAULT_HEAD + DEFAULT_TAIL <= DEFAULT_MAX_LINES
