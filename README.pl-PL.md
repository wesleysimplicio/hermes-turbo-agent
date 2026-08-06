# Hermes Turbo Agent

Skill z zaleceniami i audytem wydajności Hermes Agent. Nie jest wykonywalnym forkiem: mierzy wąskie gardła i stosuje małe, testowalne oraz odwracalne zmiany strukturalne.

## Zalecenia

- `orjson`: szybszy JSON z fallbackiem do standardowego `json`.
- `msgspec`: typowane parsowanie stabilnych wiadomości i tool calls.
- `uvloop`: opcjonalny event loop z fallbackiem do `asyncio`.
- Grupowy zapis sesji, aby zmniejszyć I/O i liczbę transakcji SQLite.
- Szybszy startup i tool discovery dzięki wersjonowanemu cache z poprawną invalidacją.
- Cache zewnętrznych metadanych z TTL i atomic write, bez sekretów.
- Równoległość tylko dla niezależnych operacji, z deterministyczną kolejnością i timeoutami.

## Oczekiwane korzyści

Wcześniejsze benchmarki forka wykazały około 4–6x dla dużego JSON, 3–4x dla ścieżki wiadomości, 19–38x dla zmierzonej ścieżki zapisu sesji i 2–4x dla startupu. To wartości referencyjne, nie gwarancje; należy je odtworzyć w Hermes.

Należy zachować prompt caching, kompatybilność, fallbacki Python/`asyncio`, bezpieczeństwo i rollback. Szczegóły: `README.md` i `SKILL.md`.
