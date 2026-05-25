# Customizing the Hermes Turbo Agent Identity

Hermes Turbo Agent's `DEFAULT_AGENT_IDENTITY` (in `agent/prompt_builder.py`) ships
with two messages baked into every session:

1. **Branding:** *"You are Hermes Turbo Agent, a modified and faster Hermes... built
   on top of Nous Research's Hermes Agent (currently synced with v0.14.0)..."*
2. **Hermes Turbo-core directive:** *"...for any code project you touch, run the
   `llm-project-mapper` skill first..."*

Both messages serve Hermes Turbo's public position as a faster Hermes fork with an
opinionated project-onboarding stance. **Operators who deploy Hermes Turbo under
their own brand**, or who want to neutralize either message, can do so
without forking the codebase.

## How identity resolution works

At session start, `agent.prompt_builder._build_system_prompt_parts` calls
`load_soul_md()`. If a `SOUL.md` file exists in the runtime home
(`$TOTA_HOME/SOUL.md`, default `~/.hermes_turbo/SOUL.md`), its contents become the
agent's identity message and the hardcoded `DEFAULT_AGENT_IDENTITY` is
**skipped entirely**. No merging — `SOUL.md` is a full override.

The resolution order is:

1. `$HERMES_TURBO_HOME/SOUL.md` if present.
2. `$HERMES_TURBO_HOME/profiles/<active>/SOUL.md` when profile mode is on.
3. Fallback to the hardcoded `DEFAULT_AGENT_IDENTITY`.

## Common customizations

### 1. White-label deployment — drop the Hermes Turbo / Hermes brand

```markdown
# $HERMES_TURBO_HOME/SOUL.md
You are Aria, the in-house AI engineer for Acme Corp. You assist Acme
engineers with code, infrastructure, and ops tasks. Be direct, accurate,
and admit uncertainty when relevant.

For any code project you touch, run the project-mapping skill before
making changes so the project onboarding context is fresh.
```

The mapping directive is still here — operators usually want the mapper
behavior regardless of brand — but the Hermes Turbo/Hermes naming is gone.

### 2. Keep Hermes Turbo branding, drop the mapping directive

```markdown
# $TOTA_HOME/SOUL.md
You are Hermes Turbo Agent, a modified and faster Hermes built on Nous Research's
Hermes Agent. You are helpful, knowledgeable, and direct. You assist
users with answering questions, writing and editing code, analysis,
creative work, and executing actions via your tools.
```

This keeps the brand but omits the auto-mapping language. The
`agent.auto_mapper` runtime hook still runs by default — to also disable
that, set `HERMES_TURBO_AUTO_MAP=0` or touch `$HERMES_TURBO_HOME/.disable_auto_mapper`.

### 3. Persona-specific (cron, gateway, ACP)

`SOUL.md` is profile-scoped. Run multiple personas side-by-side via the
profiles system:

```bash
hermes-turbo profile create coder
hermes-turbo profile create reviewer
hermes-turbo profile use coder
# Edit $TOTA_HOME/profiles/coder/SOUL.md → coder persona
# Edit $TOTA_HOME/profiles/reviewer/SOUL.md → reviewer persona
```

## What you cannot override via SOUL.md

The following stay hardcoded — overriding them requires a code change:

- Tool-aware guidance blocks (`MEMORY_GUIDANCE`, `SESSION_SEARCH_GUIDANCE`,
  `SKILLS_GUIDANCE`, etc.) — these only inject when the corresponding tools
  are loaded.
- Model-family operational guidance (Google, OpenAI, Codex variants).
- Platform hints (Telegram, Discord, etc.) when the gateway is running.

These are appended **after** the identity message, so they coexist with
your `SOUL.md` content. To disable individual guidance blocks, drop the
corresponding tool from the toolset.

## How to verify your override is active

```bash
HERMES_TURBO_DEBUG_DUMP_SYSTEM_PROMPT=1 hermes-turbo --help
# The dumped prompt prints to stderr; grep for your SOUL.md content.
```

Or check the active profile's `_cached_system_prompt` via the dump tool:

```bash
hermes-turbo dump --component=system_prompt
```

## Operator best practices

- **Keep `SOUL.md` short.** It runs first in the prompt and counts against
  every turn's input tokens. 100–300 words is plenty.
- **Include the mapping directive** unless you have a reason to drop it.
  The auto-mapper depends on the model knowing it should consult the
  mapping output.
- **Re-test after upgrades.** A Hermes Turbo minor version bump can change the
  surrounding guidance blocks. Re-run your golden-path prompts after
  every `hermes-turbo update`.
- **Version-control your `SOUL.md`** in your operator's config repo so the
  override is reviewable and recoverable.

## Reference

| File | Purpose |
| --- | --- |
| `agent/prompt_builder.py` (`DEFAULT_AGENT_IDENTITY`) | Hardcoded identity when no SOUL.md is present. |
| `agent/prompt_builder.py` (`load_soul_md`) | Resolves the SOUL.md path and reads contents. |
| `agent/auto_mapper.py` | Runtime hook that invokes `llm-project-mapper`. |
| `hermes_constants.py` (`get_hermes_home`) | Defines `$HERMES_TURBO_HOME` resolution order. |

For the upstream Hermes equivalent see
`NousResearch/hermes-agent`'s `SOUL.md` docs — Hermes Turbo's mechanism is
identical, only the brand and core directive differ.
