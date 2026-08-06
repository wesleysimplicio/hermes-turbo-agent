# Hermes Turbo Agent

<p align="center">
  <strong>🌍 Languages:</strong><br>
  <a href="README.md">🇬🇧 English</a> |
  <a href="READMEs/README.pt-BR.md">🇧🇷 Português</a> |
  <a href="READMEs/README.es-ES.md">🇪🇸 Español</a> |
  <a href="READMEs/README.fr-FR.md">🇫🇷 Français</a> |
  <a href="READMEs/README.de-DE.md">🇩🇪 Deutsch</a> |
  <a href="READMEs/README.it-IT.md">🇮🇹 Italiano</a> |
  <a href="READMEs/README.ja-JP.md">🇯🇵 日本語</a> |
  <a href="READMEs/README.ko-KR.md">🇰🇷 한국어</a> |
  <a href="READMEs/README.zh-CN.md">🇨🇳 简体中文</a> |
  <a href="READMEs/README.ru-RU.md">🇷🇺 Русский</a> |
  <a href="READMEs/README.pl-PL.md">🇵🇱 Polski</a> |
  <a href="READMEs/README.hi-IN.md">🇮🇳 हिन्दी</a> |
  <a href="READMEs/README.ar-SA.md">🇸🇦 العربية</a> |
  <a href="READMEs/README.he-IL.md">🇮🇱 עברית</a> |
  <a href="READMEs/README.id-ID.md">🇮🇩 Bahasa Indonesia</a> |
  <a href="READMEs/README.ms-MY.md">🇲🇾 Bahasa Melayu</a>
</p>

Skill executável de instalação e aplicação de melhorias de desempenho para o Hermes Agent.

Ao ser instalada e acionada para otimização, a skill identifica o Hermes autorizado, instala acelerações opcionais, aplica mudanças compatíveis, executa testes e compara benchmarks antes/depois. Ela não é um fork executável do Hermes.

## O que esta skill recomenda

### `orjson`

Avaliar `orjson` nos caminhos quentes de serialização e desserialização JSON, como mensagens, schemas e tool calls.

Benefícios esperados:

- menor latência em `json.loads` e `json.dumps`;
- menor custo de CPU em payloads médios e grandes;
- maior throughput no processamento de mensagens;
- possibilidade de reduzir alocações em caminhos frequentes.

O uso deve ser encapsulado e ter fallback para a biblioteca `json` padrão.

### `msgspec`

Avaliar `msgspec` para parsing tipado de mensagens e chamadas de ferramentas com contratos estáveis.

Benefícios esperados:

- parsing mais rápido e previsível;
- menor overhead de validação e conversão;
- menor uso de memória em estruturas tipadas;
- detecção mais clara de payloads inválidos.

Não deve substituir parsing flexível sem testes de compatibilidade com payloads reais.

### `uvloop`

Avaliar `uvloop` como event loop opcional no CLI e no gateway em plataformas compatíveis.

Benefícios esperados:

- melhor escalonamento de tarefas assíncronas;
- menor latência em operações de I/O;
- maior throughput em cenários com muitas tarefas concorrentes;
- melhor responsividade do gateway sob carga.

`asyncio` continua sendo o fallback oficial. O ganho deve ser medido por sistema operacional.

## Outras recomendações

### Persistência em lote

Agrupar os eventos de uma rodada e persistir em uma única transação SQLite.

Benefícios:

- menos operações de I/O;
- menor custo de transação;
- menor latência ao salvar sessões;
- melhor eficiência em conversas com muitas mensagens.

A ordenação, a alternância de papéis e a recuperação após falhas devem permanecer preservadas.

### Startup e descoberta de ferramentas

Separar descoberta de metadados da importação efetiva e cachear schemas de forma versionada.

Benefícios:

- menor cold start;
- menor trabalho repetido ao iniciar o Hermes;
- carregamento mais rápido de ferramentas e plugins;
- menos imports desnecessários.

O cache deve ser invalidado quando mudarem a versão, a configuração, as skills, os plugins ou as ferramentas.

### Cache de metadados externos

Usar cache local com TTL, schema versionado e escrita atômica.

Benefícios:

- menos chamadas de rede;
- resposta mais rápida para catálogos e metadados;
- maior resiliência quando o serviço externo estiver indisponível;
- menor custo de inicialização e consulta.

Caches nunca devem armazenar segredos ou dados sensíveis.

### Paralelismo seguro

Executar em paralelo somente operações comprovadamente independentes.

Benefícios:

- menor tempo total de operações independentes;
- melhor aproveitamento de I/O;
- maior responsividade em fluxos com várias ferramentas;
- menor espera causada por tarefas sequenciais desnecessárias.

A implementação deve manter ordem determinística, limites de concorrência, timeout, cancelamento e semântica equivalente ao caminho sequencial.

## Quanto pode melhorar

Os números abaixo são referências de benchmarks produzidos no antigo fork Hermes Turbo Agent. Eles não são garantia de ganho no Hermes atual e precisam ser reproduzidos no caminho real antes de serem considerados resultados do projeto.

| Caminho medido | Ganho observado no benchmark do fork |
| --- | ---: |
| Serialização JSON em payloads grandes | aproximadamente 4x a 6x |
| Desserialização JSON em payloads grandes | aproximadamente 4x |
| Latência de mensagens médias | aproximadamente 3x |
| Throughput de mensagens médias | aproximadamente 3x a 4x |
| Parsing tipado de tool calls | até aproximadamente 2x–5x, conforme o método |
| Escrita de sessões em lote | aproximadamente 19x–38x no caminho instrumentado |
| Consultas de metadados em cache | aproximadamente 0,007 s por consulta no cenário medido |
| Startup e descoberta de ferramentas | aproximadamente 2x–4x no cenário medido |
| Construção de subagentes com preflight local morto | aproximadamente 9x–10x no caminho específico medido |
| Execução paralela de operações independentes | aproximadamente 4x–5x no cenário medido |

Esses valores dependem de payload, hardware, sistema operacional, versão do Python, modelo, número de ferramentas, carga concorrente e caminho exato medido. Não devem ser convertidos em uma promessa de “100x” para o Hermes inteiro.

## Benefícios gerais esperados

- menor tempo de inicialização;
- respostas mais rápidas em fluxos com muitas ferramentas;
- menor custo de CPU e I/O;
- maior throughput de mensagens;
- menor uso de memória em estruturas tipadas;
- melhor escalabilidade assíncrona;
- menor quantidade de chamadas externas repetidas;
- possibilidade de usar aceleração nativa sem perder portabilidade;
- diagnóstico de regressões com métricas reproduzíveis.

## Como a skill trabalha

1. Mapeia o projeto e o Hermes ativo.
2. Confirma branch, estado de trabalho e escopo autorizado.
3. Mede cold start, warm start, descoberta de ferramentas, persistência, parsing e memória.
4. Identifica o gargalo dominante.
5. Aplica uma mudança pequena por ciclo.
6. Adiciona teste de regressão e fallback.
7. Executa benchmark antes/depois no mesmo ambiente.
8. Rejeita a mudança se houver regressão funcional, de segurança, compatibilidade ou prompt caching.
9. Entrega relatório, métricas, diff e rollback.

## Garantias de compatibilidade

- `orjson`, `msgspec` e `uvloop` são opcionais;
- `json` padrão e `asyncio` continuam disponíveis como fallback;
- o system prompt e o prefixo de prompt caching permanecem estáveis durante a conversa;
- a alternância de papéis das mensagens não é alterada;
- configurações comportamentais ficam no `config.yaml`;
- nenhum segredo é incluído em cache;
- nenhuma telemetria externa é adicionada sem opt-in;
- mudanças publicáveis devem ser pequenas e revisáveis.

## Conclusão

Hermes Turbo Agent é uma estratégia de otimização orientada por evidências. O maior benefício não vem de uma única biblioteca, mas da combinação de menos I/O, menos trabalho no startup, parsing mais eficiente, cache correto e paralelismo seguro.

O objetivo é fazer o Hermes ficar mais rápido sem transformá-lo em um fork incompatível, sem exigir Rust ou dependências nativas e sem sacrificar segurança, portabilidade ou estabilidade do prompt caching.
