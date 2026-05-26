"""Tests for the Python version guard in hermes_cli.__init__."""

from __future__ import annotations

import pytest

import hermes_cli


def test_passes_on_current_interpreter():
    calls = []

    result = hermes_cli._assert_python_version(exit_fn=lambda code: calls.append(code))

    assert result is None
    assert calls == []


def test_passes_on_explicit_minimum():
    calls = []
    result = hermes_cli._assert_python_version(
        current=hermes_cli._MIN_PYTHON + (0,),
        exit_fn=lambda code: calls.append(code),
    )
    assert result is None
    assert calls == []


def test_passes_on_above_minimum():
    calls = []
    major, minor = hermes_cli._MIN_PYTHON
    result = hermes_cli._assert_python_version(
        current=(major, minor + 1, 0),
        exit_fn=lambda code: calls.append(code),
    )
    assert result is None
    assert calls == []


def test_exits_on_python_3_9(capsys):
    calls = []
    hermes_cli._assert_python_version(
        current=(3, 9, 18),
        exit_fn=lambda code: calls.append(code),
    )

    captured = capsys.readouterr()
    assert calls == [1]
    assert "requires Python 3.11+" in captured.err
    assert "found 3.9.18" in captured.err


def test_exits_on_python_3_10(capsys):
    calls = []
    hermes_cli._assert_python_version(
        current=(3, 10, 12),
        exit_fn=lambda code: calls.append(code),
    )

    captured = capsys.readouterr()
    assert calls == [1]
    assert "found 3.10.12" in captured.err


def test_message_uses_configured_minimum(capsys):
    calls = []
    hermes_cli._assert_python_version(
        current=(3, 8, 0),
        min_version=(3, 12),
        exit_fn=lambda code: calls.append(code),
    )

    captured = capsys.readouterr()
    assert calls == [1]
    assert "requires Python 3.12+" in captured.err
    assert "found 3.8.0" in captured.err


@pytest.mark.parametrize(
    "current",
    [(2, 7, 18), (3, 0, 0), (3, 5, 9), (3, 9, 0)],
)
def test_exits_on_assorted_legacy_versions(current):
    calls = []
    hermes_cli._assert_python_version(
        current=current,
        exit_fn=lambda code: calls.append(code),
    )
    assert calls == [1]
