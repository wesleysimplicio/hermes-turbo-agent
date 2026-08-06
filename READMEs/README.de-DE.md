# Hermes Turbo Agent

Ausführbare Skill zur Installation und Leistungsoptimierung von Hermes Agent. Sie ist kein ausführbarer Fork: Sie misst Engpässe und wendet kleine, testbare und rücksetzbare Strukturänderungen an.

## Empfehlungen

- `orjson`: schnelleres JSON mit Fallback auf `json`.
- `msgspec`: typisiertes Parsing stabiler Nachrichten und Tool-Aufrufe.
- `uvloop`: optionaler Event Loop mit Fallback auf `asyncio`.
- Sitzungen stapelweise speichern, um I/O und SQLite-Transaktionen zu reduzieren.
- Startup und Tool-Erkennung durch versionierten, korrekt invalidierten Cache beschleunigen.
- Externe Metadaten mit TTL und atomarem Schreiben cachen, ohne Geheimnisse.
- Unabhängige Operationen nur mit deterministischer Reihenfolge, Limits, Timeout und Abbruch parallelisieren.

## Erwartete Vorteile

Frühere Fork-Benchmarks zeigten etwa 4–6x bei großem JSON, 3–4x im Nachrichtenpfad, 19–38x im gemessenen Persistenzpfad und 2–4x beim Startup. Das sind Referenzen, keine Garantien; sie müssen im echten Hermes reproduziert werden.

Prompt-Caching, Kompatibilität, Python/`asyncio`-Fallbacks, Sicherheit und Rollback müssen erhalten bleiben. Siehe `README.md` und `SKILL.md`.
