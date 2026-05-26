# Hermes 100X Fast Reapply Playbook

Date: 2026-05-15

Use this when NousResearch releases a new Hermes version and we want to carry
the 100X Fast work forward without guessing. The goal is not to replay patches
blindly; it is to re-apply only the optimizations that upstream still lacks,
then prove the behavior with the same focused tests and benchmark visuals.

## Branch Workflow

Start from fresh upstream, keep the old performance branch as a reference, and
open a new branch with the release/date in the name.

```powershell
git fetch upstream
git fetch origin
git switch -c codex/hermes-agent-100x-fast-YYYYMMDD upstream/main
git log --oneline --reverse origin/codex/hermes-agent-100x-fast
```

For each optimization below:

1. Inspect whether upstream already contains the idea.
2. If not present, cherry-pick the smallest relevant commit or manually port
   the code into the new upstream shape.
3. Run the focused test group for that optimization before moving to the next
   one.
4. Update the benchmark table and visual only after the code is validated.

Prefer small commits in this order: startup/tool discovery, toolsets/session
writes, TUI MCP fingerprint, runtime model metadata, delegation/parallel guard,
then docs/images.

## Optimization Matrix

| Optimization | Primary Files | Reference Commits | Verification |
| --- | --- | --- | --- |
| Defer platform plugin imports and speed tool discovery | `hermes_cli/plugins.py`, `model_tools.py`, `tools/registry.py`, `scripts/benchmark_startup_perf.py` | `bfc1de9fc` | `python -m pytest tests\tools\test_registry.py -q` |
| Memoize toolset resolution | `toolsets.py`, `tests/test_toolsets.py` | `bfc1de9fc` | `python -m pytest tests\test_toolsets.py -q` |
| Batch session writes | `hermes_state.py`, `run_agent.py`, `tests/test_hermes_state.py` | `bfc1de9fc`, `4d5aba9d0` | `python -m pytest tests\test_hermes_state.py tests\run_agent\test_compression_persistence.py -q` |
| TUI MCP reload fingerprint | `tui_gateway/server.py`, `ui-tui/src/app/useConfigSync.ts`, `ui-tui/src/gatewayTypes.ts` | `bfc1de9fc` | `python -m pytest tests\test_tui_gateway_server.py::test_config_get_mtime_includes_mcp_fingerprint tests\test_tui_gateway_server.py::test_mcp_config_fingerprint_treats_missing_section_as_empty -q` |
| Dead local endpoint fast path | `agent/model_metadata.py`, `tests/agent/test_model_metadata_local_ctx.py` | `e2834b960` | `python -m pytest tests\agent\test_model_metadata_local_ctx.py -q` |
| Delegation config reuse and heartbeat fix | `tools/delegate_tool.py`, `tests/tools/test_delegate.py`, `tests/tools/test_delegate_subagent_timeout_diagnostic.py` | `dd09b3a43`, `4d5aba9d0` | `python -m pytest tests\tools\test_delegate.py tests\tools\test_delegate_subagent_timeout_diagnostic.py -q` |
| Parallel read-file guard and parsed-arg reuse | `run_agent.py`, `tests/run_agent/test_run_agent.py` | `dd09b3a43` | `python -m pytest tests\run_agent\test_run_agent.py::TestConcurrentToolExecution tests\run_agent\test_run_agent.py::TestParallelScopePathNormalization -q` |
| OpenRouter metadata disk cache | `agent/model_metadata.py`, `hermes_cli/config.py`, `tests/agent/test_model_metadata.py`, `tests/agent/test_openrouter_response_cache.py` | `17435bffb` | `python -m pytest tests\agent\test_model_metadata.py tests\agent\test_openrouter_response_cache.py::TestDefaultConfig -q` |
| 100X README, PR docs, images | `README.md`, `docs/hermes-performance-upstream-pr.md`, `docs/hermes-100x-fast-regression-log.md`, `docs/assets/100x-fast/` | `64710fb1b` through `452b27f9c` | Markdown image path check below |

## Porting Checklist

Use this checklist for every new upstream update.

- Keep `docs/contribution_scout/` untracked unless there is a separate request
  to publish it.
- Do not keep an optimization if upstream already solved the same issue with a
  better or incompatible design.
- Preserve upstream public APIs unless the optimization already has tests that
  cover the compatibility behavior.
- Keep cache files profile-aware with `get_hermes_home()`.
- Keep stale-cache behavior conservative: fresh cache for normal reads, stale
  cache only after refresh failure, and explicit refresh paths preserved.
- Keep gateway/TUI changes fail-open where stale tool state would be worse
  than an extra reload.
- Keep benchmark claims tied to exact commands, old values, new values, and
  scope notes.

## Validation Script

After porting all code, run this focused suite before touching visuals:

```powershell
python -m py_compile hermes_cli\plugins.py model_tools.py tools\registry.py toolsets.py hermes_state.py run_agent.py tui_gateway\server.py agent\model_metadata.py tools\delegate_tool.py scripts\benchmark_startup_perf.py scripts\benchmark_runtime_usage.py
python -m pytest tests\tools\test_registry.py tests\test_toolsets.py tests\test_hermes_state.py -q
python -m pytest tests\test_tui_gateway_server.py::test_config_get_mtime_includes_mcp_fingerprint tests\test_tui_gateway_server.py::test_mcp_config_fingerprint_treats_missing_section_as_empty tests\agent\test_model_metadata_local_ctx.py -q
python -m pytest tests\tools\test_delegate.py tests\tools\test_delegate_subagent_timeout_diagnostic.py -q
python -m pytest tests\run_agent\test_run_agent.py::TestConcurrentToolExecution tests\run_agent\test_run_agent.py::TestParallelScopePathNormalization tests\run_agent\test_tool_executor_contextvar_propagation.py tests\run_agent\test_concurrent_interrupt.py tests\run_agent\test_tool_call_guardrail_runtime.py -q
python -m pytest tests\agent\test_model_metadata.py tests\agent\test_openrouter_response_cache.py::TestDefaultConfig -q
```

Then run benchmarks:

```powershell
python scripts\benchmark_startup_perf.py -n 3
python scripts\benchmark_runtime_usage.py -n 3
python scripts\benchmark_runtime_usage.py --case openrouter_metadata_disk_cache --samples 5
```

If Linux/CI parity matters for the update, run the Docker smoke suite from the
regression log before calling the branch ready.

## Markdown And Image Refresh

After benchmarks change, update all of these together:

- `README.md` visual gallery.
- `docs/hermes-performance-upstream-pr.md` PR body.
- `docs/hermes-100x-fast-regression-log.md` latest validation and benchmark
  sections.
- `docs/hermes-agent-100x-fast-pr.md` detailed implementation notes.
- `docs/assets/100x-fast/*.svg` and generated PNGs when numbers or labels
  change.
- `docs/remotion/100x-fast/` and `docs/assets/100x-fast/video/` when the
  launch video, poster, soundtrack, or storyboard should reflect new numbers.

Run this local image-path check before committing docs:

```powershell
$files = @('README.md','docs\hermes-100x-fast-regression-log.md','docs\hermes-agent-100x-fast-pr.md','docs\runtime-performance-investigation-2026-05-15.md')
$missing = @()
foreach ($file in $files) {
  $base = Split-Path -Parent (Resolve-Path $file)
  if (-not $base) { $base = (Get-Location).Path }
  $text = Get-Content -LiteralPath $file -Raw
  [regex]::Matches($text, '!\[[^\]]*\]\(([^)]+)\)|<img\s+[^>]*src="([^"]+)"') | ForEach-Object {
    $path = if ($_.Groups[1].Value) { $_.Groups[1].Value } else { $_.Groups[2].Value }
    if ($path -and $path -notmatch '^(https?:)?//' -and $path -notmatch '^#') {
      $full = Join-Path $base $path
      if (-not (Test-Path -LiteralPath $full)) { $missing += "$file -> $path" }
    }
  }
}
if ($missing.Count) { $missing; exit 1 } else { 'all local markdown image paths exist' }
```

For the video:

```powershell
cd docs\remotion\100x-fast
npm install
npm run audio
npx tsc --noEmit
npm run still
npm run render
```

The render target is `docs/assets/100x-fast/video/hermes-100x-fast-launch.mp4`.
The composition is 2700 frames at 30fps, so the expected duration is 90 seconds.

## PR Update Template

When opening or updating the next PR, include:

- What upstream version or commit the new branch starts from.
- Which optimizations were already upstream and skipped.
- Which optimizations were re-applied and why.
- Exact focused test results.
- Exact benchmark commands and medians.
- A scope note explaining that 100X is the repository's performance track and
  that each table row owns its own measured gain.

Do not claim universal speedups. Keep the claim tied to the measured hot path:
startup, endpoint probing, session persistence, metadata caching, delegation,
or parallel tool execution.
