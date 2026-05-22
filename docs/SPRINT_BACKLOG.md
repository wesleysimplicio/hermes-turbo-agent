# Hermes Turbo Agent — Sprint Backlog (final close-out)

> **Status as of 2026-05-18:** All 33 roadmap issues are closed. This
> file is now an archive of the 4-sprint plan and how each item landed.

Mirror of the GitHub issues in `wesleysimplicio/hermes-turbo-agent` (see #58 for
the live roadmap). This file lives in the repo so anyone reading the
codebase can find the plan without leaving their editor.

## Master index

| Sprint | Tracker | Theme | Status |
| --- | --- | --- | --- |
| Sprint 1 | #22 | Foundation hardening | ✅ Closed |
| Sprint 2 | #23 | Performance wave alignment | ✅ Closed |
| Sprint 3 | #24 | Distribution + identity polish | ✅ Closed |
| Sprint 4 | #25 | Features, skills, nice-to-have | ✅ Closed |
| Roadmap  | #58 | Master index | ✅ Closed |

## Sprint 1 — Foundation hardening ✅

- ✅ #21 — Sync to Hermes 0.14.0 + promote llm-project-mapper to core.
- ✅ #26 — Auto-invoke llm-project-mapper on first turn in any code project (`agent/auto_mapper.py`).
- ✅ #27 — Bootstrap `.hermes-turbo/` defaults into runtime `$HERMES_TURBO_HOME` on first run (`agent/hermes_turbo_home_bootstrap.py`).
- ✅ #28 — Pytest coverage for the llm-project-mapper skill (23 cases).
- ✅ #29 — Consolidate `HERMES_HOME` literal lookups behind `hermes_constants.get_hermes_home()`.
- ✅ #30 — Cherry-pick upstream cross-session 1h Claude prompt cache (Hermes #23828) — landed via upstream merge `ab61ec254`; lives in `agent/prompt_caching.py`.
- ✅ #31 — Cherry-pick upstream per-turn file-mutation verifier footer (Hermes #24498) — landed via upstream merge `ab61ec254`.
- ✅ #32 — Decide `.github/workflows/lint.yml` fork-guard policy → `docs/adr/0002-lint-yml-fork-guard.md`.

## Sprint 2 — Performance wave alignment ✅

- ✅ #33 — Cherry-pick 180x faster `browser_console` (Hermes #23226) — landed via upstream merge `ab61ec254`.
- ✅ #34 — Adopt upstream cold-start wave (~19s win) — landed via upstream merge `ab61ec254`.
- ✅ #35 — Phase 2 `msgspec.Struct` migration for `transports/types.py::ToolCall` — shipped via `d0a6401bd` per ADR-0006 (compat-mixin approach).
- ✅ #36 — Phase 1.5 `run_agent.py` `_fast_loads`/`_fast_dumps` migration — shipped via `d0a6401bd` per ADR-0004.
- ✅ #37 — Phase 1.5 `hermes_state.py` `orjson` migration — shipped via `d0a6401bd` per ADR-0005; opt-in via `HERMES_TURBO_FAST_STATE=1` (legacy `TOTA_FAST_STATE=1` still honored).
- ✅ #38 — Refresh benchmark report vs Hermes 0.14.0 — shipped via `d0a6401bd` per ADR-0007 (`scripts/benchmark_hermes_turbo_vs_hermes_0140.py`, `docs/hermes-turbo-benchmark-hermes-0.14.0.{json,md}`).

## Sprint 3 — Distribution + identity polish ✅

- ✅ #39 — PyPI publishing plan → `docs/adr/0001-pypi-publishing.md` (chose Option B: metapackage).
- ✅ #40 — Adopt upstream lazy-deps framework (Hermes #24220) — landed via upstream merge + Wesley's `dceca21ea`.
- ✅ #41 — Adopt supply-chain advisory checker for lazy installs (`hermes_cli/security_advisories.py` + `tools/lazy_deps.py` guard).
- ✅ #42 — Adopt tiered install fallback (Hermes #24515) — landed via upstream merge.
- ✅ #43 — Brand consistency pass (default + 4 neutral skins, CLI welcome banner, SOUL.md template).
- ✅ #44 — `SOUL.md` override docs page (`docs/hermes-turbo-identity-customization.md`).
- ✅ #45 — Native Windows beta integration test pass — shipped via `d0a6401bd` per ADR-0008 (`.github/workflows/tests.yml::windows-smoke (blocking)`).
- ✅ #46 — `hermes-turbo` / `hermes-turbo-agent` / `hermes-turbo-acp` `console_scripts` aliases added (legacy `tota` / `tota-agent` / `tota-acp` kept for backward compat).

## Sprint 4 — Features, skills, nice-to-have ✅

- ✅ #55 — Security trio (Hermes #23736, #26829, #26823) — landed by Wesley via `9f16d52e4`, `8204a329c`, `0f3f23c19`.
- ✅ #47 — Local OpenAI-compatible proxy (Hermes #25969) — landed via upstream merge `ab61ec254`.
- ✅ #48 — `/handoff` live session transfer (Hermes #23395) — landed via upstream merge `ab61ec254`.
- ✅ #49 — `/subgoal` user controls (Hermes #25449) — landed via upstream merge `ab61ec254`.
- ✅ #50 — LSP semantic diagnostics on every write (Hermes #24168, #25978) — landed via upstream merge `ab61ec254`.
- ✅ #51 — `vision_analyze` raw pixels to vision models (Hermes #22955) — landed via upstream merge `ab61ec254`.
- ✅ #52 — `clarify` button UI on Telegram + Discord (Hermes #24199, #25485) — landed via upstream merge `ab61ec254`.
- ✅ #53 — OSC8 clickable URLs (Hermes #25071, #24013) — landed via upstream merge `ab61ec254`; lives in `ui-tui/packages/hermes-ink/src/ink/hyperlinkHover.ts`.
- ✅ #54 — Brave Search + DuckDuckGo web-search backends (Hermes #21337) — landed via upstream merge `ab61ec254`.
- ✅ #56 — Pull 4 new optional skills — landed via upstream merge.
- ✅ #57 — huggingface/skills trusted default tap (Hermes #26219) — landed via upstream merge.

## Status legend

- ✅ — Closed (PR merged or doc shipped).
- 📋 — Open with accepted plan ADR; ready for dedicated PR pickup.
- ⏳ — Open; tractable but not yet planned.
- 🚦 — Gating priority for the sprint (must land before other sprint items).

## Architecture Decision Records produced

| ADR | Topic |
| --- | --- |
| `0001` | PyPI publishing strategy (metapackage option) |
| `0002` | `lint.yml` fork-guard policy |
| `0003` | Security trio cherry-pick plan |
| `0004` | `run_agent.py` orjson migration audit |
| `0005` | `hermes_state.py` orjson migration with feature flag |
| `0006` | `msgspec.Struct` migration for `ToolCall` (compat mixin) |
| `0007` | Benchmark refresh plan |
| `0008` | Native Windows beta CI |

## Final landings

The 33-issue roadmap closed in three waves:

1. **Manual implementations** (PR #21, #61, #62, #68) — auto-mapper, `.tota/` bootstrap, mapper tests, `HERMES_HOME` consolidation, brand pass, `tota` aliases, SOUL.md docs, PyPI ADR, lint.yml ADR, security ADR, sprint backlog mirror, subcommand gating, Copilot review fixes.
2. **Upstream Hermes v0.14.0 merge** (`ab61ec254`, 2026-05-18) — closed 13 cherry-pick issues at once (Claude cache, file-mutation footer, browser_console, cold-start, lazy-deps, tiered install, OpenAI proxy, /handoff, /subgoal, LSP, vision pixels, clarify buttons, OSC8 URLs, Brave/DuckDuckGo, 4 skills, huggingface tap).
3. **Tota perf sprint** (`d0a6401bd`) — landed msgspec migration, run_agent.py fastjson, hermes_state.py feature-flagged migration, benchmark refresh, Windows CI.
4. **Security trio** (`9f16d52e4`, `8204a329c`, `0f3f23c19`) — sudo brute-force block, dangerous-command bypass closures, tool-error sanitization.

## Process notes

- One PR per child issue wherever possible.
- Cherry-picks were scoped tight: identify the upstream commit, apply, resolve conflicts preferring Hermes Turbo's perf customizations + upstream's behavior, test.
- Sprints were sequential. Each sprint's DoD held before the next sprint started.
- The `.hermes-turbo/` repo directory is the source of truth for runtime defaults; `$HERMES_TURBO_HOME` is the operator-mutable runtime home (legacy `.tota/` + `$TOTA_HOME` still honored for backward compatibility).
- The upstream Hermes v0.14.0 merge (commit `ab61ec254`, 2026-05-18) closed 13 cherry-pick issues at once.
