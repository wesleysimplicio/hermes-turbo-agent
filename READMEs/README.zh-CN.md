# Hermes Turbo Agent

用于 Hermes Agent 安装与性能优化的可执行 Skill。它不是可执行 fork，而是先测量瓶颈，再应用小型、可测试且可回滚的结构性修改。

## 建议

- `orjson`：更快的 JSON，并保留 `json` fallback。
- `msgspec`：用于稳定消息和 tool call 的类型化 parsing。
- `uvloop`：可选 event loop，并保留 `asyncio` fallback。
- 批量写入会话，减少 I/O 和 SQLite 事务。
- 使用版本化 cache 并正确失效，加速 startup 和 tool discovery。
- 使用 TTL 与 atomic write 缓存外部元数据，不保存 secrets。
- 仅并行执行独立操作，并保持确定性顺序、限制、timeout 和取消语义。

## 预期收益

旧 fork 的 benchmark 在大型 JSON 上约提升 4–6 倍，消息路径 3–4 倍，实测持久化路径 19–38 倍，startup 2–4 倍。这些只是参考而非保证，必须在真实 Hermes 路径上复现。

必须保留 prompt caching、兼容性、Python/`asyncio` fallback、安全性和 rollback。请参阅 `README.md` 与 `SKILL.md`。
