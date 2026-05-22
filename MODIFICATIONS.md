# MODIFICATIONS — Hermes Turbo Agent

> Arquivo único de consolidação das anotações de modificação do repositório
> `wesleysimplicio/hermes-turbo-agent`. Reúne, sem duplicar, o que está
> espalhado em `PRD.md`, `PROGRESS.md`, `GOAL_RESULT.md`, `CHANGELOG.md`,
> `RELEASE_v*.md` e os planos individuais em `.plans/`. A seção final
> sintetiza melhorias a partir de
> [`llm-project-mapper`](https://github.com/wesleysimplicio/llm-project-mapper)
> e [`simplicio-prompt`](https://github.com/wesleysimplicio/simplicio-prompt).

---

## 1. Estado atual

| Eixo | Status |
|---|---|
| Backlog de token-economy / runtime telemetry (issues #81-#103) | **Fechado** — entregue via PRs #106-#128 + branch de gap-fill (#129) |
| Validação targeted | 159 testes (suíte unitária focada) + 5/5 compression-safety + 5/5 clawbench |
| Bloqueios | Nenhum |
| Branch ativo | `claude/hermes-turbo-agent-improvements-uNNDX` |
| Release line | `v0.14.x` (último: `0.14.2` — lazy-install advisory guard) |

Documentos de governança (não alterar conteúdo, só refletir aqui):

- `PRD.md` — template de PRD genérico (source of truth para qualquer task longa).
- `PROGRESS.md` — log de checkpoints do ciclo atual.
- `GOAL_RESULT.md` — relatório final do ciclo atual.
- `CHANGELOG.md` — Keep-a-Changelog (`[Unreleased]` cobre #81-#103).
- `RELEASE_v*.md` — 19 notas de release (v0.2.0 → v0.14.2).
- `.plans/issue-*.md` — 24 planos de issue (#81-#103 + extras).
- `.agents/AGENTS.yool.md` — manifesto canônico de capacidades yool.
- `docs/agents/yool-capability.md` — schema yool/tuple/HAMT.
- `.specs/architecture/ADR-001-yool-capability-addressing.md` — decisão de adoção.

---

## 2. Modificações por área (issues #81-#103)

### 2.1 Token-saver (compressão de output e bridge externo)

- **`agent/token_saver/proxy.py`** (#88) — truncamento head/tail com
  expansão por handle.
- **`agent/token_saver/backend.py`** (#94) — seletor `native|rtk|auto`
  via env `HERMES_TOKEN_SAVER_BACKEND`. Fallback nativo se `rtk`
  falhar ou exceder timeout.
- **`tests/test_evidence_store.py`** (#89) — evidence handles: dump
  completo em disco, fetch por handle on demand.
- **`agent/adapters/`** (#90) — `github_compact.py` + `ci_compact.py`:
  resumos slim de `gh issue|pr` JSON e falhas de CI agrupadas.
- **`tests/eval/compression_safety/`** (#95) — golden fixtures que
  asseguram preservação de sinal (failing tests, lint, type, CI, grep,
  diff).
- **`docs/perf/token-saver-proxy.md`**, **`docs/perf/compact-adapters.md`**,
  **`docs/integrations/rtk-bridge.md`**.

### 2.2 Context working set (expand-on-demand)

- **`agent/context/working_set.py`** (#92) — LRU hot set + cold-ref
  store com `expand(handle)`. Stdlib puro.
- **`agent/context/retrieval.py`** (#92) — scorer TF-IDF stdlib para
  priorizar handles a expandir.
- **`agent/context/token_cache.py`** (#83) — cache incremental
  blake2b, scoped por modelo, LRU.
- **`agent/context/incremental.py`** (#83) — pipeline incremental.
- **`docs/perf/working-set.md`**, **`docs/perf/token-throughput.md`**.

### 2.3 Telemetry (stage timing + cache usage + token savings)

- **`agent/telemetry/stage_timing.py`** (#82) — timers por estágio com
  breakdown provider/model/tool e dashboard stdout.
- **`agent/telemetry/cache_usage.py`** (#96) — parse de
  `cache_*_input_tokens` (Anthropic) e `cached_tokens` (OpenAI).
- **`agent/telemetry/token_savings.py`** + **`gain_analytics.py`**
  (#91) — JSONL ledger + CLI de agregação.
- **`docs/perf/dashboard.md`**, **`docs/perf/cache-boundary-tests.md`**,
  **`docs/perf/token-savings-analytics.md`**.

### 2.4 Budget governor + router determinístico

- **`agent/governor/budget.py`** + **`policies.py`** (#93) — budgets
  por token/cost/iteration; warn-70%, stop-100%.
- **`agent/router/deterministic.py`** + **`fallback.py`** (#99) —
  regras regex → respostas/tool-calls; conta chamadas LLM evitadas.
- **`docs/runtime/budget-governor.md`**,
  **`docs/runtime/deterministic-router.md`**.

### 2.5 Lazy schemas + skill metadata + contratos concisos

- **`agent/registry/lazy_schema.py`** + **`skill_meta.py`** (#98) —
  registro com stub `(name, description)`; schema completo on demand.
- **`agent/contracts/concise_response.py`** (#101) — `TerseAnswer`,
  `ToolCall`, `Diagnostic` com `max_chars` cap.
- **`docs/perf/lazy-schemas.md`**, **`docs/perf/concise-contracts.md`**.

### 2.6 Distributed + warm daemon

- **`agent/distributed/protocol.py`** (#97) — dataclass wire protocol
  para node host distribuído.
- **`docs/adr/0006-distributed-node-host.md`** +
  **`docs/distributed/overview.md`**.
- **`hermes_cli/daemon.py`** (#81) — warm daemon que pré-carrega
  registry de tools, índice de skills, metadados de provider.
- **`docs/runtime/warm-daemon.md`**.

### 2.7 Upstream sync + benchmark refresh

- **`scripts/upstream-sync/`** (#85) — capture/reapply de updates
  upstream.
- **`.upstream-sync-policy.yml`** + **`scripts/validate_sync_policy.py`**
  (#86) — policy declarativa.
- **`scripts/refresh_sync_benchmarks.py`** (#87) — refresh automático
  pós-sync.
- **`docs/upstream-sync/playbook.md`** + **`policy.md`**.

### 2.8 Yool / Tuple / HAMT

- **`docs/YOOL_TUPLE_HAMT.md`** (spec v0.2 vendored).
- **`AGENTS.md`** + **`CLAUDE.md`** + **`.github/copilot-instructions.md`**
  com bloco yool obrigatório (cpu_quota_pct, disk_quota_mb, timeout_s).
- **`.catalog/`** skeleton (`README.md`, `.gitkeep`, `receipts/.gitkeep`).
- **`scripts/build_hamt_catalog.py`** (#102) — parser de AGENTS.md →
  `.catalog/hamt.json` (Bagwell 2001: BRANCH=32, MAX_LEVELS=6,
  HASH_BITS=30, blake2b).
- **`.agents/AGENTS.yool.md`** — manifesto canônico.
- **`docs/agents/yool-capability.md`**.

### 2.9 RTK CLI + eval harness

- **`.skills/rtk-cli/SKILL.md`** (#103) — playbook plain→rtk com
  fallback se binário ausente.
- **`docs/integrations/rtk-cli.md`**, **`docs/integrations/rtk-bridge.md`**.
- **`eval/clawbench/runner.py`** (#100) — harness ClawBench/WildClawBench
  com scorers exact + soft.
- **`docs/eval/clawbench.md`**, **`docs/eval/compression-safety.md`**.

### 2.10 Sidecar evaluation + prompt cache

- **`docs/perf/sidecar-benchmark-plan.md`** (#84) — comparação
  pure-Python/uvloop vs Node/libuv vs Rust/Tokio.
- **`docs/adr/0005-prompt-cache-stable-prefix.md`** +
  **`tests/test_prompt_cache_stability.py`** (#96).

---

## 3. Histórico de releases (resumo)

| Versão | Tema |
|---|---|
| v0.2.0 – v0.9.0 | Ciclos iniciais (provider mix, skill commands, observability). |
| v0.10.0 | Marco de stabilization. |
| v0.11.0 – v0.12.0 | Multi-IDE adapters, ACP, OpenAI server. |
| v0.13.0 – v0.13.4 | Reapply automático de upstream Hermes. |
| v0.14.0 | Sync Hermes 0.14.x (lazy-install). |
| v0.14.1 | Patch de packaging. |
| v0.14.2 | Supply-chain advisory guard (lazy-install). |

Próxima janela: `[Unreleased]` no `CHANGELOG.md` agrupa toda a entrega
de token-economy + runtime-telemetry (#81-#103). Recomenda-se cortar
**v0.15.0** com esse bloco.

---

## 4. Validação (snapshot mais recente)

```bash
python -m pytest \
  tests/token_saver tests/router tests/agent/telemetry tests/registry \
  tests/contracts tests/agent/test_token_cache.py \
  tests/agent/test_governor.py tests/test_ci_compact.py \
  tests/test_github_compact.py tests/test_evidence_store.py \
  tests/test_prompt_cache_stability.py tests/scripts -o addopts=""
python tests/eval/compression_safety/runner.py
python eval/clawbench/runner.py
python scripts/build_hamt_catalog.py --print-list
```

Resultado: **159 passed**, **5/5** golden fixtures, **5/5** ClawBench,
catálogo HAMT parseando `AGENTS.md`.

Riscos abertos (do `GOAL_RESULT.md`):

- Catálogo HAMT precisa rebuild quando `AGENTS.md` ganhar novos blocos.
- RTK backend depende de binário externo (fallback verificado).
- Stage timing/cache usage in-memory — flush manual para sessões longas.
- `tests/agent/test_markdown_tables.py` tem erro de collection pré-existente
  fora de escopo.

---

## 5. Como evoluir o Hermes com `llm-project-mapper` e `simplicio-prompt`

### 5.1 O que cada repo entrega

**`wesleysimplicio/llm-project-mapper`** (Node CLI, TS/JS, zero
dependencies de produção):

- Scaffold AI-friendly que injeta `.specs/`, `.skills/`, `.agents/`,
  `AGENTS.md`, `CLAUDE.md`, `INIT.md`, `.starter-meta.json`,
  `.catalog/agents.json`, workflows DoD em qualquer repo.
- **Heurística de stack** por leitura de manifestos (`package.json`,
  `pyproject.toml`, `go.mod`, `Cargo.toml`, `*.csproj`, `pubspec.yaml`,
  `composer.json`, `Gemfile`, `mix.exs`, `pom.xml`, `build.gradle*`).
- **`.starter-meta.json`** declarando `managed_paths` +
  `read_only_globs` + `init_must_merge` + `init_must_ask`: contrato
  de containment.
- **`bin/build-hamt-catalog`**: wrapper que invoca
  `scripts/build_hamt.py` e materializa `.catalog/agents.json`
  append-only.
- **Receipts append-only** em `.receipts/` (sha256 content-hash,
  status, `cost.tokens`).
- Handoff documentado para 13 CLIs (Claude Code, Codex, Copilot,
  Cursor, Aider variantes, Hermes, OpenClaw).
- **Loop obrigatório**: read → plan → edit → lint → unit → e2e → fix
  → commit.
- **Definition of Done gate** via `.github/workflows/dod.yml`.

**`wesleysimplicio/simplicio-prompt`** (Node CLI, zero deps,
companion):

- Distribui **um único runtime prompt** (Tuple-Space + Yool safe-speed)
  para 8 targets (Claude Code, Codex, Hermes, OpenCode/OpenClaw,
  Cursor, Copilot, Cline, Aider) — `targets.mjs` mapeia
  target → arquivo de regra + formato.
- **Bloco delimitado idempotente**:
  `<!-- simplicio-prompt:start --> … <!-- simplicio-prompt:end -->`.
- **Response contract bracketed** (`[Tuple Space Snapshot]`,
  `[Active Agents/Subagents]`, `[Total Agents/Subagents]`,
  `[Próximo Yool a executar]`, `[Resultado parcial]`) com toggles por
  env `YOOL_TUPLE_STATUS*`.
- **Safe-speed path** antes de qualquer LLM call: receipt cache,
  concorrência adaptativa, jittered backoff, circuit breaker,
  small-task batching, compressão de contexto.
- **API JS**: `getPrompt()`, `getPromptPath()`, `getPromptSection()`,
  `getTargets()`, `findTarget()`.
- **Default silent**, opt-in verbose via env.

### 5.2 Onde Hermes já cobre (não duplicar)

| Primitiva externa | Equivalente Hermes |
|---|---|
| YOOL/HAMT spec + catálogo | `docs/YOOL_TUPLE_HAMT.md`, `scripts/build_hamt_catalog.py`, `.catalog/`, `.agents/AGENTS.yool.md` |
| Skills folder reusáveis | `.skills/rtk-cli/`, `skills/`, `optional-skills/` |
| Receipts (auditoria) | `agent/telemetry/token_savings.py` (JSONL ledger) + evidence handles |
| Response contract conciso | `agent/contracts/concise_response.py` (`TerseAnswer`/`ToolCall`/`Diagnostic`) |
| Loop obrigatório do agente | `CLAUDE.md` "Loop Behavior" + `AGENTS.md` |
| Compressão de contexto antes de LLM | `agent/context_compressor.py`, `trajectory_compressor.py`, `agent/token_saver/proxy.py` |
| Backoff/circuit breaker | `agent/retry_utils.py`, `agent/nous_rate_guard.py`, `agent/rate_limit_tracker.py` |

### 5.3 Lacunas concretas + propostas (priorizadas)

**P1 — Project fingerprint (`agent/project_mapper/`)**

- *Por que*: hoje `agent/subdirectory_hints.py` dá pistas, mas não há
  um detector central que produza um `project.fingerprint.json` com
  stack + auth + DB + monorepo flag. `llm-project-mapper` mostra que
  90% do sinal vem de heurística por manifesto — barato e
  determinístico, perfeito para o no-LLM router (#99).
- *Como*: novo módulo `agent/project_mapper/` (puro stdlib, sem deps)
  que parseia `package.json`, `pyproject.toml`, `go.mod`,
  `Cargo.toml`, `*.csproj`, `pubspec.yaml`, `composer.json`,
  `Gemfile`, `mix.exs`, `pom.xml`, `build.gradle*` e emite
  `working_set.add(kind="fingerprint", ...)`. Plugar antes do warm
  daemon (#81) cold start.
- *Custo*: ~1 dia. ~250 linhas + ~6 testes.

**P2 — Safety contract `.hermes-meta.json` (containment declarativo)**

- *Por que*: Hermes hoje confia em CLAUDE.md ("não rewrite unrelated
  architecture") como guideline em texto livre. O `.starter-meta.json`
  do `llm-project-mapper` (`read_only_globs`, `init_must_merge`,
  `init_must_ask`) é executável e auditável.
- *Como*: adicionar carregamento em `agent/file_safety.py` (já existe)
  para enforce `read_only_globs` via fnmatch antes de qualquer Write/Edit;
  emitir Diagnostic quando bloqueado. `init_must_ask` vira hook na CLI
  para pedir confirmação.
- *Custo*: ~0.5 dia. Schema mínimo, validador, hook em `file_safety`.

**P3 — Hermes Prompt Sync (CLI multi-IDE, inspirado em
`simplicio-prompt`)**

- *Por que*: Hermes mantém seu próprio runtime em `CLAUDE.md`,
  `AGENTS.md`, `.github/copilot-instructions.md`, mas não há um
  comando único que (re)injete o bloco canônico em **outros** repos
  onde o usuário queira rodar Hermes. `simplicio-prompt` resolve
  exatamente isso para 8 targets.
- *Como*: novo subcomando `hermes prompt sync [--target <id>]
  [--install-all] [--dry-run]` em `hermes_cli/` que escreve em
  `CLAUDE.md`/`AGENTS.md`/`.cursorrules`/`.github/copilot-instructions.md`/
  `.codex/AGENTS.md` etc. usando bloco delimitado
  `<!-- hermes-turbo:start --> … <!-- hermes-turbo:end -->` para
  re-injeção idempotente. Templates em `prompts/runtime/` (já existe a
  pasta `prompts/`).
- *Custo*: ~1 dia. Mapa target → caminho + formato (`block` / `mdc` /
  `raw`) e re-injetor.

**P4 — Toggles do response contract via env**

- *Por que*: o bracketed-output do CLAUDE.md ("`[Tuple Space Snapshot]
  … [Resultado parcial]`") é always-on hoje. `simplicio-prompt` torna
  cada campo opcional via env (`YOOL_TUPLE_STATUS`,
  `YOOL_TUPLE_STATUS_SNAPSHOT`, `_ACTIVE`, `_TOTAL`, `_NEXT`,
  `_PARTIAL`). Default silent + opt-in verbose alinha com
  token-economy.
- *Como*: `agent/contracts/concise_response.py` ganha
  `TupleStatusEnvelope` lendo essas envs; CLAUDE.md passa a documentar
  os toggles. Default `false` (silent) preservando o atual quando
  `HERMES_RUNTIME_VERBOSE=true`.
- *Custo*: ~0.5 dia + atualização de docs.

**P5 — Definition-of-Done gate (`.github/workflows/dod.yml`)**

- *Por que*: `llm-project-mapper` materializa o DoD como workflow CI.
  Hermes tem `.github/workflows/` mas não um `dod.yml` explícito que
  rode a sequência `lint → unit → e2e → secret-scan → compression-safety
  → clawbench` como gate de merge.
- *Como*: novo workflow `.github/workflows/dod.yml` agregando os
  comandos do bloco de "Validação" deste arquivo + `ruff` + secret
  scanning.
- *Custo*: ~0.5 dia. Sem código novo, só pipeline.

**P6 — `hermes prompt section <name>` (sub-prompts para subagentes)**

- *Por que*: `simplicio-prompt.getPromptSection()` extrai "## Prompt"
  até o próximo header. Em Hermes, subagentes hoje recebem todo o
  CLAUDE.md/AGENTS.md (caro). Servir só a seção relevante economiza
  centenas de tokens por dispatch.
- *Como*: utilitário stdlib em `hermes_cli/prompt_section.py` +
  cache LRU. Integrar no spawn de subagents (`agent.ops.runtime_dispatch`).
- *Custo*: ~0.5 dia.

**P7 — Receipts append-only canonicalizados**

- *Por que*: o `agent/telemetry/token_savings.py` já é JSONL ledger;
  `llm-project-mapper` formaliza receipts com `sha256` do conteúdo +
  `status` + `cost.tokens` em `.receipts/`. Convergir para um schema
  único permite o `scripts/build_hamt_catalog.py` indexar receipts
  por content-hash (já é HAMT compatível).
- *Como*: estender `token_savings.record_token_saving` para emitir
  também em `.receipts/<sha>.json` quando
  `HERMES_RECEIPTS_DIR` estiver setado; adicionar leitor no builder
  HAMT.
- *Custo*: ~1 dia. Implementação + migração de schema.

**P8 — Smoke test BASE_URL-driven**

- *Por que*: `llm-project-mapper` entrega `tests/e2e/smoke.spec.ts`
  como contrato mínimo do projeto. Hermes tem testes ricos, mas não
  um smoke padronizado que rode `HERMES_BASE_URL` (gateway/TUI).
- *Como*: opcional — `tests/e2e/smoke_gateway.py` que faz `GET /healthz`
  no gateway e um `agent.echo` round-trip. Marcar `@pytest.mark.e2e`.
- *Custo*: ~0.5 dia. Baixa prioridade — só fechar gap de paridade.

**P9 — Auto-detect de monorepo (workspace signals)**

- *Por que*: Hermes hoje trata o repo como árvore plana; um working
  set ciente de workspace (npm/pnpm/yarn workspaces, Cargo workspaces,
  Go modules multi-pkg) sobe a precisão do retrieval TF-IDF (#92).
- *Como*: extensão de P1 (`project_mapper`) detectando workspace e
  emitindo `WorkingSet.scope = "workspace:foo"` para particionar o
  hot set.
- *Custo*: incremental sobre P1.

**Não recomendado portar** (decisão consciente):

- *Frontmatter MDC do `simplicio-prompt`* — específico para Cursor;
  Hermes não precisa hoje.
- *Hilbert-indexed `batch_spawn`* citado nos AGENTS.md externos —
  Hermes já tem `agent/async_utils.py` + `agent/distributed/`; importar
  o termo seria cosmético.
- *Auto-criação de `.specs/sprints/`* — Hermes usa `.plans/` e
  `docs/SPRINT_BACKLOG.md`, não converter.

### 5.4 Ordem sugerida de execução

1. **P1 + P2** juntos (1.5 dia) — fingerprint + safety meta dão a
   base "project-aware" para tudo abaixo. — **DONE** (commit batch turbo-2).
2. **P4 + P6** (1 dia) — economia de tokens imediata, baixo risco. —
   **DONE** (commit batch turbo-2).
3. **P3** (1 dia) — habilita Hermes como prompt-runtime portável. —
   **DONE** (commit batch turbo-2).
4. **P5** (0.5 dia) — fecha o loop de qualidade via CI. — **DONE**
   (`.github/workflows/dod.yml`).
5. **P7** (1 dia) — convergência de schema de auditoria. — **DONE**
   (`agent/telemetry/receipts.py`).
6. **P9 + P8** (1 dia) — paridade incremental. — *pendente, baixa
   prioridade*.

Total estimado: ~6 dias de trabalho focado, todos changes incrementais
e reversíveis. Cada P abre uma issue independente e vira um PR pequeno.

## 6. Post-mortem cleanup (turbo-3) — what was undone and why

After the segmented benchmark (`docs/perf/turbo-full-segments.json`) the user
opted for the **strict literal interpretation** of "undo everything that lost
in the benchmark": every customisation whose measured turbo path was slower
than the naïve upstream-equivalent baseline was removed from the fork.

This is documented honestly because some removals throw away genuine
out-of-band value (token savings, governance, safety, auditability) that the
latency-only microbenchmark could not capture. They can be restored at any
time from git history.

### 6.1 Removed (80+ files across 11 directories)

| Module | Removed because | Real value lost |
|---|---|---|
| `agent/adapters/` (#90) | 0.01–0.09× | Compact `gh issue|pr` + CI log summaries; cut JSON payload sent to LLM. |
| `agent/contracts/` (#101, P4) | 0.12–0.16× | Output-token caps on `TerseAnswer`/`ToolCall`/`Diagnostic`. |
| `agent/context/` (#83, #92) | 0.04–0.70× | LRU hot/cold working set, TF-IDF retrieval, token cache. |
| `agent/governor/` (#93) | 0.06× | Budget warn-70%/stop-100% guardrail. |
| `agent/registry/` (#98) | 0.07–0.50× | Lazy JSON schema loading. |
| `agent/meta_contract.py` + `.hermes-meta.json` (P2) | 0.04× | Containment via `read_only_globs`. |
| `agent/distributed/` (#97) | net-new but unused | Dataclass protocol without a host implementation. |
| `agent/token_saver/` (#88) | 0.00× | Head/tail truncation + evidence handles for verbose shell. |
| `agent/telemetry/{cache_usage,dashboard,gain_analytics,stage_timer,stage_timing,token_savings}.py` (#82, #91, #96) | 0.09–0.11× | Anthropic/OpenAI cache parsing, runtime dashboard, savings ledger. |
| `hermes_cli/{prompt_sync,prompt_section}.py` (P3, P6) | 0.06–0.21× | Multi-IDE rule distribution, markdown section extractor for subagents. |
| `scripts/build_hamt_catalog.py` + `.catalog/` (#102) | 0.09–0.85× | HAMT capability addressing per yool spec v0.2. Over-engineered for 11 entries. |

Also removed: associated tests, docs (`docs/perf/{compact-adapters,concise-contracts,lazy-schemas,cache-boundary-tests,token-saver-proxy,token-savings-analytics,token-throughput}.md`, `docs/runtime/budget-governor.md`, `docs/integrations/rtk-bridge.md`, `docs/agents/yool-capability.md`, `docs/context/`, `docs/eval/compression-safety.md`, `.specs/architecture/ADR-001-yool-capability-addressing.md`).

### 6.2 Kept

- `agent/project_mapper/` — **33.97× win** (manifest heuristics vs tree walk).
- `agent/router/deterministic.py` + `fallback.py` — **133.25× win** (skips LLM call on trivial intents).
- `agent/telemetry/receipts.py` — parity with md5 (0.79× sha256 is the cost of integrity); kept for `lookup_receipt` cache short-circuiting.
- `scripts/benchmark_*` + `scripts/generate_*_pdf.py` — benchmark + PDF generation harness.
- `scripts/upstream-sync/` + `.github/workflows/upstream-sync-daily.yml` — daily upstream capture.
- `.github/workflows/dod.yml` — trimmed to the surviving surface.
- `.agents/AGENTS.yool.md` — trimmed to 8 yool blocks (was 13).

### 6.3 Validation after cleanup

- `pytest tests/agent/project_mapper tests/router tests/agent/telemetry/test_receipts.py` → **42 passed**.
- `python scripts/benchmark_full_turbo_segments.py --iters 500` → 4 stages, 2 winners, 1 parity, 1 net-new.
- Regenerated PDFs: `docs/perf/turbo-vs-baseline.pdf`, `docs/perf/turbo-full-segments.pdf`.

### 6.4 Restoring

Any removed module can be restored with::

    git show <pre-cleanup-sha>:agent/contracts/concise_response.py > agent/contracts/concise_response.py

The pre-cleanup sha is the tip of `claude/hermes-turbo-agent-improvements-uNNDX`
before the cleanup commit (run `git log --oneline` and pick the commit before
`feat(perf): full segmented benchmark`).

### 5.6 Entregue neste ciclo (turbo-2)

- **P1** `agent/project_mapper/fingerprint.py` + 6 testes — detect_fingerprint
  por manifesto (Node, Python, Go, Rust, Java, Kotlin, Ruby, PHP, Elixir,
  Dart, Swift, Deno) + workspaces (npm/pnpm/Cargo) + entrypoints.
- **P2** `.hermes-meta.json` + `agent/meta_contract.py` + 9 testes —
  containment declarativo: `read_only_globs` (block), `init_must_ask` (ask),
  `init_must_merge` (warn), `managed_paths` (allow).
- **P3** `hermes_cli/prompt_sync.py` + `prompts/runtime/hermes-turbo.md`
  + 8 testes — bloco delimitado idempotente injetado em 8 targets
  (claude, agents, copilot, codex, cursor, cline, aider, hermes).
- **P4** `TupleStatusEnvelope` em `agent/contracts/concise_response.py`
  + 6 testes — default silent + opt-in verbose via 6 envs.
- **P5** `.github/workflows/dod.yml` — gate único: ruff + unit suite
  (turbo + legado) + compression-safety + clawbench + HAMT + benchmark
  smoke.
- **P6** `hermes_cli/prompt_section.py` + 6 testes — extrai seção
  markdown por header, LRU 64 entradas.
- **P7** `agent/telemetry/receipts.py` + 5 testes — receipts
  append-only `.receipts/<sha>.json` por content-hash sha256.
- **Benchmark** `scripts/benchmark_turbo_vs_baseline.py` +
  `docs/perf/turbo-vs-baseline.md` + `docs/perf/turbo-vs-baseline-baseline.json` —
  9 estágios, p50/p95, speedup vs baseline naïve.
  - Wins reais: `project_mapper` **36.65x**, `router determinístico`
    **157.30x** (vs proxy de 100 µs; vs LLM real, ordens de magnitude
    maior).
- **Upstream daily sync** `.github/workflows/upstream-sync-daily.yml` —
  cron 06:00 UTC capturando NousResearch/hermes-agent, reaplicando
  patches sobre turbo, regerando benchmarks, abrindo PR draft
  rotulado `upstream-sync`.

Validação (turbo-2):
- 40 testes novos passando (project_mapper 6, meta_contract 9, tuple
  envelope 6, receipts 5, prompt_sync 8, prompt_section 6).
- 170 testes legados continuam verdes (era 159 — 11 incrementais).
- Compression-safety 5/5; ClawBench 5/5; HAMT `--print-list` OK.

### 5.5 Critério de "feito" para esta evolução

- Cada proposta P1–P9 vira uma issue com título prefixado por
  `feat(integration):` e body apontando para a seção 5.3 deste
  arquivo.
- `MODIFICATIONS.md` é o documento vivo: ao concluir um P,
  registrar no §2 (a área correspondente) e na §3 (release).
- `[Unreleased]` do `CHANGELOG.md` recebe entry resumindo a integração.
- `PROGRESS.md` é resetado por ciclo de trabalho; este arquivo
  permanece.

---

## 6. Referências cruzadas

| Tópico | Arquivo |
|---|---|
| Spec yool/tuple/HAMT v0.2 | `docs/YOOL_TUPLE_HAMT.md` |
| Manifesto de capacidades | `.agents/AGENTS.yool.md` |
| Plano por issue (#81-#103) | `.plans/issue-<n>-*.md` |
| Política upstream-sync | `.upstream-sync-policy.yml` |
| Backlog de sprint | `docs/SPRINT_BACKLOG.md` |
| ADRs | `docs/adr/*.md` |
| Runtime docs | `docs/runtime/*.md` |
| Perf docs | `docs/perf/*.md` |
| llm-project-mapper | <https://github.com/wesleysimplicio/llm-project-mapper> |
| simplicio-prompt | <https://github.com/wesleysimplicio/simplicio-prompt> |
| yool-tuple-hamt (spec canon) | <https://github.com/wesleysimplicio/yool-tuple-hamt> |
| rtk-ai (token-smart shell) | <https://github.com/rtk-ai/rtk> |
