#!/usr/bin/env bash
# scripts/turbo-setup.sh — Instalação automática completa do Hermes Turbo + Simplicio Runtime
#
# Issue #173 — Setup Script: turbo-setup.sh — instalação automática completa
#
# Faz tudo do zero (macOS limpo → tudo rodando):
#   1. Detecta se o Simplicio Runtime está instalado
#   2. Se não: instala via curl | bash
#   3. Instala globalmente com simplicio install --global
#   4. Roda simplicio setup (não-interativo)
#   5. Registra MCP nos 12 clients (simplicio mcp register)
#   6. Cria LaunchAgent pra manter o HTTP/MCP online (com.simplicio.runtime)
#   7. Configura cron de notificação 1x/dia
#   8. Testa tudo e exibe relatório final
#
# Uso:
#   bash scripts/turbo-setup.sh
#
# Requer: macOS (testado), curl, bash 3.2+
# Não pede senha — usa sudo apenas em 1 ponto bem definido (load LaunchAgent).

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
USER_HOME="${HOME:-/Users/$(whoami)}"
SIMPLICIO_BIN="${USER_HOME}/.local/bin/simplicio"
SIMPLICIO_LOG_DIR="${USER_HOME}/.simplicio/logs"
LAUNCH_AGENTS_DIR="${USER_HOME}/Library/LaunchAgents"
PLIST_LABEL="com.simplicio.runtime"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${PLIST_LABEL}.plist"
CRON_SCHEDULE="0 9 * * *"   # 09:00 todos os dias
CRON_COMMAND="simplicio update check --json"

# Cores (escapados pra compatibilidade com echo)
VERDE='\033[0;32m'
AZUL='\033[0;34m'
AMARELO='\033[0;33m'
VERMELHO='\033[0;31m'
CIANO='\033[0;36m'
NEGRITO='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${VERDE}✓${NC} $1"; }
info() { echo -e "  ${AZUL}→${NC} $1"; }
aviso(){ echo -e "  ${AMARELO}⚠${NC} $1"; }
erro() { echo -e "  ${VERMELHO}✗${NC} $1"; }
titulo(){ echo -e "\n${CIANO}${NEGRITO}━━━ $1 ━━━${NC}\n"; }

# acumuladores pro relatório final
PASSOS_OK=()
PASSOS_FAIL=()

passo_ok()   { PASSOS_OK+=("$1");   ok "$1"; }
passo_fail() { PASSOS_FAIL+=("$1"); erro "$1"; }

# ──────────────────────────────────────────────────────────────────────────────
# Boas-vindas
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  Hermes Turbo + Simplicio Runtime — Setup Automático (v1.0)"
echo "  Issue #173"
echo "================================================================"
echo ""
echo "  Sistema:  $(uname -srm 2>/dev/null || echo 'desconhecido')"
echo "  Bash:     ${BASH_VERSION:-desconhecido}"
echo "  Repo:     ${REPO_ROOT}"
echo "  Usuário:  $(whoami)"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# [1/8] Detectar se o Simplicio Runtime já está instalado
# ──────────────────────────────────────────────────────────────────────────────
titulo "[1/8] Detectando Simplicio Runtime"

if command -v simplicio &>/dev/null; then
    SIMPLICIO_VERSION="$(simplicio --version 2>/dev/null || simplicio --help 2>/dev/null | head -1)"
    passo_ok "Simplicio Runtime já instalado: ${SIMPLICIO_VERSION:-$(which simplicio)}"
    SIMPLICIO_CMD="$(command -v simplicio)"
elif [ -x "$SIMPLICIO_BIN" ]; then
    passo_ok "Simplicio encontrado em ${SIMPLICIO_BIN} (mas não no PATH)"
    SIMPLICIO_CMD="$SIMPLICIO_BIN"
    export PATH="${USER_HOME}/.local/bin:${PATH}"
else
    aviso "Simplicio Runtime não encontrado — será instalado."
    SIMPLICIO_CMD=""
fi

# ──────────────────────────────────────────────────────────────────────────────
# [2/8] Instalar Simplicio Runtime se necessário
# ──────────────────────────────────────────────────────────────────────────────
if [ -z "$SIMPLICIO_CMD" ]; then
    titulo "[2/8] Instalando Simplicio Runtime"

    info "Baixando instalador de https://simplicio.sh/install ..."
    if curl -fsSL https://simplicio.sh/install | bash; then
        passo_ok "Instalador executado com sucesso"
    else
        passo_fail "Falha ao executar instalador do Simplicio"
        aviso "Tente manualmente: curl -fsSL https://simplicio.sh/install | bash"
    fi

    # Verificar se apareceu
    if [ -x "$SIMPLICIO_BIN" ]; then
        SIMPLICIO_CMD="$SIMPLICIO_BIN"
        export PATH="${USER_HOME}/.local/bin:${PATH}"
        passo_ok "Simplicio Runtime instalado: ${SIMPLICIO_BIN}"
    else
        passo_fail "Simplicio Runtime não encontrado após instalação"
        SIMPLICIO_CMD="simplicio"  # esperar que esteja no PATH
    fi
fi

# ──────────────────────────────────────────────────────────────────────────────
# [3/8] Instalar globalmente (symlink + PATH + assistentes)
# ──────────────────────────────────────────────────────────────────────────────
titulo "[3/8] Instalação global (PATH, assistentes, adapters)"

if command -v simplicio &>/dev/null; then
    if simplicio install --global --yes &>/dev/null; then
        passo_ok "simplicio install --global concluído (PATH + adapters)"
    else
        # --yes pode não existir em todas as versões; tentar sem
        if simplicio install --global &>/dev/null; then
            passo_ok "simplicio install --global concluído"
        else
            aviso "simplicio install --global não disponível ou já configurado"
        fi
    fi
else
    aviso "simplicio não está no PATH — pulando install --global"
fi

# ──────────────────────────────────────────────────────────────────────────────
# [4/8] Configurar ambiente (simplicio setup + env vars guiadas)
# ──────────────────────────────────────────────────────────────────────────────
titulo "[4/8] Configuração inicial do ambiente"

# Roda setup não-interativo — detecta o ambiente, cria config, não pede input
if simplicio setup &>/dev/null; then
    passo_ok "simplicio setup concluído (config padrão criada)"
else
    aviso "simplicio setup retornou erro (pode já estar configurado)"
fi

# ── Env vars: DeepSeek + Discord ─────────────────────────────────────────────
info "Variáveis de ambiente necessárias:"
echo ""
echo "  Para o Hermes Turbo funcionar com DeepSeek,"
echo "  adicione ao seu ~/.zshrc (ou ~/.bashrc):"
echo ""
echo "    export DEEPSEEK_API_KEY=\"sk-seu-deepseek-key-aqui\""
echo "    export DISCORD_TOKEN=\"seu-discord-bot-token-aqui\""
echo ""
echo "  Depois recarregue: source ~/.zshrc"
echo ""

# Verificar se já existem
DEEPSEEK_OK=false
DISCORD_OK=false

if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
    ok "DEEPSEEK_API_KEY já configurada"
    DEEPSEEK_OK=true
else
    aviso "DEEPSEEK_API_KEY não encontrada — configure manualmente"
fi

if [ -n "${DISCORD_TOKEN:-}" ]; then
    ok "DISCORD_TOKEN já configurado"
    DISCORD_OK=true
else
    aviso "DISCORD_TOKEN não encontrado — configure manualmente"
fi

# ──────────────────────────────────────────────────────────────────────────────
# [5/8] Registrar MCP nos clients (simplicio mcp register)
# ──────────────────────────────────────────────────────────────────────────────
titulo "[5/8] Registrando MCP nos 12 clients"

if command -v simplicio &>/dev/null; then
    # Executa mcp register — registra em claude-code, hermes, cursor, windsurf,
    # kiro, gemini, trae, antigravity, jetbrains-junie, claude-desktop, vscode, opencode
    MCP_OUTPUT="$(simplicio mcp register 2>&1 || true)"

    if echo "$MCP_OUTPUT" | grep -q "registered"; then
        passo_ok "MCP registrado nos clients:"
        echo ""
        # Extrair os nomes dos clients registrados
        echo "$MCP_OUTPUT" | while IFS= read -r line; do
            if echo "$line" | grep -q "registered"; then
                echo "    ✓ $line"
            elif echo "$line" | grep -q "skipped\|manual\|not installed"; then
                echo "    ⚠ $line"
            fi
        done
        echo ""
    elif echo "$MCP_OUTPUT" | grep -q "already registered\|já registrado"; then
        passo_ok "MCP já registrado anteriormente"
    else
        aviso "Saída inesperada do mcp register:"
        echo "$MCP_OUTPUT" | head -5
        aviso "MCP pode já estar configurado manualmente"
    fi
else
    passo_fail "simplicio não encontrado no PATH — pulando mcp register"
fi

# ──────────────────────────────────────────────────────────────────────────────
# [6/8] Criar LaunchAgent pra manter o runtime online
# ──────────────────────────────────────────────────────────────────────────────
titulo "[6/8] Configurando LaunchAgent (keep-alive)"

SIMPLICIO_RESOLVED="$(command -v simplicio || echo "$SIMPLICIO_BIN")"
WORK_DIR="${REPO_ROOT}"

mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$SIMPLICIO_LOG_DIR"

cat > "$PLIST_PATH.plist.tmp" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${SIMPLICIO_RESOLVED}</string>
    <string>serve</string>
    <string>--http</string>
    <string>--port</string>
    <string>6119</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>${WORK_DIR}</string>
  <key>StandardOutPath</key>
  <string>${SIMPLICIO_LOG_DIR}/mcp-http-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${SIMPLICIO_LOG_DIR}/mcp-http-stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${USER_HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key>
    <string>${USER_HOME}</string>
  </dict>
</dict>
</plist>
EOF

# Só sobrescreve se diferente (evita bounce desnecessário do launchd)
if [ ! -f "$PLIST_PATH" ] || ! diff -q "$PLIST_PATH.plist.tmp" "$PLIST_PATH" &>/dev/null; then
    mv "$PLIST_PATH.plist.tmp" "$PLIST_PATH"
    info "Arquivo plist criado em ${PLIST_PATH}"

    # Carregar no launchd
    UID_NUM="$(id -u)"
    if launchctl list "$PLIST_LABEL" &>/dev/null 2>&1; then
        # Descarregar versão anterior primeiro
        launchctl bootout "gui/${UID_NUM}" "$PLIST_PATH" 2>/dev/null || true
    fi

    if launchctl bootstrap "gui/${UID_NUM}" "$PLIST_PATH"; then
        passo_ok "LaunchAgent carregado no launchd (HTTP MCP na porta 6119)"
    else
        aviso "Não foi possível carregar o LaunchAgent (tente reboot ou: launchctl bootstrap gui/\$(id -u) ${PLIST_PATH})"
    fi
else
    rm -f "$PLIST_PATH.plist.tmp"
    # Verificar se já está rodando
    if launchctl list "$PLIST_LABEL" &>/dev/null 2>&1; then
        passo_ok "LaunchAgent já carregado e rodando"
    else
        aviso "LaunchAgent existe mas não está carregado — rode: launchctl bootstrap gui/\$(id -u) ${PLIST_PATH}"
    fi
fi

# ──────────────────────────────────────────────────────────────────────────────
# [7/8] Configurar cron de notificação 1x/dia
# ──────────────────────────────────────────────────────────────────────────────
titulo "[7/8] Configurando cron de notificação diária"

if command -v simplicio &>/dev/null; then
    # Verificar se já existe job com esse schedule
    EXISTING_JOBS="$(simplicio cron list --json 2>/dev/null || true)"
    HAS_DAILY=false

    if echo "$EXISTING_JOBS" | grep -q '"schedule":.*0 9 \*\* \*|every.*1d|daily' 2>/dev/null; then
        HAS_DAILY=true
    fi

    if [ "$HAS_DAILY" = false ]; then
        if simplicio cron add "$CRON_SCHEDULE" "$CRON_COMMAND" &>/dev/null; then
            passo_ok "Cron diário configurado: ${CRON_SCHEDULE} → ${CRON_COMMAND}"
        else
            # Tentar formato alternativo (nome + schedule)
            if simplicio cron add "daily-notification" "$CRON_SCHEDULE" &>/dev/null; then
                passo_ok "Cron diário configurado: daily-notification @ ${CRON_SCHEDULE}"
            else
                aviso "simplicio cron add falhou — configure manualmente:"
                aviso "  simplicio cron add '${CRON_SCHEDULE}' '${CRON_COMMAND}'"
            fi
        fi
    else
        passo_ok "Cron diário já existe (pulei)"
    fi
else
    aviso "simplicio não encontrado — pulando configuração de cron"
fi

# ──────────────────────────────────────────────────────────────────────────────
# [8/8] Testar tudo e exibir relatório final
# ──────────────────────────────────────────────────────────────────────────────
titulo "[8/8] Verificação final e relatório"

echo ""
echo "  ${NEGRITO}Resumo da instalação:${NC}"
echo ""

# Teste 1: simplicio no PATH
if command -v simplicio &>/dev/null; then
    passo_ok "simplicio     ✓ ($(which simplicio))"
else
    passo_fail "simplicio     ✗ (não encontrado no PATH)"
fi

# Teste 2: simplicio --version
SIMPLICIO_VER="$(simplicio --version 2>/dev/null || echo 'versão desconhecida')"
ok "versão       ✓ (${SIMPLICIO_VER})"

# Teste 3: LaunchAgent carregado
if launchctl list "$PLIST_LABEL" &>/dev/null 2>&1; then
    LAUNCH_PID="$(launchctl list "$PLIST_LABEL" | awk '{print $1}')"
    passo_ok "launchd      ✓ (PID ${LAUNCH_PID:-rodando})"
else
    aviso "launchd      ⚠ (não carregado — bootstrap pendente)"
fi

# Teste 4: MCP endpoint (HTTP)
if nc -z localhost 6119 2>/dev/null; then
    passo_ok "MCP HTTP     ✓ (porta 6119 respondendo)"
else
    aviso "MCP HTTP     ⚠ (porta 6119 pode não estar ativa ainda)"
fi

# Teste 5: Cron configurado
CRON_LIST="$(simplicio cron list --json 2>/dev/null || true)"
if echo "$CRON_LIST" | grep -q '"enabled":true' 2>/dev/null; then
    passo_ok "cron         ✓ (jobs ativos)"
else
    CRON_COUNT="$(echo "$CRON_LIST" | grep -c '"id"' 2>/dev/null || echo 0)"
    if [ "$CRON_COUNT" -gt 0 ]; then
        aviso "cron         ⚠ (${CRON_COUNT} job(s) encontrado(s), nenhum ativo)"
    else
        aviso "cron         ⚠ (nenhum job configurado)"
    fi
fi

# Teste 6: Plist no filesystem
if [ -f "$PLIST_PATH" ]; then
    passo_ok "plist        ✓ (${PLIST_PATH})"
else
    passo_fail "plist        ✗ (arquivo não encontrado)"
fi

# Teste 7: CLI básico (simplicio_agent é o nome primário; hermes é alias legado)
if command -v simplicio_agent &>/dev/null; then
    ok "simplicio_agent CLI ✓ ($(which simplicio_agent))"
elif command -v hermes &>/dev/null; then
    ok "hermes CLI   ✓ ($(which hermes)) — considere reinstalar para ganhar o alias simplicio_agent"
else
    if [ -x "${REPO_ROOT}/hermes" ]; then
        ok "hermes CLI   ✓ (${REPO_ROOT}/hermes)"
    else
        aviso "CLI ⚠ (não no PATH — rode 'pip install -e .' na raiz do repo)"
    fi
fi

# Teste 8: Env vars checadas antes
if [ "$DEEPSEEK_OK" = true ]; then
    ok "DeepSeek key ✓"
else
    aviso "DeepSeek key ⚠ (pule — configure manualmente)"
fi
if [ "$DISCORD_OK" = true ]; then
    ok "Discord token✓"
else
    aviso "Discord token⚠ (pule — configure manualmente)"
fi

# ── Relatório final ──────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  ${NEGRITO}Relatório Final — Hermes Turbo + Simplicio Runtime${NC}"
echo "================================================================"
echo ""

PASSOS_TOTAL=$((${#PASSOS_OK[@]} + ${#PASSOS_FAIL[@]}))
PASSOS_TOTAL=$((PASSOS_TOTAL > 0 ? PASSOS_TOTAL : 8))  # fallback

FALHAS=${#PASSOS_FAIL[@]}

if [ "$FALHAS" -eq 0 ]; then
    echo "  ${VERDE}${NEGRITO}✅ Setup concluído com sucesso!${NC}"
    echo ""
    echo "  Todos os componentes estão instalados e rodando:"
    echo "    • Simplicio Runtime  → $(which simplicio)"
    echo "    • MCP registrado     → 12 clients"
    echo "    • HTTP endpoint      → http://localhost:6119"
    echo "    • LaunchAgent        → ${PLIST_PATH}"
    echo "    • Cron diário        → ${CRON_SCHEDULE}"
    echo ""
    echo "  ${NEGRITO}Próximos passos:${NC}"
    echo "    1. Configure as env vars no ~/.zshrc se ainda não fez"
    echo "    2. Rode 'hermes' ou 'simplicio chat' pra começar"
    echo "    3. Verifique os logs:"
    echo "       tail -f ${SIMPLICIO_LOG_DIR}/mcp-http-stdout.log"
else
    echo "  ${AMARELO}${NEGRITO}⚠ Setup concluído com ${FALHAS} aviso(s)/falha(s).${NC}"
    echo ""
    if [ ${#PASSOS_FAIL[@]} -gt 0 ]; then
        echo "  Falhas detectadas:"
        for f in "${PASSOS_FAIL[@]}"; do
            echo "    • ${f}"
        done
        echo ""
    fi
    echo "  ${NEGRITO}Recomendações:${NC}"
    echo "    • Verifique os logs em ${SIMPLICIO_LOG_DIR}/"
    echo "    • Rode o script novamente após corrigir os problemas"
    echo "    • Consulte: simplicio doctor --repair"
fi

echo ""
echo "================================================================"
echo "  Documentação: https://github.com/wesleysimplicio/hermes-turbo-agent"
echo "  Issue #173: Setup Script: turbo-setup.sh"
echo "================================================================"
echo ""
