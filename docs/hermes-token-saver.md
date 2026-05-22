# Hermes Token Saver

Hermes Token Saver is the first native token-economy plugin for Hermes Turbo
Agent. It reduces noisy command and tool output before it reaches the next LLM
turn, while preserving a redacted raw evidence file that can be reopened when
exact logs are needed.

## Goals

- Keep autonomous `/goal` and Ralph-style loops cheaper without hiding failures.
- Preserve exact source reads, because code review and implementation depend on
  source fidelity.
- Save raw logs as evidence handles instead of dropping information.
- Stay compatible with external RTK command rewriting while keeping a native,
  testable Hermes implementation in the repo.

## Runtime Controls

```bash
export HERMES_TOKEN_SAVER_MODE=safe
export HERMES_TOKEN_SAVER_MIN_CHARS=1200
```

Supported modes:

- `off` returns output unchanged.
- `safe` compresses long command output but keeps exact read commands raw.
- `balanced` preserves important error lines plus head and tail context.
- `aggressive` keeps the smallest useful summary while still saving raw evidence.

## Evidence Model

Compressed output is returned as a `<token-saver-output>` envelope with:

- the command or tool name;
- exit code for terminal commands;
- raw and compressed character counts;
- estimated raw, compressed, and saved tokens;
- path to the redacted raw evidence file;
- a concise summary and selected important lines.

Raw evidence is written under the Hermes home directory:

```text
<HERMES_HOME>/token-saver/raw/*.log
```

The saved file is redacted through the existing Hermes sensitive-text redactor
before it is persisted.

## GitHub Issues

This slice implements the first deliverable for:

- [#88](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/88)
- [#89](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/89)
- [#94](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/94)

It also feeds the sync and validation work tracked in:

- [#85](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/85)
- [#86](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/86)
- [#95](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/95)
