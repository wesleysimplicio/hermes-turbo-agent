# Hermes Turbo Agent — Performance Roadmap & Upstream Sync Guide

> **Status:** Living document. Owner: performance branch maintainer.
> **Target repo:** `wesleysimplicio/hermes-turbo-agent`
> **Upstream:** `NousResearch/hermes-agent`
> **Working branch:** `codex/tota-sync-hermes-20260519`
> **Last analysis:** 2026-05-19

---

## Implemented — Phase 1 (2026-05-16)

Drop-in zero-risk wins. All optional with stdlib fallback.

### uvloop (libuv event loop)

Installed as policy before `asyncio.run()` at every CLI entry point:

| Entry point | Function | Location |
|---|---|---|
| `hermes2 gateway` | `start_gateway` wrapper | `hermes_cli/gateway.py` (just before line 3286 `asyncio.run`) |
| `python -m gateway.run` | `main()` | `gateway/run.py` (top of `main`, before stdio config) |
| `hermes-acp` agent | `main()` | `acp_adapter/entry.py` (just before line 282 `asyncio.run`) |

All three wrap the install in `try/except ImportError` so Windows / Termux installs without uvloop still boot.

Expected: 20-40% I/O throughput gain on the gateway message loop and ACP agent loop.

### orjson (fast JSON)

A thin shim at `agent/_fastjson.py` exposes `loads` / `dumps` with orjson under the hood and stdlib fallback. Migrated hot paths:

| File | Sites | Why hot |
|---|---|---|
| `agent/context_compressor.py` | 3 (`_truncate_tool_call_args_json`, `_summarize_tool_result`) | Per-message, runs on every turn that crosses the budget |
| `agent/tool_result_classification.py` | 1 (`file_mutation_result_landed`) | Per-tool-result, runs on every tool call that returns JSON |

Expected: 2-10x faster decode/encode on those paths. `run_agent.py` migration deferred to Phase 1.5 — many call sites use `strict=False` and `separators=(",", ":")` which orjson does not accept; needs a dedicated audit. `hermes_state.py` deferred similarly: round-trip safety with SQLite-stored JSON columns must be audited before swapping.

### msgspec.Struct

Evaluated for `agent/transports/types.py::ToolCall` and **deferred**. Rationale: 45+ read sites in `run_agent.py` rely on `tc.function.name` / `tc.function.arguments` (back-compat property), plus one mutation site (`tc.function.arguments = json.dumps(args)` near `run_agent.py:14999`). Migrating to `msgspec.Struct` is a Phase 2 task that needs to land alongside an audit of those sites. The dep is installed and ready.

### Scripts

- `scripts/sync-upstream.sh` — safe rebase onto `upstream/main`, takes a snapshot tag before the rebase, prints a post-sync checklist.
- `scripts/apply-to-hermes2.sh` — rsync the repo into `~/.hermes2/hermes-agent` and `launchctl kickstart` the gateway. One-command deploy from a clean checkout.

### Config

- `.gitattributes` carries `merge=ours` entries for files that must never be overwritten on upstream merge: `hermes_cli/default_soul.py`, `hermes_cli/config.py`, `PERFORMANCE_ROADMAP.md`, both new scripts, `.gitattributes`, `pyproject.toml`, `agent/_fastjson.py`.
- `git config merge.ours.driver true` activates the driver locally (the sync script sets this idempotently).
- Upstream remote: `https://github.com/NousResearch/hermes-agent.git`, push URL forced to `no_push` so accidental `git push upstream` is impossible.
- `pyproject.toml` gains an optional `[perf]` extra: `uvloop`, `orjson`, `msgspec`. `pip install -e '.[perf]'` to enable.

### How to use

```bash
# Pull upstream updates without losing customizations
./scripts/sync-upstream.sh

# Deploy current branch into ~/.hermes2/hermes-agent + restart gateway
./scripts/apply-to-hermes2.sh
```

---

## 0. Executive Summary

`hermes-agent` is a Python 3.11+ multi-provider AI agent + gateway. Profile of the codebase:

- **~818k Python LOC** across ~600 files
- **Three monoliths:** `gateway/run.py` (17k), `run_agent.py` (16k), `cli.py` (14k)
- **Workload is overwhelmingly I/O-bound** (HTTP/SSE to LLM providers, websockets to chat platforms)
- **CPU-bound hot spots** are concentrated in: streaming JSON tool-call assembly, trajectory/context compression, message routing, and config loading
- **No native vector store / embedding stack** is in the critical path (voice mode uses `numpy` but only when active)

The fork already carries two performance-oriented commits (`feat: cache hierárquico`, `feat: context retention`). This roadmap extends that work along three vectors:

1. Drop-in Python wins (uvloop, msgspec, orjson, lazy imports, mmap)
2. Native (Rust via PyO3) rewrites of CPU-bound hot loops
3. Selective Go rewrite of the gateway message router *only if* benchmarks justify it

It also documents a reproducible upstream-sync workflow with explicit `ours-only` files that must never be overwritten by an upstream merge.

---

## 1. Module-by-Module Analysis (Rust via PyO3 Candidates)

Methodology: ranked by `LOC × call-frequency × CPU-share`. Frequency tiers — **per-token** (every stream chunk), **per-message** (every user turn), **per-session** (warm path), **per-boot** (cold path).

### 1.1 Top candidates

| # | File | LOC | Workload | Frequency | Expected gain | Migration | Blockers | Priority |
|---|------|-----|----------|-----------|---------------|-----------|----------|----------|
| 1 | `agent/transports/chat_completions.py` (+ streaming assembler in `run_agent.py`) | 614 + ~2k | Parse SSE chunks, deep-merge tool-call deltas, JSON repair | **per-token** | -40-60% CPU on stream loop, -20-30ms p99 per turn | **Medium** — pure data manipulation, no I/O | Pydantic models for `NormalizedResponse` cross the boundary | **5** |
| 2 | `trajectory_compressor.py` | 1508 | Trajectory replay, dedupe, token estimation, summarization scheduling | per-session, per-compaction | -50-70% on `compress()` hot path | **Medium-High** — heavy data shaping, references many `agent/` helpers | Calls back into Python for LLM calls (boundary at summarization) | **4** |
| 3 | `agent/context_compressor.py` | 1583 | Per-message budget enforcement, tool-result truncation, image-part stripping, regex scans | **per-message** | -30-50% on hot turns, larger wins on long sessions | **Medium** — already mostly pure functions (`_truncate_tool_call_args_json`, `_summarize_tool_result`) | Inherits from `ContextEngine`; needs trait abstraction in Rust | **5** |
| 4 | `hermes_state.py` | 130k bytes (~3k LOC) | Disk-backed state read/write, large JSON ser/deser | per-message + per-boot | -60-80% on state I/O (msgpack/orjson + Rust writer) | **Medium** — mostly mechanical | TOCTOU lock semantics on Windows (recent fix `7fee1f61e`) — must preserve | **4** |
| 5 | `agent/memory_manager.py` (`StreamingContextScrubber`) | 555 | Stream-time redaction (regex sweep over tokens) | **per-token** | -25-40% on scrubber loop | **Low-Medium** — pure regex + state | None — pure CPU | **5** |
| 6 | `gateway/config.py` (load + validate) | 1873 | YAML + env merge + cross-field validation at boot | per-boot, per-restart | -200-500ms boot time | **Low** — straight data shaping | YAML lib (ruamel.yaml) is heavy — replace with `serde_yaml` via Rust | **3** |
| 7 | `agent/think_scrubber.py` / `agent/redact.py` | ~600 combined | Regex-heavy redaction passes | per-message | -30-40% on redact passes | **Low** — pure regex | None | **3** |
| 8 | `agent/prompt_caching.py` + `agent/prompt_builder.py` | ~1500 | Build prompt + cache-key hashing | per-message | -10-15% per turn | **Low** | None | **2** |
| 9 | `tools/skills_guard.py` (Unicode/BiDi scanner, tables at 518-867) | 1500+ | Char-by-char scan for invisible/BiDi chars | per-tool-result | -70-90% on scanner | **Low** — perfect Rust target | None | **3** |
| 10 | `agent/tool_guardrails.py` | ~500 | Argument schema validation | per-tool-call | -20-30% | **Medium** — leans on pydantic | Pydantic boundary | **2** |

> **Out of scope for native rewrite (intentionally):** Discord/Telegram/Feishu/Matrix adapters (I/O-bound, library-coupled), `run_agent.py` orchestration (mostly glue), `cli.py` (interactive UI), all LLM provider adapters (HTTP, not CPU).

### 1.2 PyO3 boundary design

A single Rust crate, **`hermes_native`**, exposed as a Python extension. Suggested module map:

```
hermes_native/
├── Cargo.toml
├── pyproject.toml          # maturin
├── src/
│   ├── lib.rs              # #[pymodule] registration
│   ├── streaming/          # SSE chunk parser, tool-call deep-merge
│   ├── compression/        # trajectory + context compression
│   ├── scrubber/           # streaming redaction
│   ├── state/              # hermes_state binary format
│   ├── guardrails/         # skills_guard unicode scanner
│   └── codec/              # msgspec-style decoders (re-export simd-json)
```

**Migration order (dependency-respecting):**

1. **Phase A — codec primitives.** `streaming` + `scrubber`. Both are leaf modules with no Python callbacks. Validate the PyO3 toolchain end-to-end without touching business logic.
2. **Phase B — `state`.** Replace `json.loads/dumps` over hermes_state's on-disk format with a Rust reader/writer that keeps JSON-on-disk for compatibility, then optionally switches to a binary format behind a feature flag.
3. **Phase C — `compression`.** Trajectory + context. Largest payoff. Requires careful boundary design so summarization (which calls an LLM) stays in Python.
4. **Phase D — `guardrails` + ancillary.** Lower priority, parallelizable.

**Build/distribution:** use `maturin develop` for local dev, `maturin build --release --strip` for wheels. Add `cibuildwheel` matrix for the three primary targets (Linux x86_64, Linux aarch64, macOS arm64, macOS x86_64, Windows x86_64). Ship as an **optional extra** (`hermes-agent[native]`) so source builds and Termux users keep working.

---

## 2. Other Languages & Approaches

Each option below is evaluated against the actual workloads in this repo, not generic "language X is fast" claims.

### 2.1 Rust via PyO3 — *primary recommendation*

- **Use for:** CPU-bound parsers, compressors, regex/Unicode scanners (Section 1).
- **Pros:** Best-in-class single-thread performance; mature PyO3 + maturin tooling; safe concurrency for batch operations; cross-platform wheels via `cibuildwheel`.
- **Cons:** Build toolchain becomes mandatory in CI; ABI compatibility per Python minor; debugging crosses two languages.
- **When:** any module on the per-token or per-message hot path that's pure data (no awaits, no I/O).
- **Concrete deps already in the ecosystem:** `simd-json`, `serde_json`, `regex` (Rust), `aho-corasick`, `zstd`.

### 2.2 Go — *gateway message router (conditional)*

- **Use for:** would only pay off if the asyncio gateway became a measured bottleneck under high fan-out (e.g., 500+ concurrent Discord guilds).
- **Pros:** Excellent concurrent I/O, single-binary deploy, sub-ms goroutine scheduling, mature `discordgo` library.
- **Cons:** Forking the gateway off Python breaks the in-process integration with `agent/`, `hermes_state.py`, hooks, and slash command registration. Cross-process IPC (gRPC/unix-socket) would re-add latency and complexity. Loses Python's plugin ecosystem (slack-bolt, telegram-bot, matrix-mautrix).
- **When:** **not now.** Pre-condition: a benchmark proving the asyncio router is the bottleneck *after* uvloop + msgspec are in place. Even then, prefer a Rust extension that handles message fan-out + state lookup, keeping the platform adapters in Python.
- **Verdict:** parked. Revisit only with a numbered, reproducible benchmark.

### 2.3 C extension (Cython / cffi)

- **Use for:** none in this repo today.
- **Pros:** Smaller per-module overhead than PyO3 for tiny hot loops; no extra build toolchain on Linux.
- **Cons:** Cython generates C from Python-like syntax — gives modest 2-5x on numeric loops but no concurrency story; cffi requires hand-written C. Rust+PyO3 covers the same use cases with better tooling and a safer language.
- **When:** legacy modules where a one-file `.pyx` annotation gives a quick win without restructuring. Not justified here given the size of the candidate modules.
- **Verdict:** skip.

### 2.4 Zig

- **Use for:** ultra-tight low-level loops; embedded environments.
- **Pros:** No GC; comptime; small binaries; great for `comptime`-known schemas.
- **Cons:** Pre-1.0 ABI churn; no equivalent of PyO3's ergonomic Python bindings (`ziggy-pydust` exists but is young); ecosystem (regex, simd-json equivalents) is thinner than Rust's.
- **When:** an experimental rewrite of one isolated scrubber as a learning exercise, not for production.
- **Verdict:** skip for v1.

### 2.5 WebAssembly (WASM)

- **Use for:** would only help the `web/` and `website/` directories (browser-side UI), not the agent or gateway.
- **Pros:** lets a single Rust crate also run in the browser TUI / web dashboard.
- **Cons:** the agent is server-side; WASM adds nothing to the actual hot paths.
- **When:** if `web/` ever needs client-side trajectory rendering, compile the existing `hermes_native` compressor to `wasm32-unknown-unknown` and reuse the same code. Future-proofing dividend, not an action item now.
- **Verdict:** opportunistic.

### 2.6 Numba / Cython for numeric paths

- **Use for:** the voice mode (`tools/voice_mode.py`) numpy resampling and STT pre-processing.
- **Pros:** 5-50x on numpy-heavy kernels with one decorator.
- **Cons:** First-call JIT cost (Numba), packaging complexity, dead weight when voice mode is off (most users).
- **When:** only if voice mode users report measurable latency in capture/playback. Today voice mode is opt-in and `numpy` is lazy-loaded — no payoff.
- **Verdict:** skip unless a voice user reports lag.

### 2.7 Multiprocessing + shared memory

- **Use for:** never in the agent loop (state coherence + LLM call ordering rule it out). Possibly justified for `batch_runner.py` (offline evaluation).
- **Pros:** sidesteps the GIL without leaving Python; shared-memory `multiprocessing.shared_memory` avoids pickle for large arrays.
- **Cons:** Inter-process IPC overhead dominates for short-lived hot paths; fork/spawn complexity on Windows; debugging multi-process Python is painful.
- **When:** `batch_runner.py` scaling out evals to N workers — already partially handled by `pytest-xdist` in tests. Outside agent's request loop.
- **Verdict:** keep current use, do not extend.

### 2.8 uvloop — *drop-in event loop replacement*

- **Use for:** **immediate adoption** in `gateway/run.py` and any long-running asyncio entry-point.
- **Pros:** 2-4x throughput on asyncio workloads with zero code change beyond `uvloop.install()`. Backed by libuv, battle-tested in `aiohttp` server stacks.
- **Cons:** Linux/macOS only — must fall back to default loop on Windows. Adds a binary wheel dependency.
- **When:** **now.** Estimated effort: half a day including a Windows guard and a benchmark.
- **Verdict:** **Phase 1.** Pin `uvloop==0.21.0` as optional, guard with `sys.platform`.

### 2.9 msgspec — *Pydantic + json replacement*

- **Use for:** `NormalizedResponse`, `ToolCall`, `Usage` (`agent/transports/types.py`), `gateway/config.py` dataclasses, `agent/context_references.py`, plus every `json.loads/dumps` hot site in `agent/` and `gateway/`.
- **Pros:** 10-80x faster than `pydantic` for validation; 5-20x faster than stdlib `json` for ser/deser; zero-copy decoding into `msgspec.Struct`; supports JSON, MessagePack, YAML; written in C.
- **Cons:** `msgspec.Struct` is not `pydantic.BaseModel` — drop-in is not literal, need a converter layer or a parallel definition. Some pydantic features (validators, computed fields) don't have direct equivalents.
- **When:** **now**, incrementally. Start with leaf data classes (`types.py`), then expand to internal-only payloads. Keep `pydantic` for any model that crosses the OpenAI SDK boundary (the SDK itself uses pydantic).
- **Verdict:** **Phase 1.** Highest impact-to-effort ratio in the entire roadmap.

### 2.10 orjson — *json drop-in*

- **Use for:** any `json.dumps`/`json.loads` that doesn't need pydantic-level validation.
- **Pros:** 2-10x faster than stdlib `json`; serializes `dict`, `list`, `datetime`, `UUID` natively; minimal API surface.
- **Cons:** Returns `bytes` from `dumps()`, not `str` — calling sites need `.decode()` or `orjson.dumps(...).decode("utf-8")`.
- **When:** **now.** Wrap behind a small `agent/_fastjson.py` shim that falls back to stdlib if `orjson` not installed. Migrate hot files first (`gateway/session.py`, `hermes_state.py`, `agent/context_compressor.py`).
- **Verdict:** **Phase 1.** Trivial.

### 2.11 Additional drop-ins worth listing

- **`zstandard`** (or `lz4`) for trajectory persistence — replace any `gzip` use in `hermes_state.py` for 3-5x faster compression at higher ratios.
- **`xxhash`** for cache keys (`agent/prompt_caching.py`) — 10x faster than `hashlib.sha256` when collision resistance isn't a security requirement.
- **`uvicorn[standard]` + `httptools`** for `tui_gateway/server.py` and `web/` HTTP servers.
- **`stamina`** as a tenacity replacement — already use `tenacity==9.1.4`, no urgency.
- **Lazy imports.** `cli.py` is 642 KB. Profile cold start with `python -X importtime` and push provider-specific imports inside their respective code paths (Anthropic SDK, edge-tts, fal-client, etc. already gated via `tools/lazy_deps.py` — extend the pattern).

---

## 3. Upstream Sync Strategy

The fork must absorb upstream's bug fixes, provider additions, and security patches *without losing the performance customizations*. This section is the canonical procedure.

### 3.1 Topology

```
NousResearch/hermes-agent  (upstream, main)
              │
              │  scripts/sync-upstream.sh  (rebase or merge)
              ▼
wesleysimplicio/hermes-agent-100x-fast  (origin)
              │
              │  branches:
              │    • main                        (mirror of upstream main)
              │    • codex/hermes-agent-100x-fast (default — performance work)
              │    • feature/* fix/* docs/*     (PR branches off the codex branch)
              ▼
Active development happens on feature branches → PR into codex/hermes-agent-100x-fast.
```

### 3.2 Remote configuration

One-time setup on every clone:

```bash
# Inside the repo
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git remote set-url --push upstream DISABLE  # safety: never push to upstream
git fetch upstream --tags
git config remote.upstream.tagopt --no-tags  # avoid tag clobber on every fetch
```

Verify with `git remote -v`. Expected:

```
origin    https://github.com/wesleysimplicio/hermes-agent-100x-fast.git (fetch)
origin    https://github.com/wesleysimplicio/hermes-agent-100x-fast.git (push)
upstream  https://github.com/NousResearch/hermes-agent.git (fetch)
upstream  DISABLE (push)
```

### 3.3 Rebase vs Merge — which to use

| Situation | Strategy | Rationale |
|-----------|----------|-----------|
| Routine weekly catch-up, codex branch has only a handful of unpublished commits | **Rebase** (`git rebase upstream/main`) | Linear history, easier conflict review one commit at a time |
| Codex branch already has many published commits and open PRs | **Merge** (`git merge --no-ff upstream/main`) | Rewriting public history breaks every open PR and contributor checkout |
| Upstream did a large refactor that touches our `ours-only` files | **Merge with `-X ours`** then manually re-apply changes | Halts upstream from clobbering customizations, then cherry-pick the parts to keep |
| Cherry-picking a single upstream security fix | `git cherry-pick <sha>` | Surgical, doesn't pull in unrelated changes |

**Default = merge** for this fork, because `codex/hermes-agent-100x-fast` is the public default branch and has open PRs against it.

### 3.4 `ours-only` files — never overwrite from upstream

These files contain performance customizations and must survive every sync. The sync script enforces this via `git checkout --ours` after the merge.

| Path | Reason |
|------|--------|
| `PERFORMANCE_ROADMAP.md` | This document |
| `~/.hermes2/PERFORMANCE_ROADMAP.md` (out-of-tree mirror) | Local copy for fast lookup |
| `hermes_cli/default_soul.py` (SOUL.md defaults) | Custom system prompt baseline |
| `gateway/config.py` (default values + cache-hierarchy fields) | Cache hierarchy + retention defaults |
| `agent/transports/chat_completions.py` (streaming patch) | Tool-call streaming repair logic |
| `agent/context_compressor.py` + `agent/context_engine.py` | Context retention system |
| `agent/context_references.py` | Persistent context store |
| `agent/prompt_caching.py` (parallel_tool_calls patch) | Cache-key parallelization |
| Context-window settings inside `agent/model_metadata.py` | Custom per-model context limits |
| Any future `hermes_native/` Rust crate | Native extension code |
| `scripts/sync-upstream.sh` | The sync script itself |
| `CHANGELOG.md` fork-specific entries | Performance changelog |

**Add a `.gitattributes` rule** to mark these as merge-strategy `ours` (already partially used via `.gitattributes` in the repo):

```gitattributes
PERFORMANCE_ROADMAP.md           merge=ours
hermes_cli/default_soul.py       merge=ours
agent/context_compressor.py      merge=ours
agent/context_engine.py          merge=ours
agent/context_references.py      merge=ours
agent/prompt_caching.py          merge=ours
scripts/sync-upstream.sh         merge=ours
```

Activate the `ours` driver locally (must be done on every clone, git doesn't ship it by default):

```bash
git config merge.ours.driver true
```

### 3.5 Conflict-detection workflow

After a merge, before any commit:

```bash
# 1. List conflicted files
git diff --name-only --diff-filter=U

# 2. For each ours-only file that conflicted, force our version
for f in $(cat scripts/ours-only-files.txt); do
  git checkout --ours -- "$f"
  git add "$f"
done

# 3. For non-ours files, resolve normally (manual)

# 4. Sanity check: ensure no ours-only file was silently overwritten
scripts/sync-upstream.sh verify
```

### 3.6 `scripts/sync-upstream.sh`

```bash
#!/usr/bin/env bash
# scripts/sync-upstream.sh — sync from NousResearch/hermes-agent into the
# performance fork while protecting ours-only files.
#
# Usage:
#   sync-upstream.sh              # merge upstream/main into current branch
#   sync-upstream.sh --rebase     # rebase instead of merge (only if branch is unpublished)
#   sync-upstream.sh --dry-run    # show what would change, don't merge
#   sync-upstream.sh verify       # check ours-only files were not clobbered by last merge

set -euo pipefail

UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
PROTECTED_FILES=(
  "PERFORMANCE_ROADMAP.md"
  "hermes_cli/default_soul.py"
  "gateway/config.py"
  "agent/transports/chat_completions.py"
  "agent/context_compressor.py"
  "agent/context_engine.py"
  "agent/context_references.py"
  "agent/prompt_caching.py"
  "agent/model_metadata.py"
  "scripts/sync-upstream.sh"
)

die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo "[sync] $*"; }

ensure_clean_tree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    die "working tree not clean — commit or stash first"
  fi
}

ensure_upstream() {
  if ! git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
    info "adding upstream remote"
    git remote add "$UPSTREAM_REMOTE" https://github.com/NousResearch/hermes-agent.git
    git remote set-url --push "$UPSTREAM_REMOTE" DISABLE
  fi
}

snapshot_protected() {
  local dir="$1"
  mkdir -p "$dir"
  for f in "${PROTECTED_FILES[@]}"; do
    if [[ -f "$f" ]]; then
      mkdir -p "$dir/$(dirname "$f")"
      cp "$f" "$dir/$f"
    fi
  done
}

verify_protected() {
  local snap_dir="$1"
  local diffs=0
  for f in "${PROTECTED_FILES[@]}"; do
    if [[ -f "$snap_dir/$f" && -f "$f" ]]; then
      if ! diff -q "$snap_dir/$f" "$f" >/dev/null; then
        echo "  CHANGED: $f"
        diffs=$((diffs + 1))
      fi
    fi
  done
  return $diffs
}

cmd_verify() {
  local snap=".git/sync-upstream-snapshot"
  [[ -d "$snap" ]] || die "no snapshot found (run a sync first)"
  if verify_protected "$snap"; then
    info "all protected files intact"
  else
    die "protected files were modified by the last sync — restore from $snap"
  fi
}

cmd_sync() {
  local mode="$1"   # merge | rebase | dry-run
  ensure_upstream
  ensure_clean_tree
  info "fetching upstream"
  git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH"

  local snap=".git/sync-upstream-snapshot"
  rm -rf "$snap"
  snapshot_protected "$snap"

  local target="$UPSTREAM_REMOTE/$UPSTREAM_BRANCH"

  case "$mode" in
    dry-run)
      info "commits upstream is ahead by:"
      git log --oneline "HEAD..$target" | head -50
      info "files that would change:"
      git diff --name-only "HEAD..$target" | head -100
      ;;
    rebase)
      info "rebasing onto $target"
      git rebase "$target" || die "rebase had conflicts — resolve, then re-run with verify"
      ;;
    merge)
      info "merging $target (--no-ff)"
      git merge --no-ff "$target" -m "Merge upstream/main into $(git rev-parse --abbrev-ref HEAD)" || true
      # Force ours-only on conflicted protected files
      for f in "${PROTECTED_FILES[@]}"; do
        if git status --porcelain "$f" 2>/dev/null | grep -q "^UU"; then
          info "protected file $f had a conflict — keeping ours"
          git checkout --ours -- "$f"
          git add "$f"
        fi
      done
      if [[ -n "$(git ls-files -u)" ]]; then
        die "non-protected conflicts remain — resolve manually then 'git commit'"
      fi
      # Finalize the merge if it was paused only by protected-file conflicts
      if [[ -f .git/MERGE_HEAD ]]; then
        git commit --no-edit
      fi
      ;;
  esac

  info "verifying protected files"
  verify_protected "$snap" || die "protected file diverged — review $snap"
  info "sync complete"
}

main() {
  case "${1:-}" in
    verify)    cmd_verify ;;
    --rebase)  cmd_sync rebase ;;
    --dry-run) cmd_sync dry-run ;;
    "" | --merge) cmd_sync merge ;;
    *) die "unknown arg: $1" ;;
  esac
}

main "$@"
```

Make executable: `chmod +x scripts/sync-upstream.sh`.

### 3.7 Post-sync validation checklist

After every sync, before merging the resulting commit into the working branch:

1. **Unit + integration tests:** `uv run pytest -x -q` (or `scripts/run_tests.sh`). Must be green.
2. **Lint:** `uv run ruff check .` and `uv run ruff format --check .`. Must be clean.
3. **Lockfile coherence:** `uv lock --check` (catches transitives drift after pin bumps).
4. **`hermes_native` build** (if present): `maturin build --release` on the dev machine; CI matrix wheels on push.
5. **Gateway smoke test:** `hermes gateway start --dry-run` succeeds; `hermes gateway start` boots without exceptions; one Discord message round-trips.
6. **Streaming smoke test:** `hermes oneshot "say hi" --model openrouter/anthropic/claude-3.5-sonnet` produces a complete reply with no `_TOOL_CALL_ARGUMENTS_CORRUPTION_MARKER` regressions.
7. **Context-retention smoke test:** start a session, exchange 3 messages, restart agent, verify recall of message 1.
8. **Protected-file diff:** `scripts/sync-upstream.sh verify` reports all-intact.
9. **Performance regression check:** run `scripts/benchmark_runtime_usage.py` and compare against the previous baseline checked into `benchmarks/baseline.json`. Fail if any p95 regresses >10%.
10. **Update changelog:** add an entry under `## [Unreleased]` describing the sync and any conflict resolutions.

Automate steps 1-4 and 8-9 in `.github/workflows/sync-upstream.yml` triggered on push to a `sync/upstream-*` branch.

### 3.8 Versioning policy after a sync

Hermes uses SemVer (currently `0.13.0`). After a sync:

| Upstream content | Fork version bump | Example |
|------------------|-------------------|---------|
| Only bug fixes / docs | **Patch** | `0.13.0` → `0.13.1` |
| New provider / new gateway platform / new feature | **Minor** | `0.13.1` → `0.14.0` |
| Breaking API change (rare on `0.x.y`) or major refactor | **Minor** (still `0.x`) but call out under `### Changed (breaking)` in the changelog | `0.14.0` → `0.15.0` |
| Fork-only performance commit landing on top of an unchanged upstream | **Patch** | `0.13.1` → `0.13.2` |
| Native extension shipped for the first time | **Minor** + add `[native]` extra to pyproject | `0.14.0` → `0.15.0` |

Always bump `pyproject.toml::project.version` in the same commit as the changelog entry. Tag with `v0.X.Y` and push tags after merging into the working branch.

---

## 4. Implementation Roadmap

Three phases, each with a measurable success criterion. Phases overlap only where explicitly noted.

### Phase 1 — Drop-in Python wins (target: 2 weeks)

**Goal:** -30% p99 turn latency, -25% boot time, zero new toolchain dependencies for end users.

Tasks (independent, parallelizable):

1. **uvloop adoption** (1 day)
   - Add `uvloop==0.21.0` to `[messaging]` and `gateway` extras
   - In `gateway/run.py` early bootstrap: `if sys.platform != "win32": import uvloop; uvloop.install()`
   - Bench: `scripts/benchmark_runtime_usage.py` with N=1000 simulated messages.
2. **msgspec migration — leaf types** (3 days)
   - Convert `agent/transports/types.py` `NormalizedResponse`, `ToolCall`, `Usage` to `msgspec.Struct`
   - Add a `to_dict()` shim where consumers expect dicts
   - Cover with existing tests; add `tests/transports/test_types_msgspec.py`
3. **orjson shim** (1 day)
   - New `agent/_fastjson.py` exporting `dumps`/`loads` with fallback
   - Migrate `gateway/session.py`, `hermes_state.py`, `agent/context_compressor.py`
4. **xxhash for cache keys** (0.5 day)
   - `agent/prompt_caching.py`: replace sha256 with `xxhash.xxh3_64_hexdigest` for non-security uses
5. **Lazy-import audit of `cli.py`** (2 days)
   - Profile with `python -X importtime hermes --help 2>importtime.log`
   - Push provider SDK imports inside provider-specific code paths
6. **Benchmarks baseline** (1 day)
   - Capture pre/post numbers in `benchmarks/baseline.json`
   - Wire into CI via `.github/workflows/perf-regression.yml`

**Success criterion:** `scripts/benchmark_runtime_usage.py` p95 turn latency drops ≥25% vs. pre-Phase-1 baseline on a fixed scenario; `hermes --help` cold start drops ≥30%.

### Phase 2 — Native extension scaffolding + leaf modules (target: 4-6 weeks)

**Depends on:** Phase 1 complete (so benchmarks compare against the already-improved baseline).

**Goal:** ship `hermes-agent[native]` extra with `streaming` + `scrubber` modules; -30% per-token CPU.

Tasks (sequential):

1. **Toolchain & repo plumbing** (1 week)
   - Create `hermes_native/` crate (maturin layout)
   - Add `cibuildwheel` matrix (Linux x86_64+aarch64, macOS arm64+x86_64, Windows x86_64) in `.github/workflows/native-wheels.yml`
   - PyO3 abi3 build for Python ≥3.11 forward compat
2. **`streaming` module** (1.5 weeks)
   - Port SSE chunk parser + tool-call delta deep-merge
   - Behind a `HERMES_NATIVE_STREAMING=1` env flag with full Python fallback
   - Property-based tests (`hypothesis`) ensuring native and pure-Python paths produce identical `NormalizedResponse`
3. **`scrubber` module** (1 week)
   - Port `StreamingContextScrubber`
   - Same fallback + property-test discipline
4. **Bench + ship** (0.5 week)
   - Compare p95 per-token CPU on a 10k-token stream
   - Update CHANGELOG, bump to minor

**Success criterion:** native path active in CI; per-token CPU drops ≥30% vs. Phase 1 baseline; ≥99.9% byte-identical output on a 10k random-stream property-test corpus.

### Phase 3 — Native compression + state (target: 6-8 weeks)

**Depends on:** Phase 2 (proves the boundary works).

**Goal:** native trajectory + context compression + state I/O; -50% session-end compaction time, -60% state read/write.

Tasks:

1. **`hermes_state` binary path** (2 weeks) — keep JSON on disk by default; add `HERMES_STATE_FORMAT=binary` for opt-in.
2. **`compression` module** (3 weeks) — port `TrajectoryCompressor` and `ContextCompressor` pure-CPU phases; leave LLM-summarization calls in Python.
3. **`guardrails` module** (1 week) — `skills_guard` Unicode/BiDi scanner.
4. **Bench + ship** (1 week).

**Success criterion:** end-of-session compaction p95 drops ≥40%; hermes_state read/write p95 drops ≥50%; zero correctness regressions on the full pytest suite.

### Phase 4 — Conditional Go gateway (target: open-ended, only if justified)

**Depends on:** Phases 1-3 in production for 4+ weeks with telemetry.

**Trigger:** measured p95 gateway-routing latency >100ms under realistic load, *or* operator reports of asyncio backpressure on the message bus.

**Goal:** decision document, not code. Either commit to the Go rewrite with a scoped MVP (Discord only, IPC over unix-socket to the Python agent) or close the door with a written rationale.

**Success criterion:** decision recorded as an ADR (`.specs/architecture/ADR-XXX-gateway-language.md`).

---

## 5. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Native wheel build fails on a target platform | Medium | High | abi3, cibuildwheel matrix in CI, source-build fallback documented |
| Termux / Android users can't install native extras | High (for that cohort) | Medium | Native is opt-in extra; pure-Python remains the default path |
| Upstream refactors a hot-path file we'd already ported | Medium | High | `ours-only` policy + property tests catch drift early |
| msgspec dropped maintenance | Low | Medium | Keep pydantic fallback for cross-boundary types |
| Performance gains masked by LLM latency | Certain | Medium | All benchmarks must report CPU-only and end-to-end separately |
| Sync script clobbers a customization not on the protected list | Medium | High | Manual review of every sync diff; expand list as customizations grow |

---

## 6. Telemetry & Continuous Monitoring

To keep these gains from rotting:

- `scripts/benchmark_runtime_usage.py` runs in CI on every PR to `codex/hermes-agent-100x-fast`; fails if p95 regresses >10% vs. `benchmarks/baseline.json`.
- `scripts/benchmark_startup_perf.py` similarly gates cold-start regressions.
- A weekly scheduled GitHub Action (`perf-trend.yml`) re-runs all benchmarks on main and posts results to a tracked discussion thread.

---

## 7. References

- Upstream repo: https://github.com/NousResearch/hermes-agent
- This fork: https://github.com/wesleysimplicio/hermes-agent-100x-fast
- PyO3: https://pyo3.rs/
- maturin: https://www.maturin.rs/
- msgspec: https://jcristharif.com/msgspec/
- uvloop: https://github.com/MagicStack/uvloop
- orjson: https://github.com/ijl/orjson
- cibuildwheel: https://cibuildwheel.readthedocs.io/

---

*End of roadmap. Updates to this document are themselves protected by the `ours-only` rule in `scripts/sync-upstream.sh`.*
