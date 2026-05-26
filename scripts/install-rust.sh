#!/usr/bin/env bash
# scripts/install-rust.sh — Compila a extensão Rust (hermes_fast) do Hermes Agent
# Idempotente: pode ser rodado múltiplas vezes sem efeito colateral.
#
# Uso:
#   bash scripts/install-rust.sh
#
# Requer: Python 3.11+, pip (detecta automaticamente o venv ativo)
# Rust é instalado automaticamente via rustup se ausente.

set -e

echo "=== Hermes Agent — Rust extension setup ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# 1. Instalar Rust via rustup se não estiver disponível
# ---------------------------------------------------------------------------
if ! command -v rustc &>/dev/null; then
    echo "[1/4] Instalando Rust via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
    source "$HOME/.cargo/env"
else
    echo "[1/4] Rust já instalado: $(rustc --version)"
fi

# Garantir que cargo está no PATH mesmo em subshells não-interativos
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
fi

# Sanity-check: rustc deve estar disponível agora
if ! command -v rustc &>/dev/null; then
    echo "❌ Rust não encontrado após instalação. Adicione ~/.cargo/bin ao PATH e tente novamente."
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Detectar Python / pip do venv ativo (ou do sistema)
# ---------------------------------------------------------------------------
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    export VIRTUAL_ENV="$REPO_ROOT/.venv"
    PATH="$VIRTUAL_ENV/bin:$PATH"
    PYTHON="$REPO_ROOT/.venv/bin/python"
elif [ -x "$REPO_ROOT/venv/bin/python" ]; then
    export VIRTUAL_ENV="$REPO_ROOT/venv"
    PATH="$VIRTUAL_ENV/bin:$PATH"
    PYTHON="$REPO_ROOT/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
else
    PYTHON="$(command -v python)"
fi

echo "[2/4] Python: $PYTHON ($(${PYTHON} --version 2>&1))"

pip_install() {
    if "$PYTHON" -m pip --version &>/dev/null; then
        "$PYTHON" -m pip install "$@"
    elif command -v uv &>/dev/null; then
        uv pip install --python "$PYTHON" "$@"
    else
        echo "❌ pip não disponível para $PYTHON e uv não encontrado."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# 3. Instalar maturin (build backend para extensões PyO3)
# ---------------------------------------------------------------------------
if ! "$PYTHON" -m maturin --version &>/dev/null 2>&1; then
    echo "[3/4] Instalando maturin..."
    pip_install "maturin>=1.0,<2.0" --quiet
else
    echo "[3/4] maturin já instalado: $("$PYTHON" -m maturin --version 2>&1)"
fi

# ---------------------------------------------------------------------------
# 4. Compilar hermes_fast
# ---------------------------------------------------------------------------
RUST_EXT_DIR="$REPO_ROOT/rust_ext"

if [ ! -d "$RUST_EXT_DIR" ]; then
    echo "❌ Diretório rust_ext/ não encontrado em $REPO_ROOT"
    echo "   Certifique-se de estar rodando a partir do repositório Hermes Agent."
    exit 1
fi

echo "[4/4] Compilando hermes_fast (release, pode levar ~30s na primeira vez)..."
cd "$RUST_EXT_DIR"
"$PYTHON" -m maturin develop --release

echo ""
echo "Verificando instalação..."
PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}" "$PYTHON" -c "
from agent._hermes_fast import HAVE_RUST, estimate_tokens
assert HAVE_RUST, 'HAVE_RUST ainda False após compilação! Verifique os logs acima.'
n = estimate_tokens('hello world test')
print(f'  ✓ HAVE_RUST = {HAVE_RUST}')
print(f'  ✓ estimate_tokens(\"hello world test\") = {n}')
print('  ✓ Extensão Rust OK')
" && echo "" && echo "=== Setup Rust concluído com sucesso ===" \
  || { echo ""; echo "❌ Verificação falhou — o agente continuará usando o fallback Python."; exit 1; }
