# Hermes Turbo Agent

Skill rekomendasi dan audit performa untuk Hermes Agent. Ini bukan fork yang dapat dieksekusi; skill ini mengukur bottleneck lalu menerapkan perubahan struktural kecil, teruji, dan dapat dibatalkan.

## Rekomendasi

- `orjson`: serialisasi JSON lebih cepat dengan fallback ke `json`.
- `msgspec`: parsing bertipe untuk pesan dan tool call yang stabil.
- `uvloop`: event loop opsional dengan fallback ke `asyncio`.
- Menulis sesi secara batch untuk mengurangi I/O dan transaksi SQLite.
- Mempercepat startup dan discovery tools dengan cache berversi yang di-invalidasi dengan benar.
- Cache metadata eksternal memakai TTL dan atomic write, tanpa secrets.
- Paralelkan hanya operasi independen dengan urutan deterministik, batas, dan timeout.

## Manfaat yang diharapkan

Benchmark fork sebelumnya menunjukkan sekitar 4–6x untuk JSON besar, 3–4x untuk message path, 19–38x untuk path penyimpanan sesi yang diukur, dan 2–4x untuk startup. Ini adalah referensi, bukan jaminan; hasil harus diukur ulang pada Hermes nyata.

prompt caching, kompatibilitas, fallback Python/`asyncio`, keamanan, dan rollback wajib dipertahankan. Lihat `README.md` dan `SKILL.md`.
