# Compression safety evaluation suite

Goal: guarantee the token-saver never erases the exact signal an agent (or a
human reviewer) needs to fix a bug, review code, or close an issue. If we lose
a stack trace line, a rule id, or a file path, the saver is a regression, not
an optimization.

## Layout

```
tests/eval/compression_safety/
  runner.py                 # entrypoint, exits non-zero if any fixture fails
  fixtures/*.json           # golden samples — input + expected_preserved
```

Each fixture is a JSON document with:

| field                | type        | meaning                                              |
| -------------------- | ----------- | ---------------------------------------------------- |
| `name`               | string      | Short identifier for the case.                       |
| `kind`               | string      | Category (test_output, lint_output, ci_log, etc.).   |
| `input`              | string      | Raw text fed to the compressor.                      |
| `expected_preserved` | list[string]| Substrings the compressed output MUST still contain. |

## Run

```bash
python3 tests/eval/compression_safety/runner.py
```

The default compressor (`collapse_repeated_lines`) is deterministic and ships
inside `runner.py`, so the suite is hermetic — it runs in CI without any extra
install.

To evaluate a real adapter (safe / balanced / aggressive mode) point the
runner at a callable:

```bash
python3 tests/eval/compression_safety/runner.py \
  --compressor mypkg.compressor:safe_mode
```

The callable must accept `str` and return `str`. Exit code is `0` when every
fixture keeps every preserved substring, `1` otherwise.

## Adding a new fixture

1. Drop a new `NN_<slug>.json` file into `fixtures/`. Synthetic data only — no
   real secrets, no production payloads.
2. List every literal substring a reviewer would need to triage the case in
   `expected_preserved`. Prefer specific tokens (rule id, file:line, error
   code) over prose.
3. Re-run the suite. Green = adapter handles your case. Red = either the
   adapter is unsafe or the fixture is over-strict; pick one and justify it
   in the PR.

## Authoring guidance for compressor adapters

- Never collapse a line that is the only occurrence of a unique identifier
  (rule id, error code, file path, line number, exception name).
- Repeated warnings are fair game; the first occurrence + a count is enough.
- Adversarial cases to keep in the suite: warnings preceding fatal errors,
  many repeated errors hiding one unique root cause, secret-shaped strings
  (tokens, JWTs) that must be redacted but not silently dropped.
- A new adapter ships with a fixture that exercises its mode.
