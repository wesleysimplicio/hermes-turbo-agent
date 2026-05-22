# Tota Agent vs Hermes 0.14.0

- Generated: 2026-05-19 17:21:45 -0300
- Stock ref: `v2026.5.16` (`version = 0.14.0`)
- Local Python: `C:\Users\wesley.simplicio\AppData\Local\Microsoft\WindowsApps\python.EXE`
- Stock Python: `temporary stock venv\Scripts\python.exe`
- Browser benchmark: **blocked**
- Measured rows: **3 wins / 2 losses / 1 ties / 1 blocked** for Tota Agent on this host

## Side-by-side rows

| Row | Hermes 0.14.0 | Tota Agent | Winner | Delta | Notes |
| --- | ---: | ---: | --- | --- | --- |
| Cold start (import_model_tools proxy) | 4894.32 ms | 2866.11 ms | Tota Agent | 1.71x | Fresh subprocess import of model_tools as a cold-start proxy. |
| JSON dumps short payload | 6.719 us | 9.773 us | Hermes 0.14.0 | 0.69x |  |
| Tool-call parse | 2.735 us | 6.651 us | Hermes 0.14.0 | 0.41x |  |
| Token estimate batch | 453.374 us | 109.353 us | Tota Agent | 4.15x | Tota uses estimate_messages_tokens; stock uses estimate_messages_tokens_rough. |
| Async 1,000-task scheduler | 167.28 ms | 166.52 ms | Tota Agent | 1.00x | Tota run requested uvloop; stock stayed on default asyncio. |
| browser_console p99 | blocked | blocked | Blocked | - | Benchmark blocked on local Chrome startup. |
| Integration breadth | 31 | 31 | Tie | 1.00x | Counts Python gateway platform modules excluding __init__.py. |

## Blocker

No local Chrome/Chromium binary is available on this host, so the browser_console p99 row cannot run.

Because the browser row is still blocked and the measurable rows on this host land below the acceptance target, this pass does not regenerate `tota_agent_benchmark_report.pdf`.

## Commands

```bash
C:\Users\wesley.simplicio\AppData\Local\Microsoft\WindowsApps\python.EXE scripts/benchmark_tota_vs_hermes_0140.py --output-json C:\Users\wesley.simplicio\Documents\Codex\2026-05-18\termine-todas-as-issues-https-github-2\hermes-turbo-agent\docs\tota-benchmark-hermes-0.14.0.json --output-md C:\Users\wesley.simplicio\Documents\Codex\2026-05-18\termine-todas-as-issues-https-github-2\hermes-turbo-agent\docs\tota-benchmark-hermes-0.14.0.md
```
