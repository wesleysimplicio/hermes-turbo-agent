# Hermes Turbo Agent

Hermes Agent의 설치 및 성능 최적화를 위한 실행 가능한 Skill입니다. 실행 가능한 fork가 아니라 병목을 측정하고 작고 테스트 가능하며 되돌릴 수 있는 구조 변경을 적용합니다.

## 권장 사항

- `orjson`: `json` fallback을 제공하는 더 빠른 JSON.
- `msgspec`: 안정적인 메시지와 tool call의 타입 기반 parsing.
- `uvloop`: `asyncio` fallback을 제공하는 선택적 event loop.
- 세션을 일괄 저장하여 I/O와 SQLite 트랜잭션을 줄입니다.
- 버전이 있는 cache와 올바른 무효화로 startup과 tool discovery를 가속합니다.
- TTL과 atomic write를 사용하는 외부 메타데이터 cache. 비밀은 저장하지 않습니다.
- 독립 작업만 결정적 순서, 제한, timeout, 취소를 유지하며 병렬화합니다.

## 기대 효과

이전 fork 벤치마크에서는 큰 JSON 약 4–6배, 메시지 경로 3–4배, 측정된 persistence 경로 19–38배, startup 2–4배가 관찰되었습니다. 보장이 아니라 참고값이므로 실제 Hermes에서 재현해야 합니다.

prompt caching, 호환성, Python/`asyncio` fallback, 보안 및 rollback을 보존해야 합니다. `README.md`와 `SKILL.md`를 참조하세요.
