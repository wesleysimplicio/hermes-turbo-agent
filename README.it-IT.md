# Hermes Turbo Agent

Skill di raccomandazioni e audit delle prestazioni per Hermes Agent. Non è un fork eseguibile: misura i colli di bottiglia e applica modifiche strutturali piccole, verificabili e reversibili.

## Raccomandazioni

- `orjson`: JSON più veloce con fallback a `json`.
- `msgspec`: parsing tipizzato di messaggi e tool call stabili.
- `uvloop`: event loop opzionale con fallback a `asyncio`.
- Scrittura delle sessioni in batch per ridurre I/O e transazioni SQLite.
- Startup e tool discovery più rapidi tramite cache versionata e invalidata correttamente.
- Cache dei metadati esterni con TTL e scrittura atomica, senza segreti.
- Parallelizzare solo operazioni indipendenti, con ordine deterministico e timeout.

## Benefici attesi

I benchmark precedenti del fork hanno osservato circa 4–6x sul JSON grande, 3–4x nel percorso dei messaggi, 19–38x nel percorso misurato di persistenza e 2–4x nello startup. Sono riferimenti, non garanzie: vanno riprodotti in Hermes.

Prompt caching, compatibilità, fallback Python/`asyncio`, sicurezza e rollback restano obbligatori. Vedere `README.md` e `SKILL.md`.
