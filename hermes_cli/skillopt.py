"""``hermes skillopt`` — optimize a natural-language skill document.

Thin CLI wrapper around :mod:`agent.skillopt`. It loads a skill markdown file
and a task set, runs the SkillOpt loop (Rollout -> Reflect -> Edit -> Gate), and
writes the best validated skill back out.

Task file format (JSON)::

    {
      "train": [{"id": "t1", "prompt": "...", "reference": "..."}, ...],
      "val":   [{"id": "v1", "prompt": "...", "reference": "..."}, ...]
    }

A flat list ``[{...}, ...]`` is also accepted and split into train/val.

By default the loop runs fully offline with a deterministic proxy rollout and
the heuristic ``LocalReflector`` — reproducible and dependency-free. Pass
``--reflector llm`` (optionally ``--model``) to drive the Reflect/Edit stage
with Hermes' configured auxiliary model, falling back to the local reflector
when no model is available.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

from agent.skillopt import (
    EditBudget,
    LLMReflector,
    LocalReflector,
    OverlapRollout,
    Reflector,
    SkillOptimizer,
    Task,
    coerce_tasks,
    complete_via_auxiliary,
)


def _load_skill(path: Path) -> Tuple[str, Path]:
    """Return (skill_text, resolved_file). Accepts a file or a skill dir."""

    if path.is_dir():
        candidate = path / "SKILL.md"
        if not candidate.is_file():
            raise FileNotFoundError(f"no SKILL.md found in directory {path}")
        path = candidate
    if not path.is_file():
        raise FileNotFoundError(f"skill file not found: {path}")
    return path.read_text(encoding="utf-8"), path


def _load_tasks(path: Path) -> Tuple[List[Task], List[Task]]:
    """Load and split tasks into (train, val)."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        train = coerce_tasks(data.get("train", []) or [])
        val = coerce_tasks(data.get("val", []) or [])
        if not val:
            val = train
        if not train:
            train = val
        return train, val
    if isinstance(data, list):
        tasks = coerce_tasks(data)
        if len(tasks) < 2:
            return tasks, tasks
        split = max(1, len(tasks) // 2)
        return tasks[:split], tasks[split:]
    raise ValueError("tasks file must be a JSON object or array")


def _build_reflector(kind: str, model: Optional[str]) -> Reflector:
    if kind == "llm":
        complete = complete_via_auxiliary(model)
        if complete is not None:
            return LLMReflector(complete, fallback=LocalReflector())
        print(
            "skillopt: no auxiliary model available; using local reflector",
            file=sys.stderr,
        )
    return LocalReflector()


def _render_report(result, skill_path: Path, out_path: Path) -> str:
    lines = [
        "# SkillOpt report",
        "",
        f"- skill: `{skill_path}`",
        f"- initial score: {result.initial_score:.4f}",
        f"- best score: {result.best_score:.4f}",
        f"- gain: {result.gain:+.4f}",
        f"- iterations: {result.iterations} ({result.accepted_iterations} accepted)",
        f"- output: `{out_path}`",
        "",
        "| iter | rollout | succ | fail | proposed | applied | candidate | best | accepted |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|:--:|",
    ]
    for row in result.history:
        lines.append(
            f"| {row.iteration} | {row.rollout_score:.3f} | {row.n_success} | "
            f"{row.n_failure} | {row.proposed_edits} | {row.applied_edits} | "
            f"{row.candidate_score:.3f} | {row.best_score:.3f} | "
            f"{'yes' if row.accepted else 'no'} |"
        )
    return "\n".join(lines)


def cmd_optimize(args: argparse.Namespace) -> int:
    try:
        skill_text, skill_path = _load_skill(Path(args.skill))
        train, val = _load_tasks(Path(args.tasks))
    except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"skillopt: {exc}", file=sys.stderr)
        return 1

    if not val:
        print("skillopt: no validation tasks; cannot gate", file=sys.stderr)
        return 1

    reflector = _build_reflector(args.reflector, args.model)
    optimizer = SkillOptimizer(
        rollout_fn=OverlapRollout(success_threshold=args.threshold),
        train_tasks=train,
        val_tasks=val,
        reflector=reflector,
        budget=EditBudget(max_ops=args.budget_ops, max_chars=args.budget_chars),
        gate_margin=args.gate_margin,
        seed=args.seed,
    )
    result = optimizer.optimize(skill_text, max_iters=args.iters)

    # Resolve output target.
    if args.in_place:
        out_path = skill_path
    elif args.out:
        out_path = Path(args.out)
    else:
        out_path = skill_path.with_name("best_skill.md")

    if not args.dry_run:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result.best_skill, encoding="utf-8")
        except OSError as exc:
            print(f"skillopt: could not write {out_path}: {exc}", file=sys.stderr)
            return 1

    if args.json:
        payload: dict[str, Any] = result.to_dict()
        payload["output"] = str(out_path)
        payload["skill"] = str(skill_path)
        payload["dry_run"] = bool(args.dry_run)
        print(json.dumps(payload, indent=2))
    else:
        print(_render_report(result, skill_path, out_path))
        if args.dry_run:
            print("\n(dry run — no file written)")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes skillopt",
        description="Optimize a natural-language skill document for a frozen agent.",
    )
    sub = parser.add_subparsers(dest="skillopt_cmd")

    opt = sub.add_parser("optimize", help="Run the SkillOpt loop on a skill file")
    opt.add_argument("skill", help="Path to a SKILL.md (or a skill directory)")
    opt.add_argument("--tasks", required=True, help="Path to the tasks JSON file")
    opt.add_argument("--iters", type=int, default=10, help="Max iterations (default 10)")
    opt.add_argument("--budget-ops", type=int, default=3,
                     help="Max edits per iteration (textual learning rate)")
    opt.add_argument("--budget-chars", type=int, default=600,
                     help="Max changed characters per iteration")
    opt.add_argument("--gate-margin", type=float, default=0.0,
                     help="Min validation gain required to accept a candidate")
    opt.add_argument("--threshold", type=float, default=0.6,
                     help="Rollout success threshold (proxy rollout)")
    opt.add_argument("--reflector", choices=["local", "llm"], default="local",
                     help="Reflector backend (default local)")
    opt.add_argument("--model", default=None,
                     help="Optimizer model slug for --reflector llm")
    opt.add_argument("--out", default=None, help="Write best skill here")
    opt.add_argument("--in-place", action="store_true",
                     help="Overwrite the input skill file with the best skill")
    opt.add_argument("--dry-run", action="store_true",
                     help="Run the loop but do not write any file")
    opt.add_argument("--json", action="store_true", help="Emit JSON result")
    opt.add_argument("--seed", type=int, default=0, help="RNG seed for rollout sampling")
    opt.set_defaults(func=cmd_optimize)
    return parser


def skillopt_command(args: argparse.Namespace) -> int:
    """Dispatch entry point used by the main Hermes CLI."""

    func = getattr(args, "func", None)
    if func is None or getattr(args, "skillopt_cmd", None) is None:
        print("Usage: hermes skillopt optimize <skill> --tasks <tasks.json> [options]")
        print()
        print("Run `hermes skillopt optimize --help` for all options.")
        return 0
    return func(args)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return skillopt_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
