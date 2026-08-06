# Hermes Turbo Agent

Skill eseguibile per l’installazione e l’ottimizzazione delle prestazioni di Hermes Agent. Non è un fork eseguibile: misura i colli di bottiglia e applica modifiche strutturali piccole, verificabili e reversibili.

## Raccomandazioni

- `orjson`: JSON più veloce con fallback a `json`.
- `msgspec`: parsing tipizzato di messaggi e tool call stabili.
- `uvloop`: event loop opzionale con fallback a `asyncio`.
- Scrittura batch delle sessioni per ridurre I/O e transazioni SQLite.
- Startup e scoperta degli strumenti più rapidi con cache versionata e invalidazione corretta.
- Cache dei metadati esterni con TTL e scrittura atomica, senza segreti.
- Parallelizzare solo operazioni indipendenti, con ordine deterministico, limiti, timeout e cancellazione.

## Benefici attesi

I benchmark precedenti del fork hanno osservato circa 4–6x sul JSON grande, 3–4x nel percorso dei messaggi, 19–38x nel percorso misurato della persistenza e 2–4x nello startup. Sono riferimenti, non garanzie: le misure vanno riprodotte su Hermes reale.

Prompt caching, compatibilità, fallback Python/`asyncio`, sicurezza e rollback devono essere preservati. Consulta `README.md` e `SKILL.md`.
