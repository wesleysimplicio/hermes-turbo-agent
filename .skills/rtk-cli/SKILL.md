---
name: rtk-cli
description: Use RTK CLI (https://github.com/rtk-ai/rtk) to cut tokens during repo exploration and verbose validation
trigger: any task with shell-heavy exploration, git status/diff/log, grep/find, or verbose CLI validation
---

## Quando ativar

Sempre que a task envolver inspeção de repositório, git, grep/find ou validação verbosa, e o objetivo for **decisão técnica** (e não preservar output bruto como evidência).

## Steps (plain → rtk)

| Objetivo | Comando padrão | Comando RTK |
| --- | --- | --- |
| Ler arquivo curto | `cat AGENTS.md` | `rtk read AGENTS.md` |
| Buscar padrão | `grep -rn "pattern" hermes_cli/` | `rtk grep "pattern" hermes_cli/` |
| Encontrar arquivo | `find . -name "*.py"` | `rtk find "*.py" .` |
| Estado do git | `git status` | `rtk git status` |
| Diff | `git diff` | `rtk git diff` |
| Histórico curto | `git log -n 10` | `rtk git log -n 10` |
| Rodar pytest | `pytest -q` | `rtk pytest` |

## Do NOT route through RTK

- Prompts interativos (`gh auth login`, `npm init`).
- Streaming contínuo (`tail -f`, `gh run watch`).
- Output que é evidência verbatim (Playwright traces, screenshots, stack traces preservados em PR/issue).
- Comandos cujo retorno é consumido por outro processo (pipes em script).

## Trigger examples

- "Onde está a função X?" → `rtk grep`.
- "Mostre o status do branch antes de commitar." → `rtk git status` + `rtk git diff`.
- "Roda os testes rápidos pra ver se passou." → `rtk pytest`.
- "Lê o AGENTS.md desse repo." → `rtk read AGENTS.md`.

## Fallback

Se `rtk` não estiver no PATH, segue com o comando padrão sem bloquear. Nenhuma task depende de RTK.

## DoD

- Onde RTK aplicável, usado em vez do comando bruto.
- Output usado para tomar decisão, não para preservar evidência.
- Comandos não-aplicáveis (interativo, streaming, evidência) permaneceram no formato original.

## References

- Repo: https://github.com/rtk-ai/rtk
- Bloco RTK em `AGENTS.md` / `CLAUDE.md` / `.github/copilot-instructions.md` (marker `<!-- rtk-cli:start -->`).
