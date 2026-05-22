# Hermes Turbo Agent v0.14.7 - token saver and upstream sync policy

**Release type:** token economy, update automation, and regression coverage.

**Previous version:** `0.14.6`.

This release starts the OpenClaw-beating token-economy track with a native
Hermes Turbo plugin and a policy-driven upstream sync engine. It keeps external
RTK support available, but moves the core savings behavior into this repo so it
can be tested, reviewed, and reapplied after upstream Hermes updates.

## Highlights

- **Native token saver plugin:** `plugins/token_saver/` compacts noisy terminal
  and tool output while saving redacted raw evidence handles.
- **Safe source fidelity:** exact file-read commands and exact read tools remain
  raw so coding agents do not lose line-level context.
- **Token gain telemetry:** compressed envelopes include raw/compressed sizes and
  estimated saved tokens.
- **Upstream sync policy:** `docs/hermes-upstream-sync-policy.yaml` declares how
  Hermes Turbo customizations should be kept, merged, regenerated, or manually
  reviewed during upstream Hermes updates.
- **Sync report engine:** `scripts/sync_hermes_upstream.py` fetches upstream,
  classifies changed paths against the policy, and writes an auditable report.
- **Global RTK compatibility:** RTK can remain installed as a global command
  bridge while this plugin provides the repo-native implementation.
- **CI stabilization:** refreshed Hermes Turbo branding expectations, gateway
  service isolation, runtime stream recovery, approval fallback compatibility,
  Kanban diagnostic filtering, and process/stdin helpers so the GitHub test job
  tracks the forked behavior instead of stale upstream assumptions.

## GitHub Tracking

- `#85` robust upstream Hermes update capture and reapply system.
- `#86` upstream sync policy file for Hermes Turbo customizations.
- `#88` native token-saver proxy for shell and tool output.
- `#89` raw command output as expandable evidence handles.
- `#94` RTK compatibility and external token-saver bridge.
- `#95` compression safety evaluation suite for token saver outputs.

## Validation

- `python -m pytest tests/plugins/test_token_saver_plugin.py tests/hermes_cli/test_upstream_sync_policy.py tests/hermes_cli/test_hermes_upstream_sync.py -q`
- `python scripts/validate_hermes_sync_policy.py docs/hermes-upstream-sync-policy.yaml`
- `python -m ruff check plugins/token_saver scripts/validate_hermes_sync_policy.py scripts/sync_hermes_upstream.py tests/plugins/test_token_saver_plugin.py tests/hermes_cli/test_upstream_sync_policy.py tests/hermes_cli/test_hermes_upstream_sync.py hermes_cli/__init__.py`
- `python -m pytest <41 focused CI-regression tests> -q`
- `python -m ruff check agent/anthropic_adapter.py agent/conversation_loop.py cli.py hermes_cli/gateway.py hermes_state.py plugins/kanban/dashboard/plugin_api.py run_agent.py tools/approval.py tools/browser_tool.py tools/process_registry.py tools/send_message_tool.py tests/acp/test_registry_manifest.py tests/hermes_cli/test_skin_engine.py tests/test_hermes_logging.py tests/test_tota_brand_pass.py`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main`
