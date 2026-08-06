# Hermes Turbo Agent

Hermes Agent のインストールと性能最適化を行う実行可能な Skill です。実行可能な fork ではなく、ボトルネックを測定し、小さくテスト可能で元に戻せる構造変更を適用します。

## 推奨事項

- `orjson`: `json` fallback 付きの高速 JSON。
- `msgspec`: 安定したメッセージと tool call の型付き parsing。
- `uvloop`: `asyncio` fallback 付きの任意 event loop。
- セッションをまとめて SQLite に保存し、I/O とトランザクションを削減。
- versioned cache と正しい無効化で startup と tool discovery を高速化。
- TTL と atomic write を使う外部メタデータ cache。秘密情報は保存しない。
- 独立した処理だけを決定的な順序、上限、timeout、キャンセル付きで並列化。

## 期待される効果

過去の fork ベンチマークでは、大きな JSON で約 4–6 倍、メッセージ経路で 3–4 倍、測定した永続化経路で 19–38 倍、startup で 2–4 倍でした。保証ではなく参考値なので、実際の Hermes で再測定します。

prompt caching、互換性、Python/`asyncio` fallback、安全性、rollback を維持します。詳細は `README.md` と `SKILL.md` を参照してください。
