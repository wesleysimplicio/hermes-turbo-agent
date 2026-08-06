# Hermes Turbo Agent

Skill cadangan dan audit prestasi untuk Hermes Agent. Ia bukan fork boleh laksana; ia mengukur bottleneck dan menggunakan perubahan struktur yang kecil, boleh diuji dan boleh dipulihkan.

## Cadangan

- `orjson`: JSON lebih pantas dengan fallback kepada `json`.
- `msgspec`: parsing bertip untuk mesej dan tool call yang stabil.
- `uvloop`: event loop pilihan dengan fallback kepada `asyncio`.
- Simpan sesi secara batch untuk mengurangkan I/O dan transaksi SQLite.
- Percepat startup dan tool discovery melalui cache berversi yang dibatalkan dengan betul.
- Cache metadata luaran dengan TTL dan atomic write, tanpa rahsia.
- Selaraskan hanya operasi bebas secara selamat dengan susunan deterministik, had dan timeout.

## Manfaat dijangka

Benchmark fork terdahulu menunjukkan kira-kira 4–6x untuk JSON besar, 3–4x untuk laluan mesej, 19–38x untuk laluan persistence sesi yang diukur dan 2–4x untuk startup. Ini rujukan, bukan jaminan; ukur semula pada Hermes sebenar.

Kekalkan prompt caching, keserasian, fallback Python/`asyncio`, keselamatan dan rollback. Lihat `README.md` dan `SKILL.md`.
