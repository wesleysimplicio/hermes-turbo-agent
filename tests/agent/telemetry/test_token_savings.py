"""Tests for ``agent.telemetry.token_savings``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.telemetry.token_savings import (
    TokenSavingRecord,
    default_log_path,
    iter_records,
    record_token_saving,
)


def test_record_token_saving_writes_jsonl(tmp_path: Path) -> None:
    log = tmp_path / "savings.jsonl"
    record = record_token_saving(
        1000, 250, tool="read_file", adapter="anthropic", log_path=log,
    )
    assert (record.saved_tokens, record.savings_pct) == (750, 75.0)
    payload = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert payload["raw_tokens"] == 1000
    assert payload["saved_tokens"] == 750
    assert payload["tool"] == "read_file"


def test_record_clamps_compressed_above_raw(tmp_path: Path) -> None:
    record = record_token_saving(100, 500, log_path=tmp_path / "s.jsonl")
    assert record.compressed_tokens == 100
    assert record.savings_pct == 0.0


def test_record_zero_raw_does_not_divide(tmp_path: Path) -> None:
    record = record_token_saving(0, 0, log_path=tmp_path / "s.jsonl")
    assert record.savings_pct == 0.0


def test_iter_records_skips_blank_and_malformed(tmp_path: Path) -> None:
    log = tmp_path / "savings.jsonl"
    log.write_text(
        '{"raw_tokens":10,"compressed_tokens":5}\n\nnot-json\n'
        '{"raw_tokens":20,"compressed_tokens":4}\n',
        encoding="utf-8",
    )
    records = list(iter_records(log))
    assert len(records) == 2 and records[1]["compressed_tokens"] == 4


def test_iter_records_missing_file_yields_empty(tmp_path: Path) -> None:
    assert list(iter_records(tmp_path / "missing.jsonl")) == []


def test_default_log_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    override = tmp_path / "custom.jsonl"
    monkeypatch.setenv("HERMES_TOKEN_SAVINGS_LOG", str(override))
    assert default_log_path() == override
    monkeypatch.delenv("HERMES_TOKEN_SAVINGS_LOG")
    assert default_log_path().name == "token_savings.jsonl"


def test_token_saving_record_to_json_includes_saved() -> None:
    record = TokenSavingRecord(raw_tokens=200, compressed_tokens=50, ts="2026-05-21T12:34:56Z")
    payload = json.loads(record.to_json())
    assert payload["saved_tokens"] == 150


def test_record_handles_unwritable_path(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    record = record_token_saving(10, 1, log_path=blocker / "nested" / "log.jsonl")
    assert record.saved_tokens == 9  # never raises
