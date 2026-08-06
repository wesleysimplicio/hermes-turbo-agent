# Hermes Turbo Agent

Skill boleh laku untuk pemasangan dan pengoptimuman prestasi Hermes Agent. Ia bukan fork boleh laku: ia mengukur bottleneck dan menggunakan perubahan struktur yang kecil, boleh diuji dan boleh dipulihkan.

## Cadangan

- `orjson`: JSON lebih pantas dengan fallback kepada `json`.
- `msgspec`: parsing bertype untuk mesej dan tool call yang stabil.
- `uvloop`: event loop pilihan dengan fallback kepada `asyncio`.
- Menulis sesi secara kelompok untuk mengurangkan I/O dan transaksi SQLite.
- Startup dan penemuan alat lebih pantas dengan cache berversi serta invalidasi yang betul.
- Cache metadata luaran dengan TTL dan penulisan atomik, tanpa secrets.
- Selarikan hanya operasi bebas, dengan susunan deterministik, had, timeout dan pembatalan.

## Faedah yang dijangka

Benchmark fork terdahulu menunjukkan kira-kira 4–6x untuk JSON besar, 3–4x pada laluan mesej, 19–38x pada laluan persistence yang diukur dan 2–4x ketika startup. Ini rujukan, bukan jaminan; ukuran mesti diulang pada Hermes sebenar.

Prompt caching, keserasian, fallback Python/`asyncio`, keselamatan dan rollback mesti dikekalkan. Lihat `README.md` dan `SKILL.md`.
