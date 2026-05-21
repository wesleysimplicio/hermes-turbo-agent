# ClawBench Eval Harness

ClawBench-style evaluation for Hermes Turbo. Measures agent performance on
full-agent tasks (file edit, web fetch, multi-step plan, tool use, conditional
logic) instead of microbenchmarks alone.

Refs: issue #100.

## Layout

```
eval/clawbench/
  runner.py     # loads tasks, runs agent, prints/JSON report
  scorer.py     # exact_match | soft_match | llm_judge_stub
  tasks/        # 5 sample task JSONs (extend freely)
docs/eval/
  clawbench.md  # this file
```

## Task JSON schema

```json
{
  "id": "unique-task-id",
  "kind": "file_edit | web_fetch | multi_step_plan | tool_use | conditional_logic",
  "description": "one-line summary",
  "prompt": "instructions handed to the agent",
  "scorer": "exact | soft | judge",
  "expected": "ground-truth string the scorer compares against"
}
```

Drop a new JSON file into `eval/clawbench/tasks/` and the runner picks it up
automatically (alphabetical order).

## Running

Dry run (no external calls -- uses the stub `echo_agent`, every task passes):

```bash
python3 eval/clawbench/runner.py --dry-run
```

JSON report for CI:

```bash
python3 eval/clawbench/runner.py --json
```

Exit code `0` when every task scores `>= 1.0`, otherwise `1`.

## Wiring a real agent

Replace `echo_agent` in `runner.py` with a callable that takes a task dict and
returns the agent's final observable output as a string.

- Hermes Turbo: call the runtime API, await final message, return its text.
- OpenClaw: run the binary against the prompt, capture stdout, return it.

## Scorers

| Scorer  | Behavior                                                  |
|---------|-----------------------------------------------------------|
| `exact` | Normalized (lowercase, punctuation-stripped) equality.    |
| `soft`  | Jaccard token overlap, returns a value in `[0.0, 1.0]`.   |
| `judge` | Stub returning the soft-match score. Swap for a real LLM. |

The `judge` stub is intentionally deterministic so CI is reproducible. Replace
it with a real LLM-as-judge call when integrating WildClawBench-style
open-ended grading.

## Roadmap (issue #100)

- [x] Local harness for long-horizon agent tasks with tool calls.
- [ ] Track wall-clock, tokens, cost, success rate, retries, safety incidents.
- [ ] Publish benchmark report separating micro / runtime / full-agent results.
- [ ] Update README scoreboard from harness output.
