"""Tests for ``hermes_cli.prompt_sync``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import prompt_sync as ps


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    (tmp_path / "prompts" / "runtime").mkdir(parents=True)
    (tmp_path / "prompts" / "runtime" / "hermes-turbo.md").write_text(
        "## Operating contract\n\nDo X.\n", encoding="utf-8"
    )
    return tmp_path


def test_find_target_known() -> None:
    assert ps.find_target("claude") is not None
    assert ps.find_target("unknown") is None


def test_apply_block_creates_file(workdir: Path) -> None:
    body = ps.load_prompt(workdir)
    target = ps.find_target("claude")
    assert target is not None
    result = ps.apply(target, body, root=workdir)
    assert result.action == "created"
    dest = workdir / target.path
    text = dest.read_text(encoding="utf-8")
    assert ps.HTM_START_MARK in text
    assert ps.HTM_END_MARK in text
    assert "Do X." in text


def test_apply_is_idempotent(workdir: Path) -> None:
    body = ps.load_prompt(workdir)
    target = ps.find_target("claude")
    assert target is not None

    ps.apply(target, body, root=workdir)
    second = ps.apply(target, body, root=workdir)
    assert second.action == "unchanged"


def test_apply_updates_block_in_place(workdir: Path) -> None:
    target = ps.find_target("claude")
    assert target is not None

    # Pre-existing file with our delimiters and stale content
    dest = workdir / target.path
    dest.write_text(
        "preamble\n\n"
        f"{ps.HTM_START_MARK}\nold body\n{ps.HTM_END_MARK}\n\n"
        "postamble\n",
        encoding="utf-8",
    )

    result = ps.apply(target, ps.load_prompt(workdir), root=workdir)
    assert result.action == "updated"

    text = dest.read_text(encoding="utf-8")
    assert "old body" not in text
    assert "Do X." in text
    assert "preamble" in text
    assert "postamble" in text


def test_apply_raw_format(workdir: Path) -> None:
    target = ps.find_target("hermes")
    assert target is not None
    assert target.fmt == "raw"

    result = ps.apply(target, "raw body\n", root=workdir)
    assert result.action == "created"
    dest = workdir / target.path
    assert dest.read_text(encoding="utf-8") == "raw body\n"


def test_dry_run_does_not_write(workdir: Path) -> None:
    target = ps.find_target("claude")
    assert target is not None
    result = ps.apply(target, "x", root=workdir, dry_run=True)
    assert result.action.startswith("would-")
    assert not (workdir / target.path).exists()


def test_sync_all_covers_every_target(workdir: Path) -> None:
    results = ps.sync_all(root=workdir)
    assert {r.target for r in results} == {t.key for t in ps.TARGETS}


def test_cli_list_targets(capsys: pytest.CaptureFixture[str]) -> None:
    rc = ps.main(["--list-targets"])
    captured = capsys.readouterr()
    assert rc == 0
    for t in ps.TARGETS:
        assert t.key in captured.out
