"""Tests for ``hermes_cli.prompt_section``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.prompt_section import get_file_section, get_section


SAMPLE = """\
# Title

intro

## Section A

body of A

with multiple lines

### Subsection A.1

a.1 body

## Section B

body of B

# Other H1

other
"""


def test_get_section_returns_body() -> None:
    body = get_section(SAMPLE, "Section A")
    assert body is not None
    assert "body of A" in body
    assert "Subsection A.1" in body
    assert "Section B" not in body
    assert "Other H1" not in body


def test_get_section_case_insensitive() -> None:
    body = get_section(SAMPLE, "section a")
    assert body is not None
    assert "body of A" in body


def test_get_section_missing_returns_none() -> None:
    assert get_section(SAMPLE, "Does Not Exist") is None


def test_get_section_stops_at_higher_level() -> None:
    body = get_section(SAMPLE, "Section B")
    assert body is not None
    assert "body of B" in body
    assert "other" not in body


def test_get_section_subsection() -> None:
    body = get_section(SAMPLE, "Subsection A.1")
    assert body is not None
    assert "a.1 body" in body
    assert "Section B" not in body


def test_get_file_section(tmp_path: Path) -> None:
    p = tmp_path / "doc.md"
    p.write_text(SAMPLE, encoding="utf-8")
    body = get_file_section(p, "Section A")
    assert body is not None
    assert "body of A" in body
