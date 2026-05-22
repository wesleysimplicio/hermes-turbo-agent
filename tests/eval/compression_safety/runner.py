#!/usr/bin/env python3
"""Compression safety evaluation runner.

Loads golden fixtures from ``fixtures/`` and validates that every
``expected_preserved`` substring still appears in the compressed output of a
token-saver pass. The default compressor is a deterministic heuristic
(``collapse_repeated_lines``) so the suite runs without external dependencies.

A different compressor can be injected via the ``--compressor`` flag for
adapters that ship later (safe / balanced / aggressive modes). Each adapter
must accept ``str -> str``.

Exit status: 0 if every fixture preserves its required signals, 1 otherwise.
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def collapse_repeated_lines(text: str) -> str:
    """Default safe compressor: drop adjacent duplicate lines and trim trailing whitespace."""
    out: list[str] = []
    prev: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line == prev:
            continue
        out.append(line)
        prev = line
    return "\n".join(out)


def load_compressor(spec: str | None) -> Callable[[str], str]:
    if not spec:
        return collapse_repeated_lines
    module_name, _, attr = spec.rpartition(":")
    if not module_name:
        raise ValueError(f"compressor spec must be 'module:callable', got {spec!r}")
    module = importlib.import_module(module_name)
    fn = getattr(module, attr)
    if not callable(fn):
        raise TypeError(f"{spec} is not callable")
    return fn


def evaluate_fixture(fixture: dict[str, Any], compressor: Callable[[str], str]) -> list[str]:
    """Return a list of missing preserved tokens. Empty list means pass."""
    compressed = compressor(fixture["input"])
    return [needle for needle in fixture["expected_preserved"] if needle not in compressed]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compressor",
        default=None,
        help="Importable callable 'module.path:func' that takes str -> str.",
    )
    parser.add_argument(
        "--fixtures",
        default=str(FIXTURES_DIR),
        help="Directory with golden JSON fixtures.",
    )
    args = parser.parse_args(argv)

    fixtures_path = Path(args.fixtures)
    files = sorted(fixtures_path.glob("*.json"))
    if not files:
        print(f"no fixtures found under {fixtures_path}", file=sys.stderr)
        return 2

    compressor = load_compressor(args.compressor)
    failures: list[tuple[str, list[str]]] = []
    for fx_path in files:
        fixture = json.loads(fx_path.read_text(encoding="utf-8"))
        missing = evaluate_fixture(fixture, compressor)
        status = "OK" if not missing else "FAIL"
        print(f"[{status}] {fixture['name']} ({fixture['kind']})")
        if missing:
            for needle in missing:
                safe = re.sub(r"\s+", " ", needle)[:120]
                print(f"        missing: {safe!r}")
            failures.append((fixture["name"], missing))

    print()
    print(f"fixtures: {len(files)}  failures: {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
