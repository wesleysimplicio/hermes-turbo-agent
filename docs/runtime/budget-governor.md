# Budget Governor

> Stdlib-only token / cost / iteration budgets for autonomous loops
> (`/goal`, Ralph). Refs: [issue #93](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/93).

## Why

Autonomous loops accumulate shell output, summaries, test logs, and planning
text on every turn. Without a budget the loop silently burns context and
dollars until something explodes. The governor turns that into an explicit,
inspectable contract:

- record spend on each step,
- escalate to compressed mode at 70%,
- hard stop at 100%.

## API

```python
from agent.governor import (
    BudgetConfig,
    BudgetGovernor,
    BudgetExceeded,
    WarnAt70HardStopAt100,
    EscalationLevel,
)

cfg = BudgetConfig(
    max_tokens_per_loop=100_000,  # None = disabled
    max_cost_usd=2.0,
    max_iterations=50,
)

def on_warn(axis, snap):
    # flip to focused/compressed mode here
    print(f"warn on {axis}: {snap}")

gov = BudgetGovernor(cfg, warn_ratio=0.70, on_warn=on_warn)
policy = WarnAt70HardStopAt100()

while True:
    step = run_one_turn()
    try:
        gov.record_step(tokens=step.tokens, cost_usd=step.cost)
    except BudgetExceeded as e:
        # graceful shutdown: persist progress, emit summary
        break

    level = policy.evaluate(gov.snapshot(), cfg)
    if level == EscalationLevel.WARN:
        switch_to_focused_logs()
```

## Axes

| Axis              | Config field           | Default |
|-------------------|------------------------|---------|
| Token spend       | `max_tokens_per_loop`  | `None`  |
| USD cost          | `max_cost_usd`         | `None`  |
| Iteration count   | `max_iterations`       | `None`  |

`None` means "do not enforce this axis". `BudgetExceeded` carries
`axis`, `used`, `limit` for surgical error handling.

## Escalation

`WarnAt70HardStopAt100` returns one of three `EscalationLevel` values
based on the highest used/limit ratio across all configured axes:

- `OK` (< 70%) -- business as usual.
- `WARN` (70-99%) -- switch to compressed/focused output, drop verbose
  logs, prefer summaries over full tool results.
- `STOP` (>= 100%) -- `BudgetGovernor.record_step` already raised
  `BudgetExceeded`; the loop must wind down.

## Tests

`tests/agent/test_governor.py` covers: under-limit recording, raise on
each axis, negative-input rejection, single-fire warn callback,
no-limit pass-through, full OK -> WARN -> STOP transition, and the
multi-axis "highest ratio wins" rule.

Run:

```bash
pytest tests/agent/test_governor.py -q
```
