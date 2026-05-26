#!/usr/bin/env bash
# scripts/setup.sh — Setup completo do Hermes Agent para novos contribuidores/devs.
#
# Este script complementa o `pip install -e .` instalando as dependências de
# performance (orjson, msgspec, uvloop) e compilando a extensão Rust (hermes_fast).
# O agente funciona sem ambos — mas com eles é significativamente mais rápido.
#
# Uso (a partir da raiz do repositório):
#   pip install -e .
#   bash scripts/setup.sh
#
# Ou, em um único passo:
#   pip install -e ".[fast,dev]" && bash scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "======================================================"
echo "  Hermes Agent — Developer Setup"
echo "======================================================"
echo ""

# ---------------------------------------------------------------------------
# Detectar Python / pip (venv tem prioridade)
# ---------------------------------------------------------------------------
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
elif [ -x "$REPO_ROOT/venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
else
    PYTHON="python"
fi

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

echo "Python: $PYTHON ($("$PYTHON" --version 2>&1))"
echo ""

# ---------------------------------------------------------------------------
# [1/4] Instalar dependências Python base
# ---------------------------------------------------------------------------
echo "[1/4] Instalando dependências Python (pip install -e .)..."
if pip_install -e ".[dev]" --quiet 2>/dev/null; then
    echo "  ✓ Instalado via extras [dev]"
elif [ -f requirements.txt ]; then
    pip_install -r requirements.txt --quiet
    echo "  ✓ Instalado via requirements.txt"
else
    pip_install -e . --quiet
    echo "  ✓ Instalado via pip install -e ."
fi

# ---------------------------------------------------------------------------
# [2/4] Instalar dependências de performance
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Instalando dependências de performance (orjson, msgspec, uvloop)..."
pip_install \
    "orjson>=3.11,<4" \
    "msgspec>=0.21,<0.23" \
    --quiet
PLATFORM="$("$PYTHON" -c 'import sys; print(sys.platform)')"
if [ "$PLATFORM" != "win32" ]; then
    pip_install "uvloop>=0.22,<0.24" --quiet
    echo "  ✓ orjson + msgspec + uvloop instalados"
else
    echo "  ✓ orjson + msgspec instalados (uvloop não suportado no Windows)"
fi

# ---------------------------------------------------------------------------
# [3/4] Compilar extensão Rust
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Compilando extensão Rust (hermes_fast)..."
if bash "$SCRIPT_DIR/install-rust.sh"; then
    RUST_OK=true
else
    echo "  ⚠  Compilação Rust falhou — o agente usará o fallback Python."
    echo "     Isso não impede o uso do Hermes, apenas reduz performance."
    RUST_OK=false
fi

# ---------------------------------------------------------------------------
# [4/4] Verificação final
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Verificação final..."
"$PYTHON" -c "
import sys
print(f'  Python:  {sys.version.split()[0]}')

try:
    import orjson
    print(f'  orjson:  {orjson.__version__} ✓')
except ImportError:
    print('  orjson:  não instalado (fallback stdlib json)')

try:
    import msgspec
    print(f'  msgspec: {msgspec.__version__} ✓')
except ImportError:
    print('  msgspec: não instalado')

try:
    import uvloop
    print(f'  uvloop:  {uvloop.__version__} ✓')
except ImportError:
    print('  uvloop:  não instalado (fallback asyncio)')

try:
    from agent._hermes_fast import HAVE_RUST, estimate_tokens
    if HAVE_RUST:
        n = estimate_tokens('hello world')
        print(f'  Rust ext: ativo ✓ (estimate_tokens=\"{n}\" tokens)')
    else:
        print('  Rust ext: fallback Python (HAVE_RUST=False)')
except ImportError:
    print('  Rust ext: não disponível')
"

echo ""
echo "======================================================"
if [ "$RUST_OK" = true ]; then
    echo "  ✅ Setup completo! Tudo instalado e Rust compilado."
else
    echo "  ✅ Setup completo! (Rust não compilado — fallback Python ativo)"
fi
echo ""
echo "  Para iniciar: hermes"
echo "  Gateway:      hermes gateway run"
echo "  Documentação: https://hermes-agent.nousresearch.com/docs/"
echo "======================================================"
