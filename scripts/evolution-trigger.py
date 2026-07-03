#!/usr/bin/env python3
"""
Evolution Trigger — Auto-detection of Simplicio Runtime limitations.

When Hermes Turbo needs a tool that Simplicio does not have (or returns an
error), this script detects the gap, checks for existing duplicates, and
opens a structured GitHub issue in the configured runtime repository.

Usage:
    # After a failed Simplicio tool call, pipe details:
    evolution-trigger.py --tool simplicio.edit --error "tool not found" \\
        --command "write_file('foo.py', content)" --context "wanted to edit file"

    # Dry-run mode (no issue created):
    evolution-trigger.py --tool simplicio.edit --dry-run

    # Manual suggestion:
    evolution-trigger.py --tool simplicio.new-tool --suggest "Add file rename support"

    # Install as a Hermes post-tool hook (optional):
    evolution-trigger.py --install-hook

Requirements: gh CLI authenticated, Python 3.10+
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Configuration ────────────────────────────────────────────────────────────

REPO_OWNER = os.environ.get("HERMES_TURBO_RUNTIME_OWNER", "wesleysimplicio")
REPO_NAME = os.environ.get("HERMES_TURBO_RUNTIME_REPO", "hermes-turbo-agent")
REPO = f"{REPO_OWNER}/{REPO_NAME}"

# Labels used on evolution / enhancement issues
DEFAULT_LABELS = "enhancement,evolution-trigger,simplicio"

# Path to a local dedup cache (avoids re-creating the same issue across runs)
DEDUP_CACHE = os.environ.get(
    "HERMES_TURBO_EVOLUTION_CACHE",
    str(Path.home() / ".hermes_turbo" / "evolution-trigger-dedup.json"),
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _run_gh(*args: str, input_data: Optional[str] = None) -> str:
    """Run `gh` CLI and return stdout."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            input=input_data,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"[evolution-trigger] gh error: {result.stderr.strip()}", file=sys.stderr)
            return ""
        return result.stdout.strip()
    except FileNotFoundError:
        print(
            "[evolution-trigger] ERROR: gh CLI not found. Install GitHub CLI: "
            "https://cli.github.com/",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print("[evolution-trigger] ERROR: gh CLI timed out", file=sys.stderr)
        return ""


def _load_dedup_cache() -> dict:
    """Load the dedup cache from disk."""
    path = Path(DEDUP_CACHE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_dedup_cache(cache: dict) -> None:
    """Save the dedup cache to disk."""
    path = Path(DEDUP_CACHE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2))


def _normalize_tool_name(tool: str) -> str:
    """Normalize tool name for dedup key: 'simplicio.edit' → 'edit'."""
    return tool.lower().replace("simplicio.", "").replace("-", "_").replace(" ", "_")


def _check_existing_issues(tool_name: str) -> bool:
    """Check if an open issue already exists for this tool gap. Returns True if
    a duplicate exists."""
    query = f"is:issue is:open label:evolution-trigger {tool_name} in:title repo:{REPO}"
    output = _run_gh("issue", "list", "--state", "open", "--search", f'"{tool_name}"', "--repo", REPO, "--limit", "1")
    return bool(output.strip())


def _generate_suggestion(tool: str, error: str, command: str, context: str) -> str:
    """Generate a structured enhancement suggestion based on available info."""
    tool_short = _normalize_tool_name(tool)

    lines = [
        f"## 🧬 Evolution Trigger: `{tool}`",
        "",
        "### Context",
        f"",
        f"Hermes Turbo attempted to use **`{tool}`** but encountered an error.",
        "",
    ]

    if command:
        lines.append(f"- **Command**: `{command}`")
    if error:
        lines.append(f"- **Error**: `{error}`")
    if context:
        lines.append(f"- **Scenario**: {context}")

    lines += [
        "",
        "### Suggested Implementation",
        "",
        "_TODO: Describe the expected tool interface, parameters, and return type._",
        "",
        "```python",
        f"# Suggested signature for '{tool_short}'",
        f"def {tool_short}(",
        "    # TODO: define parameters",
        "    ...",
        ") -> dict:",
        '    """',
        f'    {tool_short}: TODO - describe what this tool does.',
        "",
        "    Returns:",
        "        dict with result/error keys.",
        '    """',
        "    raise NotImplementedError",
        "```",
        "",
        "### Evidence",
        "",
        "Collected automatically by `scripts/evolution-trigger.py`.",
        f"- **Timestamp**: {datetime.now(timezone.utc).isoformat()}",
        "- **Trigger**: Failed tool call",
        "",
        "### Priority",
        "",
        "Priority is determined by frequency of occurrence. If this tool is",
        "requested multiple times, consider higher priority.",
        "---",
        "*This issue was automatically created by the Evolution Trigger system.*",
    ]
    return "\n".join(lines)


def _count_occurrences(cache: dict, tool_key: str) -> int:
    """Increment and return the occurrence count for a tool."""
    entry = cache.get(tool_key, {"count": 0, "first_seen": None})
    entry["count"] += 1
    if entry["first_seen"] is None:
        entry["first_seen"] = datetime.now(timezone.utc).isoformat()
    entry["last_seen"] = datetime.now(timezone.utc).isoformat()
    cache[tool_key] = entry
    return entry["count"]


# ── Main Actions ─────────────────────────────────────────────────────────────


def detect_and_report(
    tool: str,
    error: str = "",
    command: str = "",
    context: str = "",
    dry_run: bool = False,
) -> None:
    """
    Main detection flow:
    1. Normalize and dedup-check
    2. Count occurrences
    3. Check for existing issues
    4. If threshold met, create issue
    """
    tool_key = _normalize_tool_name(tool)
    cache = _load_dedup_cache()

    # Update occurrence count
    count = _count_occurrences(cache, tool_key)
    _save_dedup_cache(cache)

    # Minimum threshold: 1 occurrence to create an issue
    if count < 1:
        return

    # Check if an open issue already exists
    if _check_existing_issues(tool_key):
        print(f"[evolution-trigger] DUPLICATE: issue for '{tool}' already open — skipping")
        return

    # Check dedup cache for already-reported tools
    cached = cache.get(tool_key, {})
    if cached.get("issue_url"):
        print(f"[evolution-trigger] DUPLICATE: already reported at {cached['issue_url']} — skipping")
        return

    # Build issue body
    title = f"[Evolution] Simplicio missing tool: {tool}"
    body = _generate_suggestion(tool, error, command, context)

    if dry_run:
        print("=" * 60)
        print(f"[evolution-trigger] DRY-RUN: would create issue")
        print(f"  Title: {title}")
        print(f"  Repo:  {REPO}")
        print(f"  Tool:  {tool}")
        print(f"  Count: {count}")
        print("=" * 60)
        print("\n--- Issue Body Preview ---")
        print(body)
        print("--- End Preview ---")
        return

    # Create the issue
    print(f"[evolution-trigger] Creating issue in {REPO}...")

    # Use gh issue create with title and body
    issue_url = _run_gh(
        "issue", "create",
        "--repo", REPO,
        "--title", title,
        "--label", DEFAULT_LABELS,
        "--body", body,
    )

    if issue_url:
        print(f"[evolution-trigger] Created issue: {issue_url}")
        # Update cache
        cache[tool_key]["issue_url"] = issue_url
        cache[tool_key]["created_at"] = datetime.now(timezone.utc).isoformat()
        _save_dedup_cache(cache)
    else:
        print(f"[evolution-trigger] FAILED to create issue — check gh auth and permissions", file=sys.stderr)


def suggest(tool: str, suggestion: str = "", dry_run: bool = False) -> None:
    """Create a manual suggestion without error context."""
    detect_and_report(
        tool=tool,
        context=suggestion or "Manual suggestion",
        dry_run=dry_run,
    )


def install_hook() -> None:
    """Install as a Hermes post-tool hook (adds to Hermes config)."""
    hook_config = {
        "evolution-trigger": {
            "command": f"python3 {__file__}",
            "trigger": "on_tool_error",
            "description": "Auto-detect Simplicio tool gaps and create evolution issues",
        }
    }
    hook_path = Path.home() / ".hermes_turbo" / "hooks" / "evolution-trigger.json"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(json.dumps(hook_config, indent=2))
    print(f"[evolution-trigger] Hook installed at {hook_path}")

    # Also offer to set up a cron job for periodic reporting
    print("[evolution-trigger] To enable automatic periodic reporting, add to cron:")
    print(f"    0 6 * * 1 cd {Path.cwd()} && python3 {__file__} --report-unreported")


def report_unreported() -> None:
    """Report any unreported tools from the dedup cache."""
    cache = _load_dedup_cache()
    reported_any = False
    for tool_key, entry in cache.items():
        if not entry.get("issue_url") and entry.get("count", 0) >= 1:
            print(f"[evolution-trigger] Unreported: {tool_key} (count={entry['count']})")
            detect_and_report(tool=tool_key)
            reported_any = True
    if not reported_any:
        print("[evolution-trigger] All cached gaps have been reported.")


def list_gaps() -> None:
    """List all detected tool gaps and their status."""
    cache = _load_dedup_cache()
    if not cache:
        print("[evolution-trigger] No tool gaps recorded yet.")
        return

    print(f"{'Tool':<30} {'Count':<8} {'Status':<40}")
    print("-" * 78)
    for tool_key, entry in sorted(cache.items()):
        count = entry.get("count", 0)
        issue_url = entry.get("issue_url")
        last_seen = entry.get("last_seen", "unknown")
        status = issue_url or "not reported"
        print(f"{tool_key:<30} {count:<8} {status:<40}")
    print(f"\nTotal gaps detected: {len(cache)}")


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evolution Trigger — auto-detect Simplicio Runtime gaps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Core detection mode
    parser.add_argument("--tool", "-t", help="Tool name that failed (e.g. simplicio.edit)")
    parser.add_argument("--error", "-e", default="", help="Error message from the failed call")
    parser.add_argument("--command", "-c", default="", help="The command that triggered the error")
    parser.add_argument("--context", "-x", default="", help="Description of the scenario")

    # Other modes
    parser.add_argument("--suggest", "-s", help="Manual suggestion (tool name)")
    parser.add_argument("--suggestion-desc", "-d", default="", help="Description for manual suggestion")

    # Actions
    parser.add_argument("--dry-run", "-n", action="store_true", help="Preview without creating issue")
    parser.add_argument("--install-hook", action="store_true", help="Install as Hermes post-tool hook")
    parser.add_argument("--report-unreported", action="store_true", help="Report any cached but unreported gaps")
    parser.add_argument("--list-gaps", action="store_true", help="List all detected gaps and their status")

    args = parser.parse_args()

    # Dispatch actions
    if args.install_hook:
        install_hook()
    elif args.report_unreported:
        report_unreported()
    elif args.list_gaps:
        list_gaps()
    elif args.suggest:
        suggest(tool=args.suggest, suggestion=args.suggestion_desc, dry_run=args.dry_run)
    elif args.tool:
        detect_and_report(
            tool=args.tool,
            error=args.error,
            command=args.command,
            context=args.context,
            dry_run=args.dry_run,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
