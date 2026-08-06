# Hermes Turbo Agent

Hermes Agent के लिए performance recommendations और audit skill। यह executable fork नहीं है; यह bottleneck मापकर छोटे, testable और reversible structural बदलाव सुझाती और लागू करती है।

## सिफारिशें

- `orjson`: standard `json` fallback के साथ तेज़ JSON serialization।
- `msgspec`: स्थिर messages और tool calls के लिए typed parsing।
- `uvloop`: `asyncio` fallback के साथ वैकल्पिक event loop।
- SQLite I/O और transactions घटाने के लिए batched session writes।
- versioned और सही तरीके से invalidated cache से startup और tool discovery तेज़ करना।
- TTL और atomic writes वाला external metadata cache, बिना secrets के।
- केवल independent operations का सुरक्षित parallel execution।

## अपेक्षित लाभ

पुराने fork benchmarks में बड़े JSON पर लगभग 4–6x, message path पर 3–4x, मापे गए session persistence path पर 19–38x और startup पर 2–4x देखा गया। ये references हैं, guarantees नहीं; Hermes में दोबारा मापना आवश्यक है।

prompt caching, compatibility, Python/`asyncio` fallbacks, security और rollback सुरक्षित रहने चाहिए। पूरी जानकारी `README.md` और `SKILL.md` में है।
