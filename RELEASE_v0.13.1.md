# Hermes Agent v0.13.1 (v2026.5.17)

**Release Date:** May 17, 2026

> Tota Agent benchmark follow-up: bytes-native JSON, stronger Rust hot paths,
> batched token estimation, automatic uvloop policy setup, and documented
> benchmark remediation.

## Highlights

- Added `agent._fastjson.dumps_bytes()` and `_fast_dumps_bytes` for hot paths
  that can keep UTF-8 JSON bytes and skip a Python string decode.
- Added batched token estimation through `estimate_tokens_many()` and
  whole-message budget estimation through `estimate_messages_tokens()`.
- Added Rust bytes variants for message-token estimation and truncation.
- Optimized Rust tool-call parsing by converting `serde_json::Value` directly
  into Python objects instead of round-tripping through Python `json.loads`.
- Added centralized optional `uvloop` policy installation for CLI and gateway
  entrypoints.
- Tightened `fast` extra dependency bounds and refreshed `uv.lock`.
- Hardened setup scripts for moved worktrees by preferring local virtualenvs
  and using `python -m pip`.
- Added focused tests for bytes JSON, Rust-backed token helpers, parser
  payloads, uvloop policy installation, and version/ACP manifest alignment.

## Validation

- `venv/bin/python -m pytest -o addopts='' tests/agent/test_fastjson.py tests/agent/test_hermes_fast.py tests/agent/test_uvloop_utils.py tests/acp/test_registry_manifest.py tests/hermes_cli/test_update_check.py`
- `PATH="$HOME/.cargo/bin:$PATH" bash scripts/install-rust.sh`
- `cd rust_ext && PYO3_PYTHON="$PWD/../.venv/bin/python" cargo check`
