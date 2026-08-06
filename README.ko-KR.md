# Hermes Turbo Agent

Hermes Agent의 성능 권장 사항과 감사를 위한 Skill입니다. 실행 가능한 fork가 아니라 병목을 측정하고 작고 테스트 가능하며 되돌릴 수 있는 구조 변경을 적용합니다.

## 권장 사항

- `orjson`: 표준 `json` fallback을 갖춘 빠른 JSON 처리.
- `msgspec`: 안정적인 메시지와 tool call의 typed parsing.
- `uvloop`: `asyncio` fallback을 갖춘 선택적 event loop.
- 세션을 batch로 저장해 SQLite I/O와 트랜잭션을 줄입니다.
- 버전이 지정되고 올바르게 무효화되는 cache로 startup과 tool discovery를 개선합니다.
- TTL과 atomic write를 사용하는 외부 metadata cache. 비밀은 저장하지 않습니다.
- 독립 작업만 결정적 순서, 제한, timeout과 함께 병렬화합니다.

## 기대 효과

이전 fork benchmark에서는 큰 JSON 약 4–6배, 메시지 경로 3–4배, 측정된 session persistence 경로 19–38배, startup 2–4배의 개선이 관찰되었습니다. 보장이 아니라 참고값이며 실제 Hermes에서 재측정해야 합니다.

prompt caching, 호환성, Python/`asyncio` fallback, 보안과 rollback을 유지해야 합니다. 자세한 내용은 `README.md`와 `SKILL.md`를 확인하세요.
