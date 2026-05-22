# Token-saver proxy (native)

Native Hermes Turbo layer that compresses shell and tool output before it is
appended to model context. Lives in `agent/token_saver/`.

## What it does

- Counts lines in the captured output.
- Below `max_lines`: returns the text untouched.
- Above `max_lines`: keeps the first `head` lines, drops the middle, keeps the
  last `tail` lines, and inserts a single truncation marker in between.
- Writes the full payload to a file under the configured `storage_dir` and
  exposes it as `<handle:/abs/path/to/output-<ts>-<sha>.txt>` so callers can
  pull the complete log when they actually need it.

## Why head/tail

Shell tools (`pytest`, `git diff`, `npm test`, long `rg`) follow a recurring
pattern: the interesting signal sits at the top (banner / summary / first
failure) and the bottom (final assertion, exit code, totals). The noisy middle
is what blows the context budget. Head/tail is the smallest strategy that
preserves both ends without inventing parser-specific rules per command --
those land as adapters on top of this proxy in follow-up commits.

## Usage

```python
from agent.token_saver import TokenSaverProxy

proxy = TokenSaverProxy(max_lines=200, head=80, tail=80)
result = proxy.wrap(captured_stdout)

# Feed the compact view back to the model:
context_chunk = result.text

# Later, when the model asks for the full log:
if result.handle:
    full = proxy.resolve(result.handle)
```

`TruncationResult` carries the visible `text`, the `handle` (or `None`), the
`full_path` on disk, original/kept line counts, and a `meta` dict with the
head/tail/elided split.

## Defaults

| Field         | Value                                              |
| ------------- | -------------------------------------------------- |
| `max_lines`   | 200                                                |
| `head`        | 80                                                 |
| `tail`        | 80                                                 |
| `storage_dir` | `${TMPDIR}/hermes-token-saver`                     |
| Handle form   | `<handle:/abs/path/output-<ts>-<sha1[:12]>.txt>`   |

Invariants enforced at call time: `max_lines > 0`, `head >= 0`, `tail >= 0`,
`head + tail <= max_lines`.

## Out of scope (tracked separately)

- Command-aware adapters for `git status`, `git diff`, `git log`, `rg`,
  `pytest`, `ruff`, `npm test` -- they build on top of `TokenSaverProxy` and
  ship as follow-ups under issue #88.
- `off / safe / balanced / aggressive` profile presets -- next iteration.
- TTL / garbage collection on `storage_dir` -- intentionally manual for now.

## Tests

`tests/token_saver/test_proxy.py` covers head/tail boundary conditions, handle
creation and resolution, invalid argument handling, and the round-trip from
`wrap()` to `resolve()`.
