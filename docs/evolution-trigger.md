# Evolution Trigger — Auto-detection de Limitações do Simplicio

> **Issue:** [#175](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/175)
> **Script:** `scripts/evolution-trigger.py`
> **Status:** Implementado
> **Última atualização:** 2026-07-03

## Objetivo

Quando o Hermes Turbo precisar de uma ferramenta que o Simplicio Runtime não
tem (ou retorna erro), o Evolution Trigger detecta automaticamente a lacuna e
cria uma issue estruturada no repositório do runtime, sugerindo implementação
e priorizando baseado em frequência.

## Fluxo

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  Hermes tenta   │────>│  Simplicio retorna   │────>│ Evolution        │
│  usar tool do   │     │  erro ou não tem a   │     │ Trigger detecta  │
│  Simplicio      │     │  ferramenta          │     │ a lacuna         │
└─────────────────┘     └─────────────────────┘     └──────────────────┘
                                                           │
                                                           ▼
                                                    ┌──────────────────┐
                                                    │  Verifica se já  │
                                                    │  existe issue    │
                                                    │  duplicada       │
                                                    └──────────────────┘
                                                           │
                                                    (não duplicada)
                                                           ▼
                                                    ┌──────────────────┐
                                                    │  Cria issue      │
                                                    │  no repositório  │
                                                    │  do runtime      │
                                                    └──────────────────┘
                                                           │
                                                           ▼
                                                    ┌──────────────────┐
                                                    │  Sugere          │
                                                    │  implementação   │
                                                    │  concreta        │
                                                    └──────────────────┘
```

## Componentes

### 1. Script principal: `scripts/evolution-trigger.py`

Script Python que implementa todo o fluxo de detecção e reporte.

### 2. Cache de dedup: `~/.hermes_turbo/evolution-trigger-dedup.json`

Arquivo JSON que armazena o histórico de ferramentas já detectadas, contagem
de ocorrências, e URLs das issues criadas. Evita criar issues duplicadas.

### 3. Integração com GitHub CLI (`gh`)

Usa o `gh` CLI para criar issues no repositório configurado.

## Critérios de acionamento

O trigger só cria uma issue quando TODOS os critérios abaixo são atendidos:

1. **Tool não encontrada ou erro**: Simplicio retornou erro ou não tem a tool.
2. **Não duplicada**: Nenhuma issue aberta com o mesmo título/label existe no
   repositório.
3. **Cache limpo**: A tool não foi reportada anteriormente (verifica cache de
   dedup).

## Uso

### Modo básico (após falha de tool)

```bash
# Após Hermes encontrar erro ao chamar simplicio.edit
python3 scripts/evolution-trigger.py \
    --tool simplicio.edit \
    --error "tool not found" \
    --command "write_file('foo.py', content)" \
    --context "wanted to edit Python file"
```

### Dry-run (visualizar sem criar issue)

```bash
python3 scripts/evolution-trigger.py \
    --tool simplicio.edit \
    --error "tool not found" \
    --dry-run
```

### Sugestão manual

```bash
# Sugerir implementação de uma tool manualmente
python3 scripts/evolution-trigger.py \
    --suggest simplicio.new-tool \
    --suggestion-desc "Add file rename support with rollback"
```

### Instalar hook (integração automática com Hermes)

```bash
python3 scripts/evolution-trigger.py --install-hook
```

Instala um hook pós-tool que detecta automaticamente erros do Simplicio e
aciona o trigger.

### Reportar gaps pendentes

```bash
# Reporta todas as tools detectadas mas ainda não reportadas
python3 scripts/evolution-trigger.py --report-unreported
```

### Listar gaps detectados

```bash
python3 scripts/evolution-trigger.py --list-gaps
```

Exemplo de saída:

```
Tool                           Count    Status
----------------------------------------------
edit                           3        https://github.com/.../issues/42
web-search                     1        not reported
file_rename                    2        https://github.com/.../issues/45

Total gaps detected: 3
```

## Configuração via variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `HERMES_TURBO_RUNTIME_OWNER` | `wesleysimplicio` | Dono do repositório do runtime |
| `HERMES_TURBO_RUNTIME_REPO` | `hermes-turbo-agent` | Nome do repositório do runtime |
| `HERMES_TURBO_EVOLUTION_CACHE` | `~/.hermes_turbo/evolution-trigger-dedup.json` | Caminho do cache de dedup |

## Labels usadas

As issues criadas recebem as labels: `enhancement`, `evolution-trigger`, `simplicio`.

## Integração com CI/CD (opcional)

É possível configurar um cron job (via `launchd` no macOS ou `systemd` no
Linux) para executar periodicamente o reporte de gaps pendentes:

```bash
# Cron: toda segunda às 6h
0 6 * * 1 cd /path/to/hermes-turbo-agent && python3 scripts/evolution-trigger.py --report-unreported
```

## Exemplo de issue criada

Título: `[Evolution] Simplicio missing tool: simplicio.edit`

Corpo:
```
## 🧬 Evolution Trigger: `simplicio.edit`

### Context

Hermes Turbo attempted to use **`simplicio.edit`** but encountered an error.

- **Command**: `write_file('foo.py', content)`
- **Error**: `tool not found`
- **Scenario**: wanted to edit Python file

### Suggested Implementation

_TODO: Describe the expected tool interface, parameters, and return type._

```python
# Suggested signature for 'edit'
def edit(
    # TODO: define parameters
    ...
) -> dict:
    """
    edit: TODO - describe what this tool does.

    Returns:
        dict with result/error keys.
    """
    raise NotImplementedError
```

### Evidence

Collected automatically by `scripts/evolution-trigger.py`.
- **Timestamp**: 2026-07-03T12:00:00+00:00
- **Trigger**: Failed tool call

### Priority

Priority is determined by frequency of occurrence. If this tool is
requested multiple times, consider higher priority.
---
*This issue was automatically created by the Evolution Trigger system.*
```

## Manutenção

- O cache de dedup (`~/.hermes_turbo/evolution-trigger-dedup.json`) pode ser
  limpo manualmente se necessário:
  ```bash
  rm ~/.hermes_turbo/evolution-trigger-dedup.json
  ```
- Para redefinir o cache de uma tool específica, edite o JSON e remova a
  entrada ou ajuste o `count`.

## Referências

- Issue original: [#175](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/175)
- Script: `scripts/evolution-trigger.py`
- Cache: `~/.hermes_turbo/evolution-trigger-dedup.json`
- Guia de migração: `MIGRATION.md`
