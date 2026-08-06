# Hermes Turbo Agent

Wykonywalny skill do instalacji i optymalizacji wydajności Hermes Agent. To nie jest wykonywalny fork: mierzy wąskie gardła i stosuje małe, testowalne oraz odwracalne zmiany strukturalne.

## Zalecenia

- `orjson`: szybszy JSON z fallbackiem do `json`.
- `msgspec`: typowane parsing wiadomości i stabilnych wywołań narzędzi.
- `uvloop`: opcjonalny event loop z fallbackiem do `asyncio`.
- Grupowy zapis sesji w celu ograniczenia I/O i transakcji SQLite.
- Szybszy startup i wykrywanie narzędzi dzięki wersjonowanemu cache z poprawną invalidacją.
- Cache zewnętrznych metadanych z TTL i zapisem atomowym, bez sekretów.
- Równoległość tylko dla niezależnych operacji, z deterministyczną kolejnością, limitami, timeoutem i anulowaniem.

## Oczekiwane korzyści

Wcześniejsze benchmarki forka wykazały około 4–6x dla dużego JSON, 3–4x dla ścieżki wiadomości, 19–38x dla zmierzonej ścieżki utrwalania i 2–4x podczas startupu. To wartości referencyjne, nie gwarancje; pomiary trzeba powtórzyć na rzeczywistym Hermes.

Należy zachować prompt caching, kompatybilność, fallbacki Python/`asyncio`, bezpieczeństwo i rollback. Zobacz `README.md` i `SKILL.md`.
