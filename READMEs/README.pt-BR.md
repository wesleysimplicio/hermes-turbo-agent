# Hermes Turbo Agent

Skill executável de instalação e otimização de desempenho para o Hermes Agent. Ela não é um fork executável: mede gargalos e aplica mudanças estruturais pequenas, testáveis e reversíveis.

## Recomendações

- `orjson`: JSON mais rápido com fallback para `json`.
- `msgspec`: parsing tipado de mensagens e tool calls estáveis.
- `uvloop`: event loop opcional com fallback para `asyncio`.
- Escrita de sessões em lote para reduzir I/O e transações SQLite.
- Startup e descoberta de ferramentas mais rápidos com cache versionado e invalidação correta.
- Cache de metadados externos com TTL e escrita atômica, sem segredos.
- Paralelismo apenas para operações independentes, com ordem determinística, limites, timeout e cancelamento.

## Benefícios esperados

Benchmarks anteriores do fork observaram aproximadamente 4–6x em JSON grande, 3–4x no caminho de mensagens, 19–38x no caminho medido de persistência e 2–4x no startup. São referências, não garantias; é preciso reproduzir as medições no Hermes real.

Prompt caching, compatibilidade, fallbacks Python/`asyncio`, segurança e rollback devem ser preservados. Consulte `README.md` e `SKILL.md`.
