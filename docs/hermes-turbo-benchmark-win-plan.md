# Tota Agent Benchmark Win Plan

This note tracks the post-benchmark changes made to push Tota Agent toward
winning every practical row in the Hermes Original vs Tota Agent vs OpenClaw
comparison.

## Implemented

| Benchmark pressure | Change | Files |
| --- | --- | --- |
| JSON short payload gap vs V8 | Added `dumps_bytes()` / `_fast_dumps_bytes` so hot paths can avoid the `orjson.dumps(...).decode("utf-8")` round-trip when bytes are acceptable. | `agent/_fastjson.py` |
| Tool-call parse overhead | Changed the Rust parser to convert `serde_json::Value` directly into Python objects instead of serializing back to bytes and calling Python `json.loads`. | `rust_ext/src/lib.rs` |
| Token counting micro-benchmark | Added `estimate_tokens_many()` to batch many estimates through one Python-to-Rust boundary. | `agent/_hermes_fast.py`, `rust_ext/src/lib.rs` |
| Message budget hot path | Added `estimate_messages_tokens()` plus Rust bytes variants for whole-message token budgets. | `agent/_hermes_fast.py`, `rust_ext/src/lib.rs` |
| Async benchmark gap | Added centralized `uvloop` policy installation for CLI and gateway entrypoints when the `fast` extra is installed. | `agent/uvloop_utils.py`, `hermes_cli/main.py`, `gateway/run.py` |
| Disk footprint and supply-chain bounds | Kept performance dependencies in the optional `fast` extra and added upper bounds for `orjson`, `msgspec`, and `uvloop`. | `pyproject.toml`, `uv.lock` |
| Setup reliability | Updated Rust/setup scripts to prefer local `.venv`/`venv`, use `python -m pip`, and verify the extension with the repo root on `PYTHONPATH`. | `scripts/install-rust.sh`, `scripts/setup.sh` |

## Validation

Run the focused performance-contract tests:

```bash
venv/bin/python -m pytest -o addopts='' \
  tests/agent/test_fastjson.py \
  tests/agent/test_hermes_fast.py \
  tests/agent/test_uvloop_utils.py
```

Build and verify the native extension:

```bash
PATH="$HOME/.cargo/bin:$PATH" bash scripts/install-rust.sh
cd rust_ext
PYO3_PYTHON="$PWD/../.venv/bin/python" cargo check
```

Confirm the Rust path is active:

```bash
venv/bin/python -c "from agent._hermes_fast import HAVE_RUST; print(HAVE_RUST)"
```

## Benchmark Expectations

- `JSON dumps - short`: `dumps_bytes()` removes the mandatory decode cost for
  internal hot paths and should close the small short-payload gap against V8
  where callers can keep bytes.
- `Tool call parse`: direct Rust-to-Python conversion removes one full Python
  JSON parse from the Rust fast path.
- `Token estimate`: batch APIs reduce Python/Rust boundary overhead for many
  small strings and message lists.
- `Async 1,000 tasks`: `uvloop` is now installed as the default event-loop
  policy when available. This improves real Hermes async paths, but a synthetic
  1,000-task scheduler test can still favor native Node/libuv. Winning that row
  outright would require a larger Rust/Tokio gateway or sidecar architecture.
- `Integrations`: the benchmark PDF measured only WhatsApp and HTTP for Tota
  Agent, but the current checkout already contains gateway adapters for
  Telegram, Discord, Slack, Matrix, Signal, email, SMS, API server, and more.
  Future benchmark reports should score the current gateway surface rather than
  the narrower measured subset.

## Release Scope

Version bump: `0.13.1`.

This is a performance and packaging patch. It does not introduce mandatory
runtime dependencies into the base install.
