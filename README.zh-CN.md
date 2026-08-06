# Hermes Turbo Agent

用于 Hermes Agent 性能建议与审计的 Skill。它不是可执行 fork，而是先测量瓶颈，再应用小型、可测试、可回滚的结构性改进。

## 建议

- `orjson`：在保留标准 `json` fallback 的前提下加速 JSON。
- `msgspec`：对稳定的消息和 tool call 使用类型化 parsing。
- `uvloop`：在兼容平台上作为可选 event loop，并保留 `asyncio` fallback。
- 批量写入 session，减少 SQLite I/O 和事务次数。
- 使用带版本和正确失效机制的 cache 加速启动与工具发现。
- 使用 TTL 和原子写入缓存外部元数据，不能保存秘密。
- 仅并行执行相互独立的操作，并保持确定性顺序、并发限制和 timeout。

## 预期收益

旧 fork 的 benchmark 观察到：大型 JSON 约 4–6 倍，消息路径约 3–4 倍，实测 session 持久化路径约 19–38 倍，启动约 2–4 倍。这些只是参考值，不是保证；必须在真实 Hermes 中重新测量。

必须保持 prompt caching、兼容性、Python/`asyncio` fallback、安全性和 rollback。详见 `README.md` 与 `SKILL.md`。
