# Hermes Turbo Agent

Skill für Performance-Empfehlungen und Audits von Hermes Agent. Sie erstellt keinen ausführbaren Fork, sondern misst Engpässe und wendet kleine, testbare und rücksetzbare Strukturänderungen an.

## Empfehlungen

- `orjson`: schnelleres JSON mit Fallback auf das Python-Standardmodul.
- `msgspec`: typisiertes Parsing stabiler Nachrichten und Tool-Aufrufe.
- `uvloop`: optionaler Event Loop mit Fallback auf `asyncio`.
- Sitzungen stapelweise in SQLite speichern, um I/O zu reduzieren.
- Startup und Tool-Erkennung durch versionierten, korrekt invalidierten Cache beschleunigen.
- Externe Metadaten mit TTL und atomarem Schreiben cachen, ohne Geheimnisse.
- Unabhängige Operationen sicher parallel ausführen.

## Erwartete Vorteile

Frühere Fork-Benchmarks zeigten etwa 4–6x bei großem JSON, 3–4x im Nachrichtenpfad, 19–38x im gemessenen Session-Speicherpfad und 2–4x beim Startup. Das sind Referenzen, keine Garantien; sie müssen im echten Hermes reproduziert werden.

Prompt-Caching, Kompatibilität, Python/`asyncio`-Fallbacks, Sicherheit und Rollback bleiben Pflicht. Siehe `README.md` und `SKILL.md`.
