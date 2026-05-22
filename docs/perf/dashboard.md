# Runtime Performance Dashboard

The telemetry module (`agent/telemetry/`) records per-stage durations from real
Hermes Turbo Agent runs and renders a local ASCII dashboard for diagnosing
slow runs. Closes issue #82.

## What gets logged

Every `StageTimer` block appends one JSON line to a JSONL log with the shape:

```json
{"ts":"2026-05-21T12:34:56.789012Z","stage":"context_build","duration_ms":42.501,"provider":"deepseek","model":"deepseek-chat","tool":null,"ok":true,"meta":{}}
```

Fields: `ts` (UTC ISO 8601), `stage`, `duration_ms`, optional `provider` /
`model` / `tool` labels, `ok` (false when the block raised), and free-form
`meta`.

**Privacy guarantee**: no prompt content, secret, or arbitrary user data is
written by the timer itself. Callers must keep `meta` redacted.

Default path: `~/.hermes/telemetry.jsonl`. Override with `HERMES_TELEMETRY_LOG`.

## Instrumenting a stage

```python
from agent.telemetry import StageTimer

with StageTimer("context_build"):
    build_context(...)

with StageTimer("model_call", provider="deepseek", model="deepseek-chat"):
    response = call_model(...)

with StageTimer("tool_dispatch", tool="ripgrep"):
    run_tool(...)
```

Recommended stage names (extend as needed):

- `context_build` - assembling prompt context
- `prompt_build` - final prompt rendering
- `model_call` - LLM HTTP roundtrip
- `tool_dispatch` - single tool execution
- `db_write` - persistence
- `mcp_reload` - MCP server reload
- `delegation` - sub-agent handoff
- `retry` - automatic retry attempt
- `ui_event_burst` - UI event flush

## Reading the dashboard

```bash
python -m agent.telemetry.dashboard
python -m agent.telemetry.dashboard --group-by provider
python -m agent.telemetry.dashboard --group-by model --json
python -m agent.telemetry.dashboard --log /path/to/telemetry.jsonl
```

Sample output:

```
telemetry: /home/wesley/.hermes/telemetry.jsonl  (1284 events)
+----------------+--------+--------+--------+--------+--------+---------+
| stage          | count  | errors | p50_ms | p95_ms | p99_ms | mean_ms |
+----------------+--------+--------+--------+--------+--------+---------+
| model_call     | 612    | 4      | 812.50 | 2480.10| 3104.77| 968.42  |
| context_build  | 612    | 0      | 41.20  | 88.30  | 134.50 | 49.81   |
| tool_dispatch  | 60     | 1      | 22.10  | 71.40  | 96.20  | 31.05   |
+----------------+--------+--------+--------+--------+--------+---------+
```

Rows are sorted by p95 descending so the worst tail latency surfaces first.

## Diagnosing a slow run

1. Reproduce the slow run with telemetry enabled (default on).
2. Run `python -m agent.telemetry.dashboard` to find the dominant stage by p95.
3. Drill in with `--group-by provider` or `--group-by model` to isolate which
   backend is the bottleneck.
4. Use `--group-by tool` to spot a single tool dispatch that dominates.
5. Compare counts and `errors` columns to detect retry storms.

## Resetting the log

```bash
rm ~/.hermes/telemetry.jsonl
# or rotate
mv ~/.hermes/telemetry.jsonl ~/.hermes/telemetry-$(date +%F).jsonl
```

No daemon, no shipping to remote - local-only by design.
