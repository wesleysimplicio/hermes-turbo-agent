"""``hermes prompt sync`` — distribute the canonical runtime prompt to multi-IDE
rule files via idempotent delimited blocks (P3).

Inspired by ``wesleysimplicio/simplicio-prompt``: writes a single source-of-truth
prompt (``prompts/runtime/hermes-turbo.md``) into target files used by different
agent CLIs (Claude Code, Codex, Hermes, Cursor, Copilot, Aider, etc.). The
block is fenced by ``HTM_START_MARK`` / ``HTM_END_MARK`` so re-runs replace
in place without duplicating content.

CLI::

    hermes prompt sync --list-targets
    hermes prompt sync --target claude
    hermes prompt sync --install-all --dry-run
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


HTM_START_MARK = "<!-- hermes-turbo:start -->"
HTM_END_MARK = "<!-- hermes-turbo:end -->"
DEFAULT_PROMPT_PATH = "prompts/runtime/hermes-turbo.md"


@dataclass(frozen=True)
class SyncTarget:
    """One destination for the canonical prompt."""

    key: str
    path: str
    fmt: str = "block"  # "block" (default) | "raw"
    description: str = ""


TARGETS: Tuple[SyncTarget, ...] = (
    SyncTarget("claude", "CLAUDE.md", "block", "Claude Code project rules"),
    SyncTarget("agents", "AGENTS.md", "block", "OpenAI Codex / generic agent rules"),
    SyncTarget("copilot", ".github/copilot-instructions.md", "block",
               "GitHub Copilot custom instructions"),
    SyncTarget("codex", ".codex/AGENTS.md", "block", "Codex CLI rules"),
    SyncTarget("cursor", ".cursorrules", "block", "Cursor editor rules"),
    SyncTarget("cline", ".clinerules", "block", "Cline rules"),
    SyncTarget("aider", "CONVENTIONS.md", "block", "Aider conventions"),
    SyncTarget("hermes", ".hermes/instructions.md", "raw", "Hermes home override"),
)


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a single ``apply`` call."""

    target: str
    path: str
    action: str  # "created" | "updated" | "unchanged" | "skipped"
    bytes_written: int = 0


def find_target(key: str) -> Optional[SyncTarget]:
    for t in TARGETS:
        if t.key == key:
            return t
    return None


def load_prompt(root: Path, prompt_path: str = DEFAULT_PROMPT_PATH) -> str:
    """Read the canonical prompt body from ``root/prompt_path``."""

    full = (root / prompt_path).expanduser().resolve()
    return full.read_text(encoding="utf-8")


def _wrap_block(body: str) -> str:
    return f"{HTM_START_MARK}\n{body.strip()}\n{HTM_END_MARK}\n"


def _replace_or_append_block(existing: str, body: str) -> Tuple[str, str]:
    block = _wrap_block(body)
    if HTM_START_MARK in existing and HTM_END_MARK in existing:
        start = existing.index(HTM_START_MARK)
        end = existing.index(HTM_END_MARK) + len(HTM_END_MARK)
        new = existing[:start] + block.rstrip() + existing[end:]
        return new, "updated"
    sep = "" if existing.endswith("\n\n") or not existing else (
        "\n" if existing.endswith("\n") else "\n\n"
    )
    return existing + sep + block, "appended"


def apply(
    target: SyncTarget,
    body: str,
    *,
    root: Path,
    dry_run: bool = False,
) -> SyncResult:
    """Inject ``body`` into ``target.path`` (relative to ``root``)."""

    dest = (root / target.path).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if target.fmt == "raw":
        new_content = body if body.endswith("\n") else body + "\n"
        existing = dest.read_text(encoding="utf-8") if dest.exists() else ""
        action = "unchanged" if existing == new_content else (
            "updated" if existing else "created"
        )
    else:
        existing = dest.read_text(encoding="utf-8") if dest.exists() else ""
        new_content, mode = _replace_or_append_block(existing, body)
        if not existing:
            action = "created"
        elif new_content == existing:
            action = "unchanged"
        else:
            action = "updated"
        _ = mode

    if dry_run:
        return SyncResult(target.key, str(dest), f"would-{action}", len(new_content))

    if action == "unchanged":
        return SyncResult(target.key, str(dest), action, len(new_content))

    dest.write_text(new_content, encoding="utf-8")
    return SyncResult(target.key, str(dest), action, len(new_content))


def sync_all(
    *,
    root: Path,
    targets: Iterable[SyncTarget] = TARGETS,
    prompt_path: str = DEFAULT_PROMPT_PATH,
    dry_run: bool = False,
) -> List[SyncResult]:
    body = load_prompt(root, prompt_path)
    return [apply(t, body, root=root, dry_run=dry_run) for t in targets]


def _format_results(results: List[SyncResult]) -> str:
    width = max((len(r.target) for r in results), default=8)
    lines = [f"{r.target.ljust(width)}  {r.action:>14}  {r.path}" for r in results]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hermes prompt sync",
        description="Distribute the Hermes runtime prompt to multi-IDE rule files.",
    )
    parser.add_argument("--target", help="single target key (see --list-targets)")
    parser.add_argument("--install-all", action="store_true",
                        help="apply to every registered target")
    parser.add_argument("--list-targets", action="store_true",
                        help="print the target registry and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned changes without writing")
    parser.add_argument("--root", default=".", help="repo root (default: cwd)")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT_PATH,
                        help=f"path to canonical prompt (default: {DEFAULT_PROMPT_PATH})")
    args = parser.parse_args(argv)

    if args.list_targets:
        for t in TARGETS:
            print(f"{t.key:<10} {t.path:<40} [{t.fmt}] {t.description}")
        return 0

    root = Path(args.root).expanduser().resolve()
    if args.target:
        t = find_target(args.target)
        if t is None:
            print(f"unknown target: {args.target}", file=sys.stderr)
            return 2
        results = [apply(t, load_prompt(root, args.prompt),
                         root=root, dry_run=args.dry_run)]
    elif args.install_all:
        results = sync_all(root=root, prompt_path=args.prompt, dry_run=args.dry_run)
    else:
        parser.print_help()
        return 2

    print(_format_results(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
