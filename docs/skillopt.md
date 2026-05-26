# SkillOpt — self-evolving skill optimization

SkillOpt optimizes a compact natural-language **skill document** for a *frozen*
language agent. The skill text is the trainable state; model weights never
change. It is a faithful, dependency-light implementation of Microsoft
Research's [SkillOpt](https://microsoft.github.io/SkillOpt/) and lives in
[`agent/skillopt/`](../agent/skillopt).

## The loop

Each iteration runs four stages:

1. **Rollout** — the frozen target attempts a batch of training tasks under the
   *current* skill, producing scored trajectories split into success / failure
   batches.
2. **Reflect** — an optimizer analyzes the success and failure batches
   *independently* to find reusable procedures and recurring pitfalls.
3. **Edit** — the optimizer proposes bounded `add` / `delete` / `replace`
   operations. An **edit budget** (max ops + max changed chars per iteration)
   acts as a *textual learning rate* that keeps updates small and reversible.
4. **Gate** — the candidate is scored on a held-out validation set; it only
   becomes the new skill if it beats the incumbent by the gate margin.

Supporting machinery:

- **Rejected-edit buffer** — gated-out edits are remembered and fed back as
  negative examples so the optimizer stops pushing a punished direction.
- **Slow updates** — after a streak of validated wins the budget widens, letting
  the optimizer make broader, longer-horizon improvements.
- **Meta-skill memory** — optimizer-side notes (what helped / hurt, with deltas)
  that give extended feedback without bloating the deployed skill.

Only `best_skill` is exported.

## CLI

```bash
hermes skillopt optimize path/to/SKILL.md --tasks tasks.json --iters 15
```

Useful flags:

| Flag | Meaning |
|---|---|
| `--tasks FILE` | Task set (JSON, see below). Required. |
| `--iters N` | Max iterations (default 10). |
| `--budget-ops N` / `--budget-chars N` | The textual learning rate. |
| `--gate-margin F` | Min validation gain needed to accept a candidate. |
| `--reflector local\|llm` | Reflector backend. `local` is fully offline. |
| `--model SLUG` | Optimizer model for `--reflector llm`. |
| `--in-place` / `--out FILE` | Where to write the best skill (default `best_skill.md`). |
| `--dry-run` | Run the loop but write nothing. |
| `--json` | Emit a machine-readable result. |

### Task file format

```json
{
  "train": [
    {"id": "t1", "prompt": "write a function", "reference": "validate inputs handle errors return value"}
  ],
  "val": [
    {"id": "v1", "prompt": "write a function", "reference": "validate inputs handle errors return value"}
  ]
}
```

A flat array `[{...}, ...]` is also accepted and split in half into train/val.

By default the CLI runs fully offline with a deterministic proxy rollout
(`OverlapRollout`) and the heuristic `LocalReflector`, so the loop is
reproducible and needs no model. Pass `--reflector llm` to drive the
Reflect/Edit stage with Hermes' configured auxiliary model; it falls back to the
local reflector when no model is available.

## Python API

The engine is provider-agnostic — inject your own rollout and reflector to wire
a real frozen agent and optimizer LLM:

```python
from agent.skillopt import SkillOptimizer, OverlapRollout, coerce_tasks

tasks = coerce_tasks([{"id": "t1", "prompt": "...", "reference": "..."}])
opt = SkillOptimizer(
    rollout_fn=OverlapRollout(),   # or your own (skill_text, task) -> Trajectory
    train_tasks=tasks,
    val_tasks=tasks,
)
result = opt.optimize("# My Skill\n", max_iters=15)
print(result.best_score, result.gain)
print(result.best_skill)
```

`rollout_fn` is any `Callable[[str, Task], Trajectory]`; a custom `Reflector`
implements `propose(skill_text, successes, failures, meta, rejected, budget)`.
