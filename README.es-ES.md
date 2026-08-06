# Hermes Turbo Agent

Skill de recomendaciones y auditoría de rendimiento para Hermes Agent. No es un fork ejecutable: mide cuellos de botella y aplica cambios estructurales pequeños, comprobables y reversibles.

## Recomendaciones

- `orjson`: serialización JSON más rápida con fallback a `json`.
- `msgspec`: parsing tipado de mensajes y llamadas de herramientas estables.
- `uvloop`: event loop opcional con fallback a `asyncio`.
- Guardar sesiones por lotes para reducir I/O y transacciones SQLite.
- Optimizar el arranque y descubrir herramientas mediante caché versionada e invalidada correctamente.
- Cachear metadatos externos con TTL y escritura atómica, sin secretos.
- Paralelizar solo operaciones independientes, con orden, límites y timeouts.

## Beneficios esperados

Los benchmarks anteriores del fork observaron aproximadamente 4–6x en JSON grande, 3–4x en mensajes, 19–38x en el camino medido de persistencia y 2–4x en arranque. Son referencias, no garantías: hay que reproducirlas en Hermes real.

Se deben conservar prompt caching, compatibilidad, fallbacks Python/`asyncio`, seguridad y rollback. Consulta `README.md` y `SKILL.md`.
