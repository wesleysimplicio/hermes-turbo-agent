#!/usr/bin/env bash
# ==============================================================================
# benchmark-compare.sh — Hermes vanilla vs Turbo nos mesmos cenários
#
# USO:
#   bash scripts/benchmark-compare.sh                    # Executa todos os cenários
#   bash scripts/benchmark-compare.sh --smoke             # 1 iteração rápida (CI)
#   bash scripts/benchmark-compare.sh --vanilla-binary PATH  # Caminho custom p/ vanilla
#   bash scripts/benchmark-compare.sh --turbo-binary  PATH   # Caminho custom p/ turbo
#   bash scripts/benchmark-compare.sh --json             # Saída JSON
#   bash scripts/benchmark-compare.sh --out results.json # Salva JSON
#
# CENÁRIOS (Issue #177):
#   1. Mapear repositório (project mapper)
#   2. Editar 10 arquivos
#   3. Buscar decisão anterior (memória)
#   4. Fan-out 50 sub-agentes
#   5. Pesquisar web + extrair conteúdo
#   6. Navegar browser + capturar screenshot
#
# MÉTRICAS:
#   - Tempo total (segundos)
#   - Tokens gastos (estimativa via saída --quiet)
#   - Custo estimado (USD, base modelo ~$3/M input + $15/M output)
#   - Precisão (erros/confabulações detectados)
# ==============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RESULTS_DIR="${BENCHMARK_RESULTS_DIR:-${REPO_ROOT}/benchmarks/results}"
DATE_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
COMMIT_SHA="${GITHUB_SHA:-$(cd "${REPO_ROOT}" && git rev-parse HEAD 2>/dev/null || echo unknown)}"
REF_NAME="${GITHUB_REF_NAME:-$(cd "${REPO_ROOT}" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)}"
OUT_JSON="${REPO_ROOT}/benchmarks/benchmark-compare-${DATE_UTC}.json"
OUT_MD="${REPO_ROOT}/BENCHMARKS.md"

# Binários — descobre ou usa defaults
VANILLA_BINARY=""
TURBO_BINARY=""

# Flags
SMOKE=false
JSON_OUT=false

# ── Help ──────────────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Uso: $(basename "$0") [opções]

Compara Hermes vanilla vs Turbo nos mesmos cenários de benchmark.

Opções:
  --smoke              Modo rápido (1 iteração por cenário, para CI)
  --vanilla-binary P   Caminho para o binário 'hermes' vanilla
  --turbo-binary  P    Caminho para o binário 'hermes' turbo (default: ./hermes)
  --json               Saída em JSON puro (stdout)
  --out PATH           Salvar resultados em arquivo JSON
  --help               Mostra esta ajuda
EOF
    exit 0
}

# ── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --smoke) SMOKE=true; shift ;;
        --json) JSON_OUT=true; shift ;;
        --vanilla-binary) VANILLA_BINARY="$2"; shift 2 ;;
        --turbo-binary) TURBO_BINARY="$2"; shift 2 ;;
        --out) OUT_JSON="$2"; shift 2 ;;
        --help) usage ;;
        *) echo "Erro: argumento desconhecido: $1"; usage ;;
    esac
done

# ── Detecta binários ─────────────────────────────────────────────────────────
if [[ -z "$TURBO_BINARY" ]]; then
    TURBO_BINARY="${REPO_ROOT}/hermes"
fi
if [[ ! -x "$TURBO_BINARY" ]]; then
    TURBO_BINARY="$(command -v hermes 2>/dev/null || echo '')"
fi
if [[ -z "$TURBO_BINARY" || ! -x "$TURBO_BINARY" ]]; then
    echo "ERRO: binário Hermes Turbo não encontrado. Use --turbo-binary ou execute de dentro do repositório."
    exit 1
fi

# Vanilla: se não foi passado, tenta descobrir via 'hermes-hermes' (upstream) ou pede
if [[ -z "$VANILLA_BINARY" ]]; then
    VANILLA_BINARY="$(command -v hermes-hermes 2>/dev/null || echo '')"
fi

# ── Setup vanilla environment ────────────────────────────────────────────────
SETUP_VANILLA=false
VANILLA_VENV=""
if [[ -z "$VANILLA_BINARY" || ! -x "$VANILLA_BINARY" ]]; then
    echo "→ Vanilla Hermes não encontrado. Provisionando ambiente isolado upstream..."
    SETUP_VANILLA=true
    VANILLA_VENV="$(mktemp -d "${REPO_ROOT}/.vanilla-bench-XXXXXX")"
    VANILLA_BINARY="${VANILLA_VENV}/bin/hermes"

    # Clone upstream (Hermes Agent) em cache local se não existir
    UPSTREAM_CACHE="${REPO_ROOT}/.upstream-cache"
    if [[ ! -d "$UPSTREAM_CACHE" ]]; then
        echo "   Clonando Hermes Agent upstream..."
        git clone --depth 1 https://github.com/NousResearch/hermes-agent.git "$UPSTREAM_CACHE" 2>&1
    fi

    echo "   Criando virtualenv em ${VANILLA_VENV}..."
    python3 -m venv "${VANILLA_VENV}"
    "${VANILLA_VENV}/bin/pip" install --quiet -e "$UPSTREAM_CACHE" 2>&1
    echo "   Vanilla instalado em ${VANILLA_BINARY}"
fi

echo "Binários:"
echo "  Vanilla: ${VANILLA_BINARY}  ($("${VANILLA_BINARY}" --version 2>&1 | head -1))"
echo "  Turbo:   ${TURBO_BINARY}    ($("${TURBO_BINARY}" --version 2>&1 | head -1))"

# ── Limpeza ───────────────────────────────────────────────────────────────────
cleanup() {
    if [[ "$SETUP_VANILLA" == "true" && -n "$VANILLA_VENV" ]]; then
        rm -rf "$VANILLA_VENV" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Funções auxiliares ───────────────────────────────────────────────────────

# run_scenario <binary> <label> <prompt> [toolset]
#   Executa um cenário, captura timing e tokens.
#   Saída: tab-separated: status\ttime_sec\ttokens_est\taccuracy_errors
run_scenario() {
    local binary="$1"
    local label="$2"
    local prompt="$3"
    local toolset="${4:-full}"  # default toolset full

    if [[ "$SMOKE" == "true" ]]; then
        local max_turns=3
    else
        local max_turns=20
    fi

    local start_time end_time elapsed
    local output_file tmp_out

    tmp_out="$(mktemp)"
    # Arquivo para stderr separado
    local err_out
    err_out="$(mktemp)"

    start_time="$(date +%s.%N)"

    # Executa com --quiet para saída programática
    if ! "${binary}" chat -q "${prompt}" --quiet -t "${toolset}" --max-turns "${max_turns}" >"${tmp_out}" 2>"${err_out}"; then
        echo "FAILED\t0\t0\t1"
        rm -f "${tmp_out}" "${err_out}"
        return
    fi

    end_time="$(date +%s.%N)"
    elapsed=$(python3 -c "print(${end_time} - ${start_time})" 2>/dev/null || echo "0")

    # Estima tokens: conta palavras da saída como proxy
    local word_count token_est
    word_count="$(wc -w <"${tmp_out}" 2>/dev/null || echo 0)"
    token_est=$((word_count * 3 / 2))  # ~1.5 token/palavra

    # Checa por erros/confabulações
    local errors=0
    if grep -qiE "(erro|error|desculpe|sorry|não.*consegui|could not|failed|exception)" "${tmp_out}" 2>/dev/null; then
        errors=$((errors + 1))
    fi
    if grep -qiE "(confabula|fabricat|invent|hallucinat)" "${tmp_out}" 2>/dev/null; then
        errors=$((errors + 1))
    fi

    echo "OK\t${elapsed}\t${token_est}\t${errors}"
    rm -f "${tmp_out}" "${err_out}"
}

# estimate_cost <total_tokens> — custo estimado USD (modelo misto ~$3/M input + $15/M output)
estimate_cost() {
    local tokens="$1"
    # Assume ~75% input, 25% output como fração conservadora
    python3 -c "
tokens = ${tokens}
input_tokens = int(tokens * 0.75)
output_tokens = tokens - input_tokens
cost = (input_tokens / 1_000_000 * 3) + (output_tokens / 1_000_000 * 15)
print(f'{cost:.6f}')
"
}

# ── Cenários ──────────────────────────────────────────────────────────────────
# Cada cenário é um prompt padronizado que será executado em ambos os agentes.

declare -a SCENARIO_LABELS
declare -a SCENARIO_PROMPTS
declare -a SCENARIO_TOOLSETS

SCENARIO_LABELS+=("mapear_repositorio")
SCENARIO_PROMPTS+=("Mapeie a estrutura deste repositório de software. Identifique as principais linguagens, frameworks, diretórios-chave (src, tests, docs, config) e a arquitetura geral. Produza um resumo conciso em markdown.")
SCENARIO_TOOLSETS+=("read")

SCENARIO_LABELS+=("editar_10_arquivos")
SCENARIO_PROMPTS+=("Crie 10 arquivos de exemplo em /tmp/bench-test-${DATE_UTC} com nomes de A até J (A.txt, B.txt, ... J.txt). Cada arquivo deve conter uma linha com seu nome e um UUID fictício. Após criar todos, leia cada um de volta para confirmar que foram escritos corretamente. Relate quantos foram criados e lidos com sucesso.")
SCENARIO_TOOLSETS+=("read,write")

SCENARIO_LABELS+=("buscar_decisao_anterior")
SCENARIO_PROMPTS+=("Busque no histórico de memória ou sessões anteriores alguma decisão técnica que tenha sido tomada sobre a estrutura de diretórios ou convenção de nomes neste projeto. Se não encontrar, relate 'nenhuma decisão anterior encontrada' e proponha uma convenção para nomes de arquivos de benchmark.")
SCENARIO_TOOLSETS+=("read")

SCENARIO_LABELS+=("fanout_50_agents")
SCENARIO_PROMPTS+=("Simule a delegação de 50 tarefas hipotéticas. Para cada uma, crie um dicionário com: 'id' (0-49), 'tarefa' (uma descrição curta e variada como 'calcular pi', 'escrever poema', 'listar diretório'), e 'status' ('pendente'). Após gerar todos os 50 itens, conte quantos são únicos (por tarefa) e reporte o resumo em formato de tabela markdown.")
SCENARIO_TOOLSETS+=("full")

SCENARIO_LABELS+=("pesquisar_web_extrair")
SCENARIO_PROMPTS+=("Pesquise na web sobre as últimas novidades em AI agents para 2026. Extraia 3 fontes/referências diferentes com título, URL e um parágrafo de resumo de cada uma. Organize em formato markdown.")
SCENARIO_TOOLSETS+=("web")

SCENARIO_LABELS+=("navegar_browser_screenshot")
SCENARIO_PROMPTS+=("Navegue até https://example.com usando o browser, capture a página e descreva o que vê. Extraia o título e o texto principal da página.")
SCENARIO_TOOLSETS+=("computer-use")


# ── Execução ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   Benchmark: Hermes vanilla vs Turbo nos mesmos cenários   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "Data: ${DATE_UTC}"
echo "Commit: ${COMMIT_SHA}"
echo "Modo: $([[ "$SMOKE" == "true" ]] && echo "SMOKE (1 iteração)" || echo "COMPLETO")"
echo ""

# Cabeçalho da tabela
printf "%-26s | %-10s | %-12s | %-12s | %-12s | %-10s | %-12s | %-12s | %-12s | %-10s\n" \
    "Cenario" "Versao" "Status" "Tempo(s)" "Tokens" "Custo(USD)" "Tempo(s)" "Tokens" "Custo(USD)" "Erros"
printf "%-26s | %-10s | %-12s | %-12s | %-12s | %-10s | %-12s | %-12s | %-12s | %-10s\n" \
    "" "" "" "Vanilla" "Vanilla" "Vanilla" "Turbo" "Turbo" "Turbo" ""
printf "%s\n" "$(printf '%.0s-' {1..140})"

declare -a RESULTS_JSON

for i in "${!SCENARIO_LABELS[@]}"; do
    label="${SCENARIO_LABELS[$i]}"
    prompt="${SCENARIO_PROMPTS[$i]}"
    toolset="${SCENARIO_TOOLSETS[$i]}"

    echo ""
    echo "▶ Cenário $((i+1)): ${label}"

    # ── Vanilla ──
    echo "   Vanilla: executando..."
    IFS=$'\t' read -r v_status v_time v_tokens v_errors <<< "$(run_scenario "${VANILLA_BINARY}" "${label}-vanilla" "${prompt}" "${toolset}")"
    v_cost="$(estimate_cost "${v_tokens}")"
    echo "     status=${v_status}  tempo=${v_time}s  tokens=${v_tokens}  custo=\$${v_cost}  erros=${v_errors}"

    # ── Turbo ──
    echo "   Turbo:   executando..."
    IFS=$'\t' read -r t_status t_time t_tokens t_errors <<< "$(run_scenario "${TURBO_BINARY}" "${label}-turbo" "${prompt}" "${toolset}")"
    t_cost="$(estimate_cost "${t_tokens}")"
    echo "     status=${t_status}  tempo=${t_time}s  tokens=${t_tokens}  custo=\$${t_cost}  erros=${t_errors}"

    # Comparação
    if [[ "$v_status" == "OK" && "$t_status" == "OK" ]]; then
        speedup=$(python3 -c "
vt=${v_time}
tt=${t_time}
if tt > 0:
    print(f'{vt/tt:.2f}')
else:
    print('inf')
" 2>/dev/null || echo "0")
    else
        speedup="N/A"
    fi

    printf "%-26s | %-10s | %-12s | %-12.2f | %-12s | %-10s | %-12.2f | %-12s | %-12s | %-10s\n" \
        "${label}" "vanilla" "${v_status}" "${v_time}" "${v_tokens}" "\$${v_cost}" "" "" "" "${v_errors}"
    printf "%-26s | %-10s | %-12s | %-12s | %-12s | %-10s | %-12.2f | %-12s | %-12s | %-10s\n" \
        "" "turbo" "${t_status}" "" "" "" "${t_time}" "${t_tokens}" "\$${t_cost}" "${t_errors}"

    if [[ "$speedup" != "N/A" ]]; then
        printf "%-26s | %-10s | %-12s | %-12s | %-12s | %-10s | %-12s | %-12s | %-12s | %-10s\n" \
            "" "speedup" "" "" "" "" "${speedup}x" "" "" ""
    fi

    # Acumula JSON
    RESULTS_JSON+=("$(cat <<EOF
    {
      "cenario": "${label}",
      "vanilla": {
        "status": "${v_status}",
        "time_sec": ${v_time},
        "tokens": ${v_tokens},
        "cost_usd": ${v_cost},
        "errors": ${v_errors}
      },
      "turbo": {
        "status": "${t_status}",
        "time_sec": ${t_time},
        "tokens": ${t_tokens},
        "cost_usd": ${t_cost},
        "errors": ${t_errors}
      },
      "speedup_x": $( [[ "$speedup" != "N/A" ]] && echo "${speedup}" || echo "null" )
    }
EOF
)")
done

# ── Saída JSON ───────────────────────────────────────────────────────────────
mkdir -p "$(dirname "${OUT_JSON}")"
cat > "${OUT_JSON}" <<EOF
{
  "benchmark": "Hermes vanilla vs Turbo nos mesmos cenários",
  "date": "${DATE_UTC}",
  "commit": "${COMMIT_SHA}",
  "ref": "${REF_NAME}",
  "smoke": ${SMOKE},
  "provisioned_vanilla": ${SETUP_VANILLA},
  "scenarios": [
    $(IFS=,; echo "${RESULTS_JSON[*]}")
  ]
}
EOF
echo ""
echo "Resultados JSON salvos em: ${OUT_JSON}"

if [[ "$JSON_OUT" == "true" ]]; then
    cat "${OUT_JSON}"
fi

# ── Escreve BENCHMARKS.md ────────────────────────────────────────────────────
echo ""
echo "→ Escrevendo ${OUT_MD}..."

{
    echo "# Benchmarks: Hermes vanilla vs Turbo"
    echo ""
    echo "Gerado em: ${DATE_UTC}"
    echo ""
    echo "## Resumo"
    echo ""
    echo "| Cenário | Status Vanilla | Status Turbo | Tempo Vanilla (s) | Tempo Turbo (s) | Speedup | Erros Vanilla | Erros Turbo |"
    echo "|---------|---------------|-------------|-------------------|-----------------|---------|--------------|-------------|"

    for result in "${RESULTS_JSON[@]}"; do
        cenario="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['cenario'])")"
        v_status="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['vanilla']['status'])")"
        t_status="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['turbo']['status'])")"
        v_time="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"vanilla\"][\"time_sec\"]:.2f}')")"
        t_time="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"turbo\"][\"time_sec\"]:.2f}')")"
        speedup="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('speedup_x'); print(f'{s:.2f}x' if s else 'N/A')")"
        v_err="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['vanilla']['errors'])")"
        t_err="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['turbo']['errors'])")"
        echo "| ${cenario} | ${v_status} | ${t_status} | ${v_time} | ${t_time} | ${speedup} | ${v_err} | ${t_err} |"
    done

    echo ""
    echo "## Detalhamento"
    echo ""

    for result in "${RESULTS_JSON[@]}"; do
        cenario="$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['cenario'])")"
        echo "### ${cenario}"
        echo ""
        echo '```json'
        echo "$result" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))"
        echo '```'
        echo ""
    done

    echo "## Notas"
    echo ""
    echo "- **Custo estimado**: calculado como (\$3/M tokens input + \$15/M tokens output), assumindo 75% input / 25% output."
    echo "- **Tokens estimados**: proxy baseado em contagem de palavras × 1.5."
    echo "- **Erros**: contagem de padrões de erro/confabulação na saída do agente."
    echo "- **Modo smoke**: executa com max-turns=3 para verificação rápida em CI."
    echo ""
    echo "---
    echo "*Benchmark gerado por scripts/benchmark-compare.sh — Issue #177*"
} > "${OUT_MD}"

echo "BENCHMARKS.md atualizado."
echo ""
echo "╔════════════════════════════════════════╗"
echo "║   Benchmark concluído!                 ║"
echo "║   Resultados: ${OUT_JSON}  ║"
echo "║   Relatório:  ${OUT_MD} ║"
echo "╚════════════════════════════════════════╝"
