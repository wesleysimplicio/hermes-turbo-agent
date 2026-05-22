# Issue #103: Integrate RTK CLI for token-smart shell

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/103

## Original description (excerpt)

```
# Integrate RTK CLI for token-smart shell

## Why

`rtk` (https://github.com/rtk-ai/rtk) is a thin shell wrapper that produces compact, agent-friendly output for `read/grep/find/git/npm`. Cuts ~40–70% of tokens during exploration and validation without losing technical signal. Standard tool across all `wesleysimplicio/*` AI-facing repos.

Reference: https://github.com/wesleysimplicio/llm-project-mapper/blob/main/AGENTS.md (section "Shell token-smart").

## Scope

1. **Add RTK section to `AGENTS.md`** (mirror in `CLAUDE.md` / `.github/copilot-instructions.md`):

```markdown
## Shell token-smart (RTK CLI, opcional)

Se `rtk` estiver instalado na máquina, prefira-o em tarefas shell-heavy e de exploração:

\`\`\`bash
rtk read AGENTS.md
rtk grep "pattern" src/
rtk find "*.ts" .
rtk git status
rtk git diff
rtk git log -n 10
rtk npm test
\`\`\`

Regras:
- Use `rtk read|grep|find|git ...` como primeira opção para inspeção textual compacta.
- Use `rtk <comando>` em validações verbosas quando o output resumido basta.
- **Não** passe por RTK comandos interativos, streaming, ou em que o output bruto é a evidência principal (`curl`, `playwright`, `gh pr view --web`, logs longos verbatim).
- Se `rtk` não estiver instalado, siga com os comandos normais sem bloquear a task.
```

2. **(Optional) Add `.skills/rtk-cli/SKILL.md`** skill manifest:

```markdown
---
name: rtk-cli
description: Use RTK CLI to reduce tokens during repo exploration (read/grep/find/git/npm).
trigger: any task involving repo inspection, git status/diff/log, grep/find across files, or verbose CLI validation.
---

## Steps
1. Detect `rtk` on PATH: `command -v rtk`.
2. Replace `cat <file>` with `rtk read <file>`.
3. Replace `grep -r "x" .` with `rtk grep "x" .`.
4. Replace `find . -name "*.ts"` with `rtk find "*.ts" .`.
5. Replace `git status|diff|log` with `rtk git status|diff|log`.
6. Replace verbose `npm test` smoke runs with `rtk npm test`.

## Do not RTK
- Interactive prompts (login flows, REPL).
- Streaming logs you need verbatim as evidence.
- Playwright runners (need full trace/screenshot output).
- `curl` calls where response body is the artifact.

## DoD
- AGENTS.md references RTK section.
- Skill manifest committed under `.skills/rtk-cli/SKILL.md`.
- README/skill index lists `rtk-cli` skill.
```

3. **Update onboarding/setup docs** to mention RTK install path (optional, never required): `https://github.com/rtk-ai/rtk`.

## Acceptance Criteria

- [ ] `AGENTS.md` has the "Shell token-smart (RTK CLI)" section.
- [ ] Section is mirrored in `CLAUDE.md` / `.github/copilot-instructions.md` if those exist.
- [ ] (Optional but recommended) `.skills/rtk-cli/SKILL.md` exists and is referenced in `.skills/README.md`.
- [ ] No hard dependency on `rtk` — repo still works fully if `rtk` is not installed.
- [ ] CHANGELOG entry mentions RTK CLI guidance.

## References

- RTK repo: https://github.com/rtk-ai/rtk
- Reference adoption: https://github.com/wesleysimplicio/llm-project-mapper (AGENTS.md "Shell token-smart" section)
```

## Implementation plan
- [ ] Read context (module / spec / ADR)
- [ ] Draft minimal change set
- [ ] Add tests (unit + e2e where applicable)
- [ ] Lint / typecheck / coverage >= 80% on diff
- [ ] Update CHANGELOG + docs
- [ ] Link ADR if architectural

## Definition of Done
Per AGENTS.md DoD: lint + unit + e2e green, evidence attached, AC checked, conventional commit.
