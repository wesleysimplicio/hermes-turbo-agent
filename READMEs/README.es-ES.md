# Hermes Turbo Agent

Skill ejecutable de instalación y optimización del rendimiento de Hermes Agent. No es un fork ejecutable: mide cuellos de botella y aplica cambios estructurales pequeños, comprobables y reversibles.

## Recomendaciones

- `orjson`: JSON más rápido con fallback a `json`.
- `msgspec`: parsing tipado de mensajes y llamadas de herramientas estables.
- `uvloop`: event loop opcional con fallback a `asyncio`.
- Escritura de sesiones por lotes para reducir I/O y transacciones SQLite.
- Startup y descubrimiento de herramientas más rápidos con caché versionada e invalidación correcta.
- Caché de metadatos externos con TTL y escritura atómica, sin secretos.
- Paralelismo solo para operaciones independientes, con orden determinista, límites, timeout y cancelación.

## Beneficios esperados

Benchmarks anteriores del fork observaron aproximadamente 4–6x en JSON grande, 3–4x en mensajes, 19–38x en el camino medido de persistencia y 2–4x en startup. Son referencias, no garantías: hay que reproducirlas en el Hermes real.

Deben conservarse prompt caching, compatibilidad, fallbacks Python/`asyncio`, seguridad y rollback. Consulta `README.md` y `SKILL.md`.
