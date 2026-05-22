# Token Savings Telemetry & Gain Analytics

Hermes Turbo records how many tokens the compression pipeline saves per tool
result and aggregates them through a small CLI.

## Storage

Default path `~/.hermes/telemetry/token_savings.jsonl`, override via
`HERMES_TOKEN_SAVINGS_LOG`. Append-only JSONL; the recorder swallows OS
errors so telemetry never breaks the agent loop.

## Schema (one object per line)

`ts` (ISO-8601 UTC, e.g. `2026-05-21T12:34:56Z`), `tool`, `command`,
`adapter`, `session`, `repo`, `raw_tokens`, `compressed_tokens`,
`saved_tokens` (`max(0, raw - compressed)`), `savings_pct`
(`100 * saved / raw`, 2 decimals). No prompt content, no secrets.

## Recording

```python
from agent.telemetry import record_token_saving

record_token_saving(
    raw_tokens=1200, compressed_tokens=380,
    tool="read_file", adapter="anthropic",
    session="sess-syn-001", repo="hermes-turbo-agent",
)
```

## Reporting

```bash
python -m agent.telemetry.gain_analytics --top 10
python -m agent.telemetry.gain_analytics --log /tmp/savings.jsonl --json
```

Text mode shows totals, top tools by raw tokens spent, and a per-day trend.
`--json` emits the same aggregation as one JSON document.

## Reading the numbers

- Overall savings under ~50% usually means many tool outputs are opaque
  (binary blobs) and the compressor can't inspect them.
- A tool dominating raw tokens is a candidate for tighter prompts.
- A drop in the daily trend often signals a compression regression - bisect.

Telemetry is local-only; delete the file or point the env var at `/dev/null`
to disable.
