# Hermes Turbo Agent — Sprint Backlog

Mirror of the GitHub issues in `wesleysimplicio/tota-agent` (see #58 for
the live roadmap). This file lives in the repo so anyone reading the
codebase can find the plan without leaving their editor.

## Master index

| Sprint | Tracker | Theme |
| --- | --- | --- |
| Sprint 1 | #22 | Foundation hardening |
| Sprint 2 | #23 | Performance wave alignment |
| Sprint 3 | #24 | Distribution + identity polish |
| Sprint 4 | #25 | Features, skills, nice-to-have |
| Roadmap  | #58 | Master index |

## Sprint 1 — Foundation hardening

- ✅ #21 — Sync to Hermes 0.14.0 + promote llm-project-mapper to core.
- ✅ #26 — Auto-invoke llm-project-mapper on first turn in any code project (`agent/auto_mapper.py`).
- ✅ #27 — Bootstrap `.tota/` defaults into runtime `$TOTA_HOME` on first run (`agent/tota_home_bootstrap.py`).
- ✅ #28 — Pytest coverage for the llm-project-mapper skill (23 cases).
- ✅ #29 — Consolidate `HERMES_HOME` literal lookups behind `hermes_constants.get_hermes_home()`.
- ✅ #30 — Cherry-pick upstream cross-session 1h Claude prompt cache (Hermes #23828) — landed via upstream merge `ab61ec254`; lives in `agent/prompt_caching.py`.
- ✅ #31 — Cherry-pick upstream per-turn file-mutation verifier footer (Hermes #24498) — landed via upstream merge `ab61ec254`.
- ✅ #32 — Decide `.github/workflows/lint.yml` fork-guard policy → `docs/adr/0002-lint-yml-fork-guard.md`.

## Sprint 2 — Performance wave alignment

- ✅ #33 — Cherry-pick 180x faster `browser_console` (Hermes #23226) — landed via upstream merge `ab61ec254`.
- ✅ #34 — Adopt upstream cold-start wave (~19s win) — landed via upstream merge `ab61ec254`.
- ⏳ #35 — Phase 2 `msgspec.Struct` migration for `transports/types.py::ToolCall`. High-risk; needs dedicated PR.
- ⏳ #36 — Phase 1.5 `run_agent.py` `orjson` migration. Needs per-site `strict=False` audit.
- ⏳ #37 — Phase 1.5 `hermes_state.py` `orjson` migration + SQLite round-trip audit. Highest-risk; behind `TOTA_FAST_STATE=1` feature flag.
- ⏳ #38 — Refresh `tota_agent_benchmark_report.pdf` post-merge. Needs runtime benchmarking environment.

## Sprint 3 — Distribution + identity polish

- ✅ #39 — PyPI publishing plan → `docs/adr/0001-pypi-publishing.md` (chose Option B: metapackage).
- ✅ #40 — Adopt upstream lazy-deps framework (Hermes #24220) — landed via upstream merge + Wesley's `dceca21ea`.
- ✅ #41 — Adopt supply-chain advisory checker for lazy installs (`hermes_cli/security_advisories.py` + `tools/lazy_deps.py` guard).
- ✅ #42 — Adopt tiered install fallback (Hermes #24515) — landed via upstream merge.
- ✅ #43 — Brand consistency pass (default + 4 neutral skins, CLI welcome banner, SOUL.md template).
- ✅ #44 — `SOUL.md` override docs page (`docs/tota-identity-customization.md`).
- ⏳ #45 — Native Windows beta integration test pass (40+ Windows fixes). Needs a Windows runner.
- ✅ #46 — `tota` / `tota-agent` / `tota-acp` `console_scripts` aliases added.

## Sprint 4 — Features, skills, nice-to-have

- ✅ #55 — Security trio (Hermes #23736, #26829, #26823) — landed by Wesley via `9f16d52e4`, `8204a329c`, `0f3f23c19`.
- ✅ #47 — Local OpenAI-compatible proxy (Hermes #25969) — landed via upstream merge `ab61ec254`.
- ✅ #48 — `/handoff` live session transfer (Hermes #23395) — landed via upstream merge `ab61ec254`.
- ✅ #49 — `/subgoal` user controls (Hermes #25449) — landed via upstream merge `ab61ec254`.
- ✅ #50 — LSP semantic diagnostics on every write (Hermes #24168, #25978) — landed via upstream merge `ab61ec254`.
- ✅ #51 — `vision_analyze` raw pixels to vision models (Hermes #22955) — landed via upstream merge `ab61ec254`.
- ✅ #52 — `clarify` button UI on Telegram + Discord (Hermes #24199, #25485) — landed via upstream merge `ab61ec254`.
- ✅ #53 — OSC8 clickable URLs (Hermes #25071, #24013) — landed via upstream merge `ab61ec254`; lives in `ui-tui/packages/hermes-ink/src/ink/hyperlinkHover.ts`.
- ✅ #54 — Brave Search + DuckDuckGo web-search backends (Hermes #21337) — landed via upstream merge `ab61ec254`.
- ✅ #56 — Pull 4 new optional skills — landed via upstream merge:
  - `optional-skills/blockchain/hyperliquid`
  - `optional-skills/finance/stocks` (yahoo-finance)
  - `optional-skills/software-development/rest-graphql-debug` (api-testing)
  - `optional-skills/devops/watchers`
- ✅ #57 — huggingface/skills trusted default tap (Hermes #26219) — landed via upstream merge; see `tools/skills_guard.py:39` and `tools/skills_hub.py:332`.

## Status legend

- ✅ — Closed (PR merged or doc shipped).
- ⏳ — Open; tractable but not yet started in this session.
- 🚦 — Gating priority for the sprint (must land before other sprint items).

## Process notes

- One PR per child issue wherever possible.
- Cherry-picks are scoped tight: identify the upstream commit, apply, resolve conflicts preferring Hermes Turbo's perf customizations + upstream's behavior, test.
- Sprints are sequential. Each sprint's DoD must hold before the next sprint starts.
- The `.tota/` repo directory is the source of truth for runtime defaults; `$TOTA_HOME` is the operator-mutable runtime home.
- The upstream Hermes v0.14.0 merge (commit `ab61ec254`, 2026-05-18) closed 13 cherry-pick issues at once. Remaining open issues are local-only work (`msgspec` migration, `run_agent.py`/`hermes_state.py` `orjson` migration, benchmark refresh, Native Windows beta).
