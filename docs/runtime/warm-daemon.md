# Warm Daemon

The warm daemon keeps expensive runtime state hot for the `desktop` and `car`
Hermes profiles. Without it, every interaction pays the full cold-start cost:
tool registry scan, skill index build, provider metadata fetch, MCP/config
fingerprinting and session summary load.

## Quick start

```bash
# foreground (dev)
python -m hermes_cli.daemon start --profile desktop

# inspect
python -m hermes_cli.daemon status

# stop
python -m hermes_cli.daemon stop
```

The default socket lives at `~/.hermes/daemon.sock` with `0600` perms. Override
with `--socket /path/to/sock`.

## Profiles

| Profile | Preloads |
|---------|----------|
| `desktop` | tool_registry, skill_index, provider_metadata, mcp_fingerprints, session_summaries |
| `car` | tool_registry, skill_index, provider_metadata |

`car` is intentionally lean — the hardware budget is tight and conversational
latency matters more than recall.

## systemd

Drop the unit files in `docker/systemd/` into `~/.config/systemd/user/` (user
service) or `/etc/systemd/system/` (system service):

```bash
cp docker/systemd/hermes-daemon-desktop.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-daemon-desktop.service
```

For the car profile swap `desktop` → `car`. Both units ship CPU/memory
guardrails (see AGENTS.md yool/tuple/HAMT §11) so a runaway preload cannot
fry the host.

## Invalidation

Config, plugin, skill or tool changes can stale a cache. Force a refresh:

```bash
python -m hermes_cli.daemon invalidate skill_index
python -m hermes_cli.daemon invalidate tool_registry
```

A file-watcher hook is planned (`watchdog` on `skills/`, `plugins/`, `tools/`
and the active config) but lives outside this initial scaffold.

## Fallback when daemon is offline

Every client call goes through `_client_request`. If the socket is missing or
unresponsive, the response is:

```json
{"ok": false, "error": "...", "fallback": "cold"}
```

Callers MUST treat `fallback: cold` as a signal to re-run the regular cold
path. The daemon is an optimization — never a hard dependency. UX never blocks
on it.

## Protocol

UNIX socket, line-oriented JSON. Operations:

| op | payload | response |
|----|---------|----------|
| `status` | — | `{ok, profile, uptime_s, caches[]}` |
| `ping` | — | `{ok, pong}` |
| `invalidate` | `{cache: "..."}` | `{ok, invalidated}` |
| `shutdown` | — | `{ok, bye}` |

## Security

- Socket perms: `0600` (owner only).
- Daemon never executes arbitrary code from requests.
- No network listener. Local UNIX socket only.
