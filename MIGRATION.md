# Playbook de Migração — Hermes vanilla → Hermes Turbo + Simplicio

> **Idioma:** Português (BR) — este guia é escrito em português brasileiro
> porque o público-alvo é a comunidade brasileira de desenvolvedores que
> utiliza o Hermes Agent e quer migrar para o Hermes Turbo com Simplicio
> Runtime.

Guia passo a passo para quem usa **Hermes Agent vanilla** (do `NousResearch/hermes-agent`)
e quer migrar para o **Hermes Turbo Agent** (fork otimizado) com o ecossistema
**Simplicio Runtime**.

---

## Índice

1. [O que é Hermes Turbo + Simplicio?](#1-o-que-é-hermes-turbo--simplicio)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Diagnóstico: qual versão você tem hoje?](#3-diagnóstico-qual-versão-você-tem-hoje)
4. [Instalação do Hermes Turbo](#4-instalação-do-hermes-turbo)
5. [Instalação do Simplicio Runtime](#5-instalação-do-simplicio-runtime)
6. [Mapeamento: tools nativas → Simplicio](#6-mapeamento-tools-nativas--simplicio)
7. [Configuração do Discord Bot](#7-configuração-do-discord-bot)
8. [Verificação pós-migração](#8-verificação-pós-migração)
9. [Rollback: voltar ao Hermes vanilla](#9-rollback-voltar-ao-hermes-vanilla)
10. [Troubleshooting](#10-troubleshooting)
11. [Referências](#11-referências)

---

## 1. O que é Hermes Turbo + Simplicio?

| Componente | Descrição |
|---|---|
| **Hermes Turbo Agent** | Fork performático do Hermes Agent com otimizações de cache, streaming, ferramentas e integração com o Simplicio Runtime. |
| **Simplicio Runtime** | Camada de runtime que adiciona tools nativas (edit, web-search, agents delegate, etc.) e um ecossistema de MCPs, skills e memória persistente. |
| **TOTA_HOME** | Diretório base do ecossistema (padrão: `~/.hermes_turbo/`). |

**Benefícios da migração:**
- Até **18.6× mais rápido** em transcripts longos (prompt caching otimizado)
- **33.4× por chunk** em streaming de diagnóstico
- Tools Simplicio integradas (edit estruturado, busca web delegada, sub-agentes)
- Hierarchical cache + warm daemon mode
- Atualização automática via `hermes update --check-main`

---

## 2. Pré-requisitos

### macOS

```bash
# 1. Sistema
macOS 13+ (Ventura ou superior)
Xcode Command Line Tools: xcode-select --install

# 2. Python
python3 --version   # 3.10+
pip3 --version      # 24+

# 3. Rust (para extensões nativas)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version     # 1.80+

# 4. Git
git --version       # 2.40+

# 5. GitHub CLI (opcional, mas recomendado)
brew install gh
gh auth login

# 6. Terminal com suporte a TUI (opcional)
# iTerm2, kitty, ou Terminal.app padrão
```

### Linux

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y python3 python3-pip git curl build-essential
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Fedora
sudo dnf install -y python3 python3-pip git curl gcc gcc-c++
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

### Windows

> Hermes Turbo tem suporte experimental no Windows via WSL2.

```powershell
# 1. Instalar WSL2 (Ubuntu 24.04 LTS recomendado)
wsl --install -d Ubuntu-24.04

# 2. Dentro do WSL, seguir os passos Linux acima
wsl ~
```

---

## 3. Diagnóstico: qual versão você tem hoje?

Antes de migrar, identifique sua instalação atual:

```bash
# Hermes vanilla (via pip)
pip3 show hermes-agent 2>/dev/null | grep Version

# Hermes Turbo (via git clone)
~/Projetos/ai/hermes-turbo-agent/hermes --version 2>/dev/null || \
  echo "Hermes Turbo não encontrado"

# Simplicio Runtime
ls ~/.hermes_turbo/simplicio 2>/dev/null && \
  echo "Simplicio presente" || echo "Simplicio ausente"

# TOTA_HOME configurado?
echo "TOTA_HOME=${TOTA_HOME:-~/.hermes_turbo}"
```

**Cenários comuns:**

| Cenário | Ação |
|---|---|
| Hermes vanilla via pip | `pip uninstall hermes-agent` e siga instalação Turbo |
| Hermes vanilla via git | Clone o fork Turbo e configure |
| Já tem Hermes Turbo | Pule para instalação do Simplicio |
| Já tem Turbo + Simplicio | Você já migrou! Rode `turbo-status.sh` para verificar saúde |

---

## 4. Instalação do Hermes Turbo

### Opção A: Script turbo-setup.sh (recomendado — instala tudo)

```bash
git clone https://github.com/wesleysimplicio/hermes-turbo-agent.git
cd hermes-turbo-agent
bash scripts/turbo-setup.sh
```

O script detecta automaticamente seu SO, instala dependências e configura o
Simplicio Runtime.

### Opção B: Instalação manual

```bash
# 1. Clonar o repositório
git clone https://github.com/wesleysimplicio/hermes-turbo-agent.git
cd hermes-turbo-agent

# 2. (Opcional) Criar virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install -e ".[dev]"

# 4. Verificar instalação
python3 -c "import hermes_constants; print('OK:', hermes_constants.__file__)"
```

### Opção C: Instalação via pip (futuro)

> Nota: O Hermes Turbo ainda não está publicado no PyPI como pacote separado.
> Instale via git clone por enquanto.

---

## 5. Instalação do Simplicio Runtime

O Simplicio Runtime é o ecossistema de tools e MCPs que estende o Hermes Turbo.

### Via turbo-setup.sh (automático)

Se você usou a Opção A acima, o Simplicio já foi instalado. Verifique:

```bash
ls ~/.hermes_turbo/simplicio/
python3 -c "import simplicio; print(simplicio.__version__)"
```

### Instalação manual do Simplicio

```bash
# 1. Clonar o runtime
git clone https://github.com/wesleysimplicio/simplicio-runtime.git ~/.hermes_turbo/simplicio

# 2. Compilar extensões nativas (Rust)
cd ~/.hermes_turbo/simplicio
cargo build --release

# 3. Instalar dependências Python
pip install -e .

# 4. Configurar TOTA_HOME (adicionar ao ~/.zshrc ou ~/.bashrc)
echo 'export TOTA_HOME="$HOME/.hermes_turbo"' >> ~/.zshrc
source ~/.zshrc

# 5. Inicializar estrutura de diretórios
python3 -c "
from pathlib import Path
for d in ['cache', 'memory', 'logs', 'runs', 'checkpoints']:
    (Path.home() / '.hermes_turbo' / d).mkdir(parents=True, exist_ok=True)
print('Simplicio Runtime initialized at ~/.hermes_turbo/')
"
```

---

## 6. Mapeamento: tools nativas → Simplicio

O Hermes Turbo usa as tools do Simplicio Runtime como camada preferencial.
Abaixo o mapeamento completo entre tools nativas do Hermes vanilla e suas
equivalentes no ecossistema Simplicio.

### Tools de Escrita e Edição

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| `write_file(path, content)` | `simplicio.edit(path, content, mode='write')` | Edit Simplicio suporta diff-aware patches, rollback, e validação de sintaxe |
| `patch(path, old_string, new_string)` | `simplicio.edit(path, patch=diff, mode='patch')` | Mesmo conceito, mas com cache de versões anteriores |
| `read_file(path)` | `simplicio.read(path)` | Retorna com highlights de sintaxe e metadados do arquivo |

### Tools de Busca e Pesquisa

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| `web_search(query)` | `simplicio.web-search(query)` | Usa motor de busca configurável (DuckDuckGo, Bing, etc.) com cache de resultados |
| `search_files(pattern, path)` | `simplicio.search(pattern, path)` | Mesma interface, adiciona indexação full-text |
| `grep_content(pattern, path)` | `simplicio.grep(pattern, path)` | Suporte a regex extendido + contexto configurável |

### Tools de Delegação e Subagentes

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| `delegate_task(agent, task)` | `simplicio.agents delegate(agent, task)` | Suporte a múltiplos agentes simultâneos, fila de tasks, relatório consolidado |
| `subagent_create(config)` | `simplicio.agents create(config)` | Templates pré-definidos de subagentes |
| `subagent_run(id, task)` | `simplicio.agents run(id, task)` | Painel de monitoramento de execução |

### Tools de Terminal e Execução

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| `terminal(command)` | `simplicio.exec(command)` | Sandbox com timeouts, logs estruturados, e replay de sessão |
| `process(action, session_id, ...)` | `simplicio.process(action, opts)` | Gerenciamento de processos longos com healthcheck |

### Tools de Conhecimento e Memória

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| `memory_search(query)` | `simplicio.memory search(query)` | Memória com embeddings e RAG |
| `memory_store(key, value)` | `simplicio.memory store(key, value)` | Namespaces de memória por projeto |
| `skill_view(name)` | `simplicio.skills view(name)` | Catálogo centralizado de skills |

### Tools de MCP e Integração

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| (nativa) `mcp_list()` | `simplicio.mcp list` | Compatível com servidores MCP padrão |
| (nativa) `mcp_call(server, tool, args)` | `simplicio.mcp call(server, tool, args)` | Cache de schemas MCP |

### Tools de Configuração e Diagnóstico

| Hermes vanilla | Simplicio | Diferença |
|---|---|---|
| `hermes tools` | `simplicio.tools` | Lista estendida com tools Simplicio |
| `hermes config` | `simplicio.config` | Interface TUI para configuração |
| (nativa) `turbo-status.sh` | `simplicio.dashboard` | Painel de saúde do ecossistema |

### Resumo visual

```
┌──────────────────────────────────────────────────┐
│                  Hermes Turbo                     │
│  ┌────────────────────────────────────────────┐  │
│  │         Simplicio Runtime (preferido)       │  │
│  │  ┌─────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │  edit   │ │web-search│ │agents       │  │  │
│  │  │  exec   │ │ memory   │ │skills       │  │  │
│  │  │  search │ │  mcp     │ │process      │  │  │
│  │  └─────────┘ └──────────┘ └────────────┘  │  │
│  └────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────┐  │
│  │   Hermes vanilla tools (fallback)          │  │
│  │   write_file, web_search, delegate_task    │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 7. Configuração do Discord Bot

O Hermes Turbo suporta gateway Discord para interagir via chat.

```bash
# 1. Criar aplicação em https://discord.com/developers/applications
#    - Bot -> Token (copiar)
#    - Bot -> Privileged Gateway Intents: MESSAGE_CONTENT

# 2. Configurar token
export DISCORD_BOT_TOKEN="seu_token_aqui"

# 3. Ou adicionar ao .env (apenas secrets!)
echo "DISCORD_BOT_TOKEN=seu_token_aqui" >> .env

# 4. Iniciar gateway Discord
python3 -m hermes_cli gateway discord

# 5. Convidar o bot para seu servidor:
#    OAuth2 -> URL Generator -> bot -> Send Messages, Read Message History
#    Use a URL gerada para adicionar ao servidor
```

**Configuração avançada:** Veja `cli-config.yaml.example` para opções de
canais, prefixo de comando e permissões.

---

## 8. Verificação pós-migração

Após a instalação, execute o dashboard de verificação:

```bash
# 1. Script de status do ecossistema
bash scripts/turbo-status.sh

# 2. Verificar tools Simplicio
python3 -c "
from hermes_cli.tools import get_all_tools
tools = get_all_tools()
simplicio_tools = [t for t in tools if 'simplicio' in t.name]
print(f'Simplicio tools carregadas: {len(simplicio_tools)}')
for t in simplicio_tools:
    print(f'  ✓ {t.name}')
"

# 3. Testar tool Simplicio (exemplo)
python3 -c "
result = __import__('simplicio').edit(path='/tmp/test.txt', content='Hello Turbo!', mode='write')
print(f'Edit result: {result}')
"

# 4. Benchmark rápido
python3 scripts/benchmark_startup_perf.py -n 3

# 5. Verificar cache hierárquico (se aplicável)
python3 -c "
import hermes_constants as hc
print(f'TOTA_HOME: {hc.get_hermes_home()}')
print(f'Cache dir: {hc.get_hermes_home() / \"cache\"}')"
```

**Indicadores de sucesso:**

- ✅ `turbo-status.sh` mostra todos os componentes verdes
- ✅ Tools Simplicio aparecem na listagem
- ✅ `simplicio.edit()` escreve arquivos corretamente
- ✅ Benchmark mostra tempos de startup < 500ms

---

## 9. Rollback: voltar ao Hermes vanilla

Se precisar desfazer a migração:

### Via pip (se instalou via pip)

```bash
# 1. Remover Hermes Turbo
pip uninstall hermes-agent -y

# 2. Reinstalar Hermes vanilla
pip install hermes-agent

# 3. Verificar
hermes --version
```

### Via git (se instalou por clone)

```bash
# 1. Salvar configurações Turbo (opcional)
cp -r ~/.hermes_turbo ~/.hermes_turbo.backup.$(date +%Y%m%d)

# 2. Remover o clone Turbo
rm -rf ~/Projetos/ai/hermes-turbo-agent

# 3. Clonar Hermes vanilla
git clone https://github.com/NousResearch/hermes-agent.git

# 4. Instalar
cd hermes-agent
pip install -e .

# 5. Restaurar configurações (cuidado: pode ter incompatibilidades)
# cp -r ~/.hermes_turbo.backup.*/* ~/.hermes_turbo/
```

### Limpeza do Simplicio Runtime

```bash
# 1. Mover configurações Simplicio (backup)
mv ~/.hermes_turbo ~/.hermes_turbo.backup.$(date +%Y%m%d)

# 2. Remover variáveis de ambiente do shell rc
#    Edite ~/.zshrc ou ~/.bashrc e remova:
#    export TOTA_HOME=...
#    source ~/.cargo/env (se não for usado por outras ferramentas)

# 3. Opcional: remover Rust (se instalado apenas para o Simplicio)
# rustup self uninstall
```

---

## 10. Troubleshooting

### Erro: `ModuleNotFoundError: No module named 'simplicio'`

**Causa:** Simplicio Runtime não está instalado ou não está no PYTHONPATH.

**Solução:**
```bash
# Verificar se o diretório existe
ls ~/.hermes_turbo/simplicio/

# Se não existir, instalar manualmente
git clone https://github.com/wesleysimplicio/simplicio-runtime.git \
  ~/.hermes_turbo/simplicio
pip install -e ~/.hermes_turbo/simplicio
```

### Erro: `git am` conflicts durante upstream sync

**Causa:** Conflito entre alterações do fork e upstream durante sync.

**Solução:**
```bash
# Ver sync-state.json para a última sincronização
cat scripts/upstream-sync/sync-state.json

# Reaplicar manualmente o patch conflitante
bash scripts/upstream-sync/reapply.sh <RUN_ID> --dry-run

# Ver docs/upstream-sync/ para guia de resolução
```

### Erro: `gh` CLI não autenticado

**Causa:** GitHub CLI não está logado ou token expirou.

**Solução:**
```bash
gh auth login
# Ou configurar token manualmente:
export GH_TOKEN="seu_token_aqui"
```

### Erro: Rust build falha no Simplicio

**Causa:** Versão do Rust incompatível ou dependências de sistema faltando.

**Solução:**
```bash
# Atualizar Rust
rustup update

# Verificar versão
rustc --version  # Precisa ser 1.80+

# Para macOS: instalar macOS SDK
xcode-select --install
```

### Performance abaixo do esperado

```bash
# 1. Verificar se as extensões nativas estão ativas
python3 -c "
try:
    from agent._hermes_fast import is_available
    print(f'hermes_fast disponível: {is_available()}')
except ImportError:
    print('hermes_fast NÃO disponível — recompile com cargo build --release')
"

# 2. Verificar cache hierárquico
python3 -c "
from hermes_state import HierarchicalStateCache
cache = HierarchicalStateCache()
print(f'Cache ativo: {cache.is_active}')
print(f'Tamanho: {cache.size}')
"

# 3. Rodar diagnóstico completo
bash scripts/turbo-status.sh --verbose
```

### Discord bot não responde

```bash
# 1. Verificar token
echo "DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN:-(não configurado)}"

# 2. Verificar gateway
python3 -m hermes_cli gateway discord --debug

# 3. Verificar logs
tail -f ~/.hermes_turbo/logs/gateway.log
```

---

## 11. Referências

| Documento | Localização |
|---|---|
| Guia de contribuição | `CONTRIBUTING.md` |
| Política de upstream sync | `.upstream-sync-policy.yml` |
| Guia da política de sync | `docs/upstream-sync/policy.md` |
| Playbook de upstream sync | `docs/upstream-sync/playbook.md` |
| Port plan do run_agent.py | `docs/upstream-sync/run-agent-port-plan.md` |
| Reapply playbook de perf | `docs/hermes-100x-fast-reapply-playbook.md` |
| Guia de identidade Turbo | `docs/hermes-turbo-identity-customization.md` |
| Changelog completo | `CHANGELOG.md` |
| Modificações do fork | `MODIFICATIONS.md` |
| Roadmap de performance | `PERFORMANCE_ROADMAP.md` |
| Guia de desenvolvimento | `AGENTS.md` |
| Configuração de exemplo | `cli-config.yaml.example` |

---

*Documento mantido em: `MIGRATION.md`*
*Issue de referência: [#176](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/176)*
*Última atualização: 2026-07-03*
