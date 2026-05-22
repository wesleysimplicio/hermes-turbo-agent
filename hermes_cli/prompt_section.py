"""``hermes prompt section <name>`` — extract a single markdown section (P6).

Subagents do not need to receive the full CLAUDE.md / AGENTS.md text on every
spawn. ``get_section(text, name)`` extracts the markdown block under the
specified header (``## <name>``) up to (but not including) the next same-or-
higher-level header. Pure stdlib, no parsing dependency.

Inspired by ``simplicio-prompt.getPromptSection()``.
"""

from __future__ import annotations

import argparse
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def get_section(text: str, name: str) -> Optional[str]:
    """Return the body under the markdown header matching ``name``.

    Matches are case-insensitive and whitespace-normalized. Returns ``None``
    when the header is not present.
    """

    target = _normalize(name)
    headers = list(_HEADER_RE.finditer(text))
    if not headers:
        return None

    for idx, m in enumerate(headers):
        level = len(m.group(1))
        title = _normalize(m.group(2))
        if title != target:
            continue
        start = m.end()
        end = len(text)
        for next_m in headers[idx + 1:]:
            next_level = len(next_m.group(1))
            if next_level <= level:
                end = next_m.start()
                break
        body = text[start:end].strip("\n")
        return body.rstrip() + "\n" if body else ""
    return None


@lru_cache(maxsize=64)
def _read(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def get_file_section(file_path: str | Path, name: str) -> Optional[str]:
    """Convenience wrapper. Result of ``Path.read_text`` is LRU-cached."""

    text = _read(str(Path(file_path).expanduser().resolve()))
    return get_section(text, name)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes prompt section",
        description="Extract a named markdown section from a prompt file.",
    )
    parser.add_argument("name", help="header text (case-insensitive)")
    parser.add_argument("--file", default="CLAUDE.md",
                        help="source file (default: CLAUDE.md)")
    args = parser.parse_args(argv)

    body = get_file_section(args.file, args.name)
    if body is None:
        print(f"section not found: {args.name}", file=sys.stderr)
        return 1
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
