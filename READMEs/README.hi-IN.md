# Hermes Turbo Agent

Hermes Agent की स्थापना और performance optimization के लिए executable Skill। यह executable fork नहीं है: bottlenecks मापती है और छोटे, testable तथा reversible structural बदलाव लागू करती है।

## सिफारिशें

- `orjson`: `json` fallback के साथ तेज़ JSON।
- `msgspec`: स्थिर messages और tool calls के लिए typed parsing।
- `uvloop`: `asyncio` fallback वाला optional event loop।
- I/O और SQLite transactions घटाने के लिए sessions को batch में लिखना।
- versioned cache और सही invalidation से startup और tool discovery तेज़ करना।
- TTL और atomic writes वाला external-metadata cache; secrets कभी न रखें।
- केवल independent operations को deterministic order, limits, timeout और cancellation के साथ parallel करना।

## अपेक्षित लाभ

पिछले fork benchmarks में बड़े JSON पर लगभग 4–6x, message path पर 3–4x, measured persistence path पर 19–38x और startup पर 2–4x देखा गया। ये references हैं, guarantees नहीं; वास्तविक Hermes path पर इन्हें दोहराना होगा।

prompt caching, compatibility, Python/`asyncio` fallbacks, security और rollback सुरक्षित रहने चाहिए। `README.md` और `SKILL.md` देखें।
