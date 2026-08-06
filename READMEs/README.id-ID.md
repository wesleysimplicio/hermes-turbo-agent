# Hermes Turbo Agent

Skill yang dapat dijalankan untuk instalasi dan optimasi performa Hermes Agent. Ini bukan fork yang dapat dijalankan: skill ini mengukur bottleneck dan menerapkan perubahan struktural yang kecil, dapat diuji, dan dapat dibatalkan.

## Rekomendasi

- `orjson`: JSON lebih cepat dengan fallback ke `json`.
- `msgspec`: parsing bertipe untuk pesan dan tool call yang stabil.
- `uvloop`: event loop opsional dengan fallback ke `asyncio`.
- Penulisan sesi secara batch untuk mengurangi I/O dan transaksi SQLite.
- Startup dan penemuan tool lebih cepat dengan cache berversi dan invalidasi yang benar.
- Cache metadata eksternal dengan TTL dan penulisan atomik, tanpa secrets.
- Paralelkan hanya operasi independen dengan urutan deterministik, batas, timeout, dan pembatalan.

## Manfaat yang diharapkan

Benchmark fork sebelumnya mengamati sekitar 4–6x pada JSON besar, 3–4x pada jalur pesan, 19–38x pada jalur persistensi yang diukur, dan 2–4x pada startup. Ini referensi, bukan jaminan; pengukuran harus diulang pada Hermes nyata.

Prompt caching, kompatibilitas, fallback Python/`asyncio`, keamanan, dan rollback harus dipertahankan. Lihat `README.md` dan `SKILL.md`.
