# Tota Agent v0.14.0 — Hermes 0.14.0 sync + `llm-project-mapper` core

**Release type:** Tota fork sync.
**Upstream baseline:** Hermes Agent `0.14.0` (NousResearch/hermes-agent,
calendar tag `v2026.5.16`).
**Previous Tota version:** `0.13.2` (synced against Hermes `0.13.0` /
`v2026.5.7`).

This release brings the Tota Agent fork in line with Hermes Agent 0.14.0
while preserving every Tota-specific customization, and promotes
[`@wesleysimplicio/llm-project-mapper`](https://github.com/wesleysimplicio/llm-project-mapper)
to a **core onboarding step** for all code projects.

---

## ✨ Highlights

- **Version pin → 0.14.0.** `pyproject.toml` and `hermes_cli/__init__.py`
  now report `0.14.0`. Dependencies in our `pyproject.toml` were already
  identical to upstream 0.14.0 (additive customizations only —
  `fast`/`perf` extras, Rust `maturin` dev pin, `tui_dist` package data,
  `acp_adapter/bootstrap` package data).
- **`TOTA_HOME` is first-class.** The fork already honored `TOTA_HOME`
  ahead of legacy `HERMES_HOME` in `hermes_constants.py`. This release
  documents that contract and ships project-local defaults under `.tota/`.
- **`llm-project-mapper` is Tota core.** New skill at
  `skills/software-development/llm-project-mapper/` with an idempotent
  `map_project.py` script. The default agent identity now instructs Tota
  to run the mapper before touching any code project. State persists in
  `$TOTA_HOME/mapped_projects.json` across sessions and profiles.
- **Identity refresh.** `DEFAULT_AGENT_IDENTITY` introduces Tota as a
  modified, faster Hermes — same surface, lower latency, tighter project
  on-ramps.

## What's preserved from prior Tota releases

All Tota-specific customizations from `0.13.0 → 0.13.2` are intact:

- Tota home (`TOTA_HOME`) with legacy `HERMES_HOME` fallback —
  `hermes_constants.py`.
- Rust `hermes_fast` PyO3 extension (Phase 3 perf) —
  `rust_ext/`, `pyproject.toml` dev extra `maturin>=1.0,<2.0`.
- `fast` / `perf` extras (`orjson`, `msgspec`, `uvloop`) —
  `pyproject.toml`.
- Hierarchical cache + metrics — see prior PR #17 / #18.
- Streaming-on-by-default + `parallel_tool_calls` — PR #11.
- Context retention + tota benchmark surfaces (`tota-agent.html`,
  `tota_agent_benchmark_report.pdf`).
- Tota launch battlecards and brand site (`website/`).
- Fork-specific gateway service names — `hermes_cli/gateway.py`.

## Upstream changes covered by this sync

The version bump captures Hermes' 1,053 upstream commits between
`v2026.5.7` and `v2026.5.16` at the *manifest* level. Because Tota's
dependency pins were already congruent with upstream, no transitive
upgrades are required for this sync to succeed.

For feature-level integration (e.g. Hermes' kanban hardening, `/goal`
Ralph loop polish, Google Chat platform, providers-as-plugins, MCP SSE),
future PRs may cherry-pick targeted commits. This release intentionally
keeps the surface narrow:

1. Manifest sync to `0.14.0`.
2. `llm-project-mapper` core integration.
3. Identity update.

## llm-project-mapper integration

### Why core, not optional

Tota's speed claim depends on never paying the onboarding tax twice.
`llm-project-mapper` canonicalizes any code repository into an
`AGENTS.md` + `INIT.md` + `.specs/` + `.skills/` scaffold the agent can
read in O(1) on every subsequent visit. The memory file in
`$TOTA_HOME/mapped_projects.json` remembers which projects have been
mapped — runs after the first are no-ops unless the mapping is older
than 30 days or `--force` is passed.

### How to invoke

```bash
python skills/software-development/llm-project-mapper/scripts/map_project.py \
    --project-root "$PWD"
```

The script:

1. Resolves `TOTA_HOME` → `HERMES_HOME` → `~/.tota`.
2. Checks `mapped_projects.json` for a fresh fingerprint.
3. Spawns `npx --yes @wesleysimplicio/llm-project-mapper` inside the
   project root when needed.
4. Records the new fingerprint with timestamp, git remote, mapper
   version (parsed from the mapper's own banner — no second `npx`
   invocation), and `ralph_ready` (true when `AGENTS.md`, `INIT.md`,
   and `_BOOTSTRAP.md` all exist).

### Default agent directive

`agent/prompt_builder.DEFAULT_AGENT_IDENTITY` now includes a Tota-core
directive: "for any code project you touch, run the
`llm-project-mapper` skill first". Operators who want to disable this
behaviour can override the identity via `SOUL.md` in their
`$TOTA_HOME`.

## Local `.tota/` defaults

New repo-local directory `.tota/` ships the canonical Tota defaults:

| Path | Contents |
| --- | --- |
| `.tota/version` | `0.14.0` |
| `.tota/HERMES_BASE` | Upstream Hermes baseline + tagline |
| `.tota/memories/MEMORY.md` | Seed memory (identity, mapping directive) |
| `.tota/mapped_projects.json` | Empty registry, copied into `$TOTA_HOME` on first run |
| `.tota/README.md` | How resolution and seeding work |

Setup scripts can copy these into the operator's `$TOTA_HOME` to keep
defaults in sync with the fork.

## Tests + breakage risk

This release does not touch agent runtime code paths beyond:

- `pyproject.toml` version string
- `hermes_cli/__init__.py` version string
- `agent/prompt_builder.DEFAULT_AGENT_IDENTITY` content

The identity update is a text change; downstream consumers that snapshot
the system prompt will see the new string but no shape change.

No `requirements*.txt`, `uv.lock`, or import-graph changes are part of
this release.
