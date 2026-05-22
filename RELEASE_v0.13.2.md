# Hermes Agent v0.13.2 (v2026.5.17)

**Release Date:** May 17, 2026

> Tota Agent home-directory alignment plus runtime hardening for corrupted
> tool-call argument recovery.

## Highlights

- Added `TOTA_HOME` as the fork-native home-directory override.
- Changed the unset-env default from `~/.hermes` to `~/.tota` for new Tota
  installs, profile roots, setup scripts, and bundled Node bootstrap.
- Kept `HERMES_HOME` as a backward-compatible override so existing
  `~/.hermes2` runtimes continue to work without data migration.
- Updated focused home-directory tests and installer/help text.

## Fixes

- Moved the corrupted tool-call-argument marker to module scope while keeping
  the `AIAgent` class attribute as a compatibility alias.
- Hardened `_sanitize_tool_call_arguments()` so it no longer crashes if the
  module-level `AIAgent` binding is replaced by a wrapper, stale class, or test
  double that does not carry the marker attribute.
- Added `separators=` compatibility to `agent._fastjson.dumps()` and
  `dumps_bytes()` so guardrail canonicalization can use compact sorted JSON.
- Replaced a stale downloaded `404: Not Found` load-test file with a valid
  skipped placeholder so repository-wide lint and test collection can run.

## Validation

- `python -m pytest tests/test_hermes_constants.py tests/test_hermes_home_profile_warning.py tests/hermes_cli/test_config.py -q`
- `python -m ruff check hermes_constants.py hermes_cli/main.py hermes_cli/__init__.py tests/test_hermes_constants.py tests/test_hermes_home_profile_warning.py tests/hermes_cli/test_config.py scripts/build_model_catalog.py scripts/build_skills_index.py`
- `HERMES_TEST_WORKERS=1 scripts/run_tests.sh tests/run_agent/test_tool_call_args_sanitizer.py -q`
- `HERMES_TEST_WORKERS=1 scripts/run_tests.sh tests/run_agent/test_repair_tool_call_arguments.py tests/run_agent/test_tool_call_args_sanitizer.py -q`
- `.venv/bin/python -m ruff check run_agent.py tests/run_agent/test_tool_call_args_sanitizer.py`
- `.venv/bin/python -m ruff check .`
- `HERMES_TEST_WORKERS=4 scripts/run_tests.sh tests/agent/test_fastjson.py tests/agent/test_tool_guardrails.py tests/run_agent/test_dict_tool_call_args.py tests/run_agent/test_tool_call_args_sanitizer.py tests/run_agent/test_repair_tool_call_arguments.py tests/run_agent/test_streaming_tool_call_repair.py tests/run_agent/test_message_sequence_repair.py tests/run_agent/test_jsondecodeerror_retryable.py -q`
- `HERMES_TEST_WORKERS=4 scripts/run_tests.sh tests/run_agent -q`
