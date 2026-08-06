---
name: hermes-turbo-agent
description: Use when improving Hermes Agent speed.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, performance, profiling, benchmarking, orjson, msgspec, uvloop, turbo]
    related_skills: [hermes-agent-skill-authoring, systematic-debugging]
---

# Hermes Turbo Agent

## Objetivo

Aplicar recomendações de desempenho ao Hermes Agent sem criar um fork permanente. Esta skill transforma o conceito Hermes Turbo em uma rotina de auditoria, benchmark e melhoria estrutural do próprio Hermes.

Ao ser instalada e acionada em uma sessão, deve primeiro mapear o Hermes ativo, medir os gargalos e aplicar apenas mudanças autorizadas no projeto correto. Não alterar outro repositório, perfil, configuração ou ambiente sem escopo explícito.

## Regra de segurança operacional

A skill pode preparar e aplicar melhorias, mas não deve apagar repositórios, forçar push, alterar a branch principal, publicar código ou abrir PR sem instrução explícita para o alvo. Mudanças devem ser pequenas, reversíveis e acompanhadas de testes e benchmark.

## Otimizações principais

### 1. Serialização rápida com `orjson`

Avaliar `orjson` nos caminhos quentes de `json.loads` e `json.dumps`, especialmente mensagens, schemas e tool calls. Encapsular em uma interface interna, preservar fallback para a biblioteca padrão e testar bytes versus strings, datas, exceções e payloads reais.

### 2. Parsing tipado com `msgspec`

Avaliar `msgspec` para decodificar mensagens e tool calls estáveis. Usar structs somente com contratos definidos. Medir latência, alocações, payloads inválidos e compatibilidade antes de substituir parsing flexível.

### 3. Event loop opcional com `uvloop`

Avaliar `uvloop` no CLI e gateway em plataformas compatíveis. Detectar capacidade em runtime e manter `asyncio` como fallback. Medir cold start, warm start, latência e estabilidade por plataforma; não torná-lo dependência obrigatória.

### 4. Persistência em lote

Acumular eventos de uma rodada e gravar uma transação SQLite por lote, preservando ordenação, alternância de papéis, recuperação após falha, concorrência e consistência.

### 5. Startup e descoberta de ferramentas

Separar descoberta de metadados da importação efetiva. Cachear schemas e metadados com versão baseada em Hermes, configuração, plugins, skills e ferramentas. Invalidar corretamente e remover preflight local que não seja necessário.

### 6. Cache de metadados externos

Usar TTL, schema versionado, escrita atômica e recuperação para o caminho original quando houver corrupção ou indisponibilidade. Nunca armazenar segredos ou dados sensíveis.

### 7. Paralelismo seguro

Paralelizar somente operações comprovadamente independentes. Manter resultados determinísticos, limitar concorrência, aplicar timeout/cancelamento e preservar a semântica do caminho sequencial. Não paralelizar efeitos colaterais ou operações dependentes de estado.

## Fluxo automático de auditoria

Quando acionada para melhorar velocidade:

1. Mapear o projeto e o Hermes ativo antes de editar.
2. Identificar o repositório, branch e estado de trabalho; não descartar mudanças existentes.
3. Medir baseline de cold start, warm start, tool discovery, persistência, parsing e memória.
4. Localizar o gargalo dominante com evidência.
5. Propor ou executar uma única mudança estrutural pequena por ciclo, dentro do escopo autorizado.
6. Implementar teste de regressão, fallback e caminho de rollback.
7. Executar benchmark antes/depois no mesmo ambiente.
8. Rejeitar mudanças com regressão funcional, de segurança, compatibilidade, prompt caching ou alternância de mensagens.
9. Produzir relatório com métricas, diff, testes e decisão.

## Invariantes do Hermes

- O system prompt e o prefixo de prompt caching devem permanecer estáveis durante uma conversa.
- Nunca inserir mensagens sintéticas que quebrem a alternância estrita de papéis.
- Fallback Python e `asyncio` devem continuar funcionando quando extras opcionais não estiverem instalados.
- Configurações comportamentais pertencem ao `config.yaml`; segredos pertencem ao `.env`.
- Nenhuma telemetria externa deve ser adicionada sem opt-in explícito.
- Benchmarks sintéticos não substituem testes E2E no caminho real.

## Ordem de implementação

1. Escrita de sessões em lote e testes de consistência.
2. Redução de trabalho no startup e remoção de preflight morto.
3. Cache versionado de descoberta de ferramentas e metadados.
4. Paralelismo seguro de operações independentes.
5. Interface de parsing com `orjson` e `msgspec`, mantendo fallback.
6. `uvloop` opcional após medir por plataforma.
7. Extensão Rust opcional somente depois de estabilizar os contratos Python.
8. Dashboard e score como observabilidade, nunca como substitutos de benchmark.

## Critérios de aceitação

- Benchmark reproduzível antes/depois no mesmo caminho.
- Testes unitários e E2E reais, inclusive com Hermes Home temporário.
- `orjson`, `msgspec` e `uvloop` opcionais, com fallback verificado.
- Compatibilidade preservada com configuração, plugins, skills e providers.
- Nenhum segredo ou telemetria não autorizada.
- Prompt caching, alternância de papéis e segurança preservados.
- Diff pequeno, revisável e com rollback simples.

## Controle de versão

Quando o usuário pedir publicação explícita: criar branch de trabalho, executar testes e benchmarks, fazer commit descritivo, fazer push da branch e abrir PR contra a branch alvo. Não fazer force push nem apagar a branch principal. Se o pedido disser simultaneamente “push na main” e “abrir PR”, pedir confirmação do fluxo porque são operações diferentes.

## Não copiar do fork

Não copiar branding, mudança automática de `HERMES_HOME`, dependências nativas obrigatórias, rotinas de atualização sem aprovação, números de benchmark não reproduzidos ou alegações de “100x” fora do caminho especificamente medido.
