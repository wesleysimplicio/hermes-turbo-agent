# RTK Compatibility Bridge

Optional bridge for the [RTK token-saver CLI](https://github.com/rtk-ai/rtk).
When `rtk` is on `PATH`, shell-heavy commands can be routed through `rtk <cmd>`
to cut tokens spent on verbose output. Without `rtk` installed, Hermes Turbo
keeps its native behaviour — RTK is never required.

## Backend modes

Configured via `HERMES_TOKEN_SAVER`:

- `auto` (default): use `rtk` when detected and the command is allow-listed.
- `rtk`: always wrap with `rtk`; raises if missing.
- `native`: never use `rtk`.

Allow-list: `read`, `grep`, `find`, `git`, `npx`, `ls`, `cat`, `head`, `tail`.

## Quick check

```bash
scripts/check-rtk.sh
# backend=auto / rtk_available=1 / rtk_path=... / effective=rtk
```

Exit codes: `0` rtk active, `1` native fallback, `2` rtk requested but missing.

## Programmatic use

```python
from agent.adapters.rtk_bridge import wrap_command, describe

argv = wrap_command(["git", "log", "-n", "10"])
# -> ["rtk", "git", "log", "-n", "10"] when rtk available under auto/rtk
# -> ["git", "log", "-n", "10"]        otherwise
```

`wrap_command` is pure — the caller still executes the resulting argv.

## Safety

- Opt-in by env var; `native` disables without uninstalling.
- Allow-list, not denylist: new commands need an explicit code change.
- Evidence-bearing commands (Playwright traces, screenshots, streaming logs)
  should bypass the bridge to preserve raw output.
- `rtk` mode raises `RtkNotInstalledError` instead of silent fallback.

Issue: <https://github.com/wesleysimplicio/hermes-turbo-agent/issues/94>
