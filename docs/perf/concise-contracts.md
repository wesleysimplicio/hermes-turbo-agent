# Concise Response Contracts

Ref: issue #101. Goal: cut output-token spend by forcing the agent into
narrow, budget-capped reply shapes.

## Contracts

Defined in `agent/contracts/concise_response.py`:

| Contract     | Purpose                         | Budget                                                |
|--------------|---------------------------------|-------------------------------------------------------|
| TerseAnswer  | Default chat reply              | text<=600; <=4 citations of 120 chars                 |
| ToolCall     | Structured tool invocation      | name<=64; <=8 args (key<=32, value<=240)              |
| Diagnostic   | Info / warning / error signal   | code<=48; message<=280; level in {info,warning,error} |

All over-budget strings are truncated with a trailing `...` ellipsis by
`enforce_budget`. The validator runs at construction time, so an
instance is guaranteed within budget once it exists.

## How the model is told

`prompts/contracts/concise.md` is injected into the system prompt of
agent loops that should emit machine-parseable output. It describes
each JSON shape, the budgets, and five rules (no extra fields, no code
fences, rewrite-don't-rely-on-truncate, prefer `Diagnostic` over a
chatty refusal, one contract per turn).

## Wiring

The contracts and prompt fragment ship together. Loader/parser work
(injecting the fragment and decoding model output into the dataclasses)
lands in a separate follow-up PR to keep this change reviewable.

## Tests

`tests/contracts/test_concise_response.py` asserts truncation at each
budget boundary, ellipsis suffix, rejection of bad input, and stable
`to_dict()` shapes. Run: `python -m unittest tests.contracts.test_concise_response`.
