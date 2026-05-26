# Context Retention System

## Fluxo de Camadas:
1. **Cache RAM** (TTL: 60s)
   - Armazenamento volátil de alta velocidade
   - Invalidado por timeout ou mudança estrutural

2. **Persistência SQLite**
   - Armazenamento durável em disco
   - Indexado por session_id + timestamp

3. **Fallback Volátil**
   - Recuperação emergencial quando as outras camadas falham

## Métricas Monitoradas:
- `context_hits`: Acessos diretos ao cache
- `context_misses`: Fallbacks para camadas mais lentas
- `context_size_bytes`: Carga de memória
- `context_ttl_seconds`: Tempo de vida configurado