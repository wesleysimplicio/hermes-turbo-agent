from prometheus_client import Gauge

# Context metrics
CONTEXT_HITS = Gauge('context_hits', 'Cache hits do contexto')
CONTEXT_MISSES = Gauge('context_misses', 'Cache misses do contexto')
CONTEXT_SIZE = Gauge('context_size_bytes', 'Tamanho total do contexto em bytes')
CONTEXT_TTL = Gauge('context_ttl_seconds', 'TTL configurado para o cache')