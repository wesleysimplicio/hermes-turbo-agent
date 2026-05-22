from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from hermes_constants import get_hermes_home


VALID_MODES = {"off", "safe", "balanced", "aggressive"}
EXACT_READ_TOOLS = {"read_file", "skill_view"}
EXACT_READ_COMMANDS = (
    "cat ",
    "head ",
    "tail ",
    "sed ",
    "sed -n ",
    "nl ",
    "less ",
)
ERROR_PATTERNS = re.compile(
    r"(FAILED|ERROR|Traceback|AssertionError|Exception|File \".+\", line \d+|"
    r"^\s*E\s+|:\d+:\s|failed|error|short test summary|FAILURES)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CompressionSummary:
    text: str
    raw_chars: int
    compressed_chars: int
    raw_tokens: int
    compressed_tokens: int
    saved_tokens: int
    saved_to: Path


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0


def _normalize_mode(mode: str) -> str:
    clean = (mode or "safe").strip().lower()
    return clean if clean in VALID_MODES else "safe"


def _should_keep_command_raw(command: str, mode: str) -> bool:
    if mode != "safe":
        return False
    clean = command.strip()
    return clean.startswith(EXACT_READ_COMMANDS)


def _should_keep_tool_raw(tool_name: str, mode: str) -> bool:
    return tool_name in EXACT_READ_TOOLS


def _redact(text: str) -> str:
    try:
        from agent.redact import redact_sensitive_text

        return redact_sensitive_text(text, force=True)
    except Exception:
        return text


def _store_raw_output(*, content: str, prefix: str, command_or_tool: str) -> Path:
    safe_content = _redact(content)
    digest = hashlib.sha256(
        (command_or_tool + "\n" + safe_content).encode("utf-8", errors="replace")
    ).hexdigest()[:16]
    storage_dir = get_hermes_home() / "token-saver" / "raw"
    storage_dir.mkdir(parents=True, exist_ok=True)
    path = storage_dir / f"{prefix}-{digest}.log"
    path.write_text(safe_content, encoding="utf-8")
    return path


def _select_lines(lines: list[str], *, mode: str) -> list[str]:
    if not lines:
        return []

    budget = {"safe": 80, "balanced": 48, "aggressive": 28}.get(mode, 80)
    selected: list[str] = []

    for line in lines:
        if ERROR_PATTERNS.search(line):
            selected.append(line)
            if len(selected) >= budget:
                break

    if selected:
        return _dedupe_keep_order(selected)

    head_count = max(8, budget // 3)
    tail_count = max(8, budget // 3)
    if len(lines) <= head_count + tail_count:
        return lines
    return lines[:head_count] + ["..."] + lines[-tail_count:]


def _dedupe_keep_order(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


def _git_status_summary(lines: list[str], mode: str) -> list[str]:
    budget = {"safe": 80, "balanced": 50, "aggressive": 30}.get(mode, 80)
    counts: dict[str, int] = {}
    for line in lines:
        status = line[:2].strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    summary = [f"files_changed: {len(lines)}"]
    summary.extend(f"{status}: {count}" for status, count in sorted(counts.items()))
    summary.append("")
    summary.extend(lines[:budget])
    if len(lines) > budget:
        summary.append(f"... omitted {len(lines) - budget} more git status lines")
    return summary


def _build_summary(
    *,
    label: str,
    source_name: str,
    content: str,
    returncode: int | None,
    mode: str,
    saved_to: Path,
) -> CompressionSummary:
    lines = content.splitlines()
    if label == "command" and source_name.strip().startswith("git status"):
        useful = _git_status_summary(lines, mode)
    else:
        useful = _select_lines(lines, mode=mode)

    raw_tokens = estimate_tokens(content)
    body = "\n".join(useful).strip()
    if not body:
        body = "(no high-signal lines found)"

    exit_line = "" if returncode is None else f"exit_code: {returncode}\n"
    first_pass = (
        "<token-saver-output>\n"
        f"{label}: {source_name}\n"
        f"{exit_line}"
        f"mode: {mode}\n"
        f"saved_to: {saved_to}\n"
        f"raw_chars: {len(content)}\n"
        "compressed_chars: 0\n"
        f"estimated_raw_tokens: {raw_tokens}\n"
        "estimated_compressed_tokens: 0\n"
        "estimated_saved_tokens: 0\n"
        "summary:\n"
        f"{body}\n"
        "</token-saver-output>"
    )
    compressed_tokens = estimate_tokens(first_pass)
    saved_tokens = max(0, raw_tokens - compressed_tokens)
    final = first_pass.replace("compressed_chars: 0", f"compressed_chars: {len(first_pass)}")
    final = final.replace(
        "estimated_compressed_tokens: 0",
        f"estimated_compressed_tokens: {compressed_tokens}",
    )
    final = final.replace("estimated_saved_tokens: 0", f"estimated_saved_tokens: {saved_tokens}")
    return CompressionSummary(
        text=final,
        raw_chars=len(content),
        compressed_chars=len(final),
        raw_tokens=raw_tokens,
        compressed_tokens=compressed_tokens,
        saved_tokens=saved_tokens,
        saved_to=saved_to,
    )


def compress_command_output(
    *,
    command: str,
    output: str,
    returncode: int = 0,
    mode: str = "safe",
    min_chars: int = 1200,
) -> str:
    mode = _normalize_mode(mode)
    if mode == "off" or len(output) < min_chars or _should_keep_command_raw(command, mode):
        return output

    saved_to = _store_raw_output(content=output, prefix="terminal", command_or_tool=command)
    return _build_summary(
        label="command",
        source_name=command,
        content=output,
        returncode=returncode,
        mode=mode,
        saved_to=saved_to,
    ).text


def compress_tool_result(
    *,
    tool_name: str,
    result: str,
    mode: str = "safe",
    min_chars: int = 1200,
) -> str:
    mode = _normalize_mode(mode)
    if mode == "off" or len(result) < min_chars or _should_keep_tool_raw(tool_name, mode):
        return result

    saved_to = _store_raw_output(content=result, prefix="tool", command_or_tool=tool_name)
    return _build_summary(
        label="tool",
        source_name=tool_name,
        content=result,
        returncode=None,
        mode=mode,
        saved_to=saved_to,
    ).text
