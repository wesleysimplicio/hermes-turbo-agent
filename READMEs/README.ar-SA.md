# Hermes Turbo Agent

Skill قابلة للتنفيذ لتثبيت Hermes Agent وتحسين أدائه. ليست fork قابلة للتنفيذ؛ بل تقيس نقاط الاختناق وتطبق تغييرات هيكلية صغيرة وقابلة للاختبار والتراجع.

## التوصيات

- `orjson`: JSON أسرع مع fallback إلى `json`.
- `msgspec`: parsing مكتوب للرسائل وtool calls ذات العقود المستقرة.
- `uvloop`: event loop اختياري مع fallback إلى `asyncio`.
- كتابة الجلسات على دفعات لتقليل I/O ومعاملات SQLite.
- تسريع startup وtool discovery باستخدام cache بإصدار وإبطال صحيح.
- cache للبيانات الوصفية الخارجية مع TTL وكتابة ذرية، من دون أسرار.
- تنفيذ العمليات المستقلة بالتوازي فقط، مع ترتيب حتمي وحدود وtimeout وإلغاء.

## الفوائد المتوقعة

أظهرت benchmarks السابقة للـ fork نحو 4–6x في JSON الكبير، و3–4x في مسار الرسائل، و19–38x في مسار الاستمرارية المقاس، و2–4x عند startup. هذه مراجع وليست ضمانات؛ يجب إعادة قياسها على Hermes الحقيقي.

يجب الحفاظ على prompt caching والتوافق وfallbacks الخاصة بـ Python/`asyncio` والأمان وrollback. راجع `README.md` و`SKILL.md`.
