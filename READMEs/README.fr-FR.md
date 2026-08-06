# Hermes Turbo Agent

Skill exécutable d’installation et d’optimisation des performances pour Hermes Agent. Ce n’est pas un fork exécutable : elle mesure les goulots d’étranglement et applique des changements structurels petits, testables et réversibles.

## Recommandations

- `orjson` : JSON plus rapide avec fallback vers `json`.
- `msgspec` : parsing typé des messages et tool calls stables.
- `uvloop` : event loop optionnelle avec fallback vers `asyncio`.
- Écriture groupée des sessions pour réduire l’I/O et les transactions SQLite.
- Startup et découverte des outils accélérés par un cache versionné et correctement invalidé.
- Cache des métadonnées externes avec TTL et écriture atomique, sans secrets.
- Paralléliser uniquement les opérations indépendantes, avec ordre déterministe, limites, timeout et annulation.

## Bénéfices attendus

Les anciens benchmarks du fork indiquaient environ 4–6x pour le gros JSON, 3–4x pour les messages, 19–38x pour le chemin mesuré de persistance et 2–4x au démarrage. Ce sont des références, pas des garanties : il faut les reproduire dans Hermes.

Le prompt caching, la compatibilité, les fallbacks Python/`asyncio`, la sécurité et le rollback doivent être préservés. Voir `README.md` et `SKILL.md`.
