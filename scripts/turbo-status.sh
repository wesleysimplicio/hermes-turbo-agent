#!/usr/bin/env bash
# scripts/turbo-status.sh — Dashboard de Saúde do Ecossistema Simplicio
#
# Mostra status em tempo real de todos os componentes do ecossistema:
#   - Repositórios core (git status, branch, dirty/clean, ahead/behind)
#   - Serviços em execução (processos conhecidos)
#   - Ferramentas CLI disponíveis no PATH
#   - Ambiente (Python, Node, Rust)
#
# Uso:
#   bash scripts/turbo-status.sh              # visão completa
#   bash scripts/turbo-status.sh --quick      # apenas resumo
#   bash scripts/turbo-status.sh --json       # saída JSON (para tooling)
#   bash scripts/turbo-status.sh --watch      # modo live-reload (a cada 5s)
#
# Exit codes:
#   0 = todos os componentes saudáveis
#   1 = pelo menos um componente com warning
#   2 = pelo menos um componente com erro

set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Ícones (fallback para ASCII quando sem suporte unicode)
OK_ICON="✓"
WARN_ICON="⚠"
ERR_ICON="✗"
INFO_ICON="●"

# ── Configuração ─────────────────────────────────────────────────────────────
REPO_HOME="$HOME/Projetos/ai"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODE="normal"  # normal | quick | json | watch
EXIT_CODE=0

# ── Parsing de argumentos ────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --quick)  MODE="quick"  ;;
    --json)   MODE="json"   ;;
    --watch)  MODE="watch"  ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

# ── Utilitários ──────────────────────────────────────────────────────────────

# Cores para o modo normal
color_ok()    { echo -e "${GREEN}${OK_ICON}${NC}"; }
color_warn()  { echo -e "${YELLOW}${WARN_ICON}${NC}"; }
color_err()   { echo -e "${RED}${ERR_ICON}${NC}"; }
color_info()  { echo -e "${CYAN}${INFO_ICON}${NC}"; }

# Cores para JSON (não escapadas) — valores inline em emit_json

# Acumulador de resultado geral
_overall="ok"

_accum() {
  local level="$1"
  if [ "$level" = "error" ]; then
    _overall="error"
    EXIT_CODE=2
  elif [ "$level" = "warning" ] && [ "$_overall" != "error" ]; then
    _overall="warning"
    [ "$EXIT_CODE" -lt 2 ] && EXIT_CODE=1
  fi
}

# ── Seção: Header ────────────────────────────────────────────────────────────

print_header() {
  if [ "$MODE" = "json" ]; then return; fi
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║   ${CYAN}🏥 Turbo Status — Simplicio Ecosystem Dashboard${NC}     ${BOLD}║${NC}"
  echo -e "${BOLD}║   ${DIM}$(date '+%Y-%m-%d %H:%M:%S')${NC}                                   ${BOLD}║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

print_footer() {
  if [ "$MODE" = "json" ]; then return; fi
  local status_color
  case "$_overall" in
    ok)      status_color="${GREEN}SAUDÁVEL${NC}" ;;
    warning) status_color="${YELLOW}ATENÇÃO${NC}" ;;
    error)   status_color="${RED}CRÍTICO${NC}" ;;
  esac
  echo ""
  echo -e "${BOLD}Resumo:${NC} Saúde geral do ecossistema: ${status_color}"
  echo ""
}

# ── Seção: Repositórios Core ────────────────────────────────────────────────

# Lista de repositórios core do ecossistema
CORE_REPOS=(
  "simplicio-runtime"
  "simplicio-mapper"
  "simplicio-dev-cli"
  "simplicio-loop"
  "simplicio-loop-marketing"
  "simplicio-agent"
  "simplicio-prompt"
  "simplicio-sprint"
  "hermes-turbo-agent"
)

check_repo() {
  local repo="$1"
  local path="$REPO_HOME/$repo"
  local name="$repo"

  if [ ! -d "$path" ]; then
    if [ "$MODE" = "json" ]; then
      echo "    {\"name\":\"$name\",\"status\":\"error\",\"detail\":\"not_found\",\"branch\":null,\"dirty\":null}"
    else
      echo -e "  $(color_err) ${BOLD}$name${NC}  — diretório não encontrado em $path"
    fi
    _accum "error"
    return
  fi

  if [ ! -d "$path/.git" ]; then
    if [ "$MODE" = "json" ]; then
      echo "    {\"name\":\"$name\",\"status\":\"warning\",\"detail\":\"no_git_repo\",\"branch\":null,\"dirty\":null}"
    else
      echo -e "  $(color_warn) ${BOLD}$name${NC}  — não é um repositório git"
    fi
    _accum "warning"
    return
  fi

  local branch dirty ahead behind
  branch="$(cd "$path" && git branch --show-current 2>/dev/null || echo 'detached')"
  dirty="$(cd "$path" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

  ahead=0; behind=0
  if (cd "$path" && git rev-parse "@{upstream}" 2>/dev/null) >/dev/null; then
    # shellcheck disable=SC1083
    eval "$(cd "$path" && git rev-list --left-right --count HEAD...@{upstream} 2>/dev/null | awk '{print "ahead="$1"; behind="$2}')" 2>/dev/null || true
  fi

  local status="ok"
  local detail="clean"
  if [ "$dirty" -gt 0 ]; then
    status="warning"
    detail="${dirty} file(s) modified"
  fi
  if [ "$ahead" -gt 0 ] || [ "$behind" -gt 0 ]; then
    [ "$status" = "ok" ] && status="warning"
    detail="$detail, ±${ahead}/⇣${behind}"
  fi

  if [ "$MODE" = "json" ]; then
    echo "    {\"name\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\",\"branch\":\"$branch\",\"dirty\":$dirty,\"ahead\":$ahead,\"behind\":$behind}"
  else
    local icon
    case "$status" in
      ok)      icon="$(color_ok)"  ;;
      warning) icon="$(color_warn)" ;;
      error)   icon="$(color_err)"  ;;
    esac
    echo -e "  $icon ${BOLD}$name${NC}  [${CYAN}$branch${NC}]  ${DIM}$detail${NC}"
  fi
  _accum "$status"
}

section_repos() {
  if [ "$MODE" = "json" ]; then return; fi
  echo -e "${BOLD}📦 Repositórios Core${NC}"
  echo -e "${DIM}──────────────────────────────────────────────${NC}"
  for repo in "${CORE_REPOS[@]}"; do
    check_repo "$repo"
  done
  echo ""
}

# ── Seção: Ferramentas CLI ───────────────────────────────────────────────────

CLI_TOOLS=(
  "python3:python3"
  "node:node"
  "npm:npm"
  "uv:uv"
  "git:git"
  "rustc:rustc"
  "cargo:cargo"
  "simplicio:simplicio"
  "hermes:hermes"
  "docker:docker"
  "modal:modal"
  "rtk:rtk"
)

check_tool() {
  local entry="$1"
  local tool_name="${entry%%:*}"
  local tool_cmd="${entry##*:}"

  if command -v "$tool_cmd" &>/dev/null; then
    local version
    version="$("$tool_cmd" --version 2>/dev/null | head -1 || echo "disponível")"
    if [ "$MODE" = "json" ]; then
      echo "    {\"name\":\"$tool_name\",\"status\":\"ok\",\"version\":\"$version\"}"
    else
      echo -e "  $(color_ok) ${BOLD}$tool_name${NC}  ${DIM}$version${NC}"
    fi
  else
    if [ "$MODE" = "json" ]; then
      echo "    {\"name\":\"$tool_name\",\"status\":\"warning\",\"version\":null}"
    else
      echo -e "  $(color_warn) ${BOLD}$tool_name${NC}  ${DIM}não encontrado no PATH${NC}"
    fi
    _accum "warning"
  fi
}

section_tools() {
  if [ "$MODE" = "json" ]; then
    # Emite como JSON array
    return
  fi
  echo -e "${BOLD}🔧 Ferramentas CLI${NC}"
  echo -e "${DIM}──────────────────────────────────────────────${NC}"
  for tool in "${CLI_TOOLS[@]}"; do
    check_tool "$tool"
  done
  echo ""
}

# ── Seção: Serviços / Processos ──────────────────────────────────────────────

check_service() {
  local name="$1"
  local pattern="$2"

  if pgrep -f "$pattern" &>/dev/null; then
    if [ "$MODE" = "json" ]; then
      echo "    {\"name\":\"$name\",\"status\":\"ok\",\"running\":true}"
    else
      echo -e "  $(color_ok) ${BOLD}$name${NC}  ${DIM}em execução${NC}"
    fi
  else
    if [ "$MODE" = "json" ]; then
      echo "    {\"name\":\"$name\",\"status\":\"info\",\"running\":false}"
    else
      echo -e "  $(color_info) ${BOLD}$name${NC}  ${DIM}parado${NC}"
    fi
  fi
}

SERVICES=(
  "hermes-agent:hermes.*agent"
  "hermes-gateway:hermes.*gateway"
  "simplicio:simplicio"
  "docker:docker"
)

section_services() {
  if [ "$MODE" = "json" ]; then return; fi
  echo -e "${BOLD}⚙️  Serviços${NC}"
  echo -e "${DIM}──────────────────────────────────────────────${NC}"
  for svc in "${SERVICES[@]}"; do
    local name="${svc%%:*}"
    local pattern="${svc##*:}"
    check_service "$name" "$pattern"
  done
  echo ""
}

# ── Seção: Ambiente ──────────────────────────────────────────────────────────

section_env() {
  if [ "$MODE" = "json" ]; then return; fi
  echo -e "${BOLD}🌐 Ambiente${NC}"
  echo -e "${DIM}──────────────────────────────────────────────${NC}"

  # Python
  if command -v python3 &>/dev/null; then
    local pyver pybin
    pyver="$(python3 --version 2>/dev/null)"
    pybin="$(command -v python3)"
    echo -e "  $(color_ok) Python   ${DIM}$pyver — $pybin${NC}"
  else
    echo -e "  $(color_err) Python   ${DIM}não encontrado${NC}"
    _accum "error"
  fi

  # Node
  if command -v node &>/dev/null; then
    local nodever nodebin
    nodever="$(node --version 2>/dev/null)"
    nodebin="$(command -v node)"
    echo -e "  $(color_ok) Node.js  ${DIM}$nodever — $nodebin${NC}"
  else
    echo -e "  $(color_warn) Node.js  ${DIM}não encontrado${NC}"
    _accum "warning"
  fi

  # Rust
  if command -v rustc &>/dev/null; then
    local rustver
    rustver="$(rustc --version 2>/dev/null)"
    echo -e "  $(color_ok) Rust     ${DIM}$rustver${NC}"
  else
    echo -e "  $(color_warn) Rust     ${DIM}não encontrado${NC}"
    _accum "warning"
  fi

  # Git
  if command -v git &>/dev/null; then
    local gitver
    gitver="$(git --version 2>/dev/null)"
    echo -e "  $(color_ok) Git      ${DIM}$gitver${NC}"
  else
    echo -e "  $(color_err) Git      ${DIM}não encontrado${NC}"
    _accum "error"
  fi

  # Shell / OS
  echo -e "  $(color_info) OS       ${DIM}$(uname -a | cut -d' ' -f1-3)${NC}"
  echo ""
}

# ── Seção: Espaço em Disco ───────────────────────────────────────────────────

section_disk() {
  if [ "$MODE" = "json" ]; then return; fi
  echo -e "${BOLD}💾 Disco${NC}"
  echo -e "${DIM}──────────────────────────────────────────────${NC}"

  local home_usage
  home_usage="$(df -h "$HOME" 2>/dev/null | awk 'NR==2{print $3 " / " $2 " (" $5 " used)"}')"
  echo -e "  $(color_info) Home     ${DIM}$home_usage${NC}"

  local repos_usage
  repos_usage="$(du -sh "$REPO_HOME" 2>/dev/null | awk '{print $1}')"
  echo -e "  $(color_info) Repos    ${DIM}${repos_usage:-?} total${NC}"

  local turbo_size
  turbo_size="$(du -sh "$REPO_ROOT" 2>/dev/null | awk '{print $1}')"
  echo -e "  $(color_info) Turbo    ${DIM}${turbo_size:-?}${NC}"

  # Warn if disk > 85%
  local pct
  pct="$(df "$HOME" 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%')"
  if [ -n "$pct" ] && [ "$pct" -gt 85 ]; then
    echo -e "  $(color_warn) ⚠ Disco com ${pct}% de uso — considere limpar"
    _accum "warning"
  fi
  echo ""
}

# ── Modo JSON ────────────────────────────────────────────────────────────────

emit_json() {
  local first=1
  echo -n '{'
  echo -n '"timestamp":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",'

  # Repos
  echo -n '"repositories":['
  first=1
  for repo in "${CORE_REPOS[@]}"; do
    [ "$first" -eq 1 ] || echo -n ','
    first=0
    check_repo "$repo"
  done
  echo -n '],'

  # Tools
  echo -n '"tools":['
  first=1
  for tool in "${CLI_TOOLS[@]}"; do
    [ "$first" -eq 1 ] || echo -n ','
    first=0
    check_tool "$tool"
  done
  echo -n '],'

  # Services
  echo -n '"services":['
  first=1
  for svc in "${SERVICES[@]}"; do
    [ "$first" -eq 1 ] || echo -n ','
    first=0
    local name="${svc%%:*}"
    local pattern="${svc##*:}"
    check_service "$name" "$pattern"
  done
  echo -n '],'

  echo -n '"overall":"'"$_overall"'"'
  echo -n '}'
  echo ""
}

# ── Modo Quick ────────────────────────────────────────────────────────────────

mode_quick() {
  echo -e "${BOLD}🏥 Turbo Status — Resumo Rápido${NC}"
  echo ""

  local ok=0 warn=0 err=0 total=0
  for repo in "${CORE_REPOS[@]}"; do
    total=$((total + 1))
    local path="$REPO_HOME/$repo"
    if [ ! -d "$path/.git" ]; then
      err=$((err + 1))
      echo -e "  $(color_err) $repo"
      continue
    fi
    local dirty
    dirty="$(cd "$path" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$dirty" -gt 0 ]; then
      warn=$((warn + 1))
      echo -e "  $(color_warn) $repo  (${dirty} dirty)"
    else
      ok=$((ok + 1))
      echo -e "  $(color_ok) $repo"
    fi
  done

  echo ""
  echo -e "${GREEN}✓${NC} $ok ok  ${YELLOW}⚠${NC} $warn warn  ${RED}✗${NC} $err err  │  Total: $total"
  echo ""
}

# ── Modo Watch ────────────────────────────────────────────────────────────────

mode_watch() {
  while true; do
    clear 2>/dev/null || true
    _overall="ok"
    EXIT_CODE=0
    MODE="normal"
    print_header
    section_repos
    section_tools
    section_services
    section_env
    section_disk
    print_footer
    echo -e "${DIM}Atualizando a cada 5s... Ctrl+C para sair${NC}"
    sleep 5
  done
}

# ── Main ──────────────────────────────────────────────────────────────────────

case "$MODE" in
  quick)
    mode_quick
    exit "$EXIT_CODE"
    ;;
  json)
    # Pré-coleta de overall
    for repo in "${CORE_REPOS[@]}"; do
      repo_path="$REPO_HOME/$repo"
      if [ ! -d "$repo_path/.git" ]; then
        _accum "error"
        continue
      fi
      dirty_count="$(cd "$repo_path" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
      [ "$dirty_count" -gt 0 ] && _accum "warning"
    done
    emit_json
    exit "$EXIT_CODE"
    ;;
  watch)
    mode_watch
    ;;
  normal)
    print_header
    section_repos
    section_tools
    section_services
    section_env
    section_disk
    print_footer
    exit "$EXIT_CODE"
    ;;
esac
