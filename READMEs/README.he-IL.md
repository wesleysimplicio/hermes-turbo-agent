# Hermes Turbo Agent

Skill להמלצות ולביקורת ביצועים עבור Hermes Agent. היא אינה fork להרצה, אלא מודדת צווארי בקבוק ומיישמת שינויים קטנים, ניתנים לבדיקה ולביטול.

## המלצות

- `orjson`: סריאליזציית JSON מהירה יותר עם fallback ל־`json`.
- `msgspec`: parsing טיפוסי להודעות ולקריאות כלים יציבות.
- `uvloop`: event loop אופציונלי עם fallback ל־`asyncio`.
- כתיבת sessions באצוות להפחתת I/O ועסקאות SQLite.
- האצת startup וגילוי כלים באמצעות cache עם versioning ו־invalidation נכון.
- cache למטא־נתונים חיצוניים עם TTL וכתיבה אטומית, ללא סודות.
- מקביליות רק לפעולות בלתי תלויות, עם סדר דטרמיניסטי, מגבלות ו־timeouts.

## תועלות צפויות

Benchmarks קודמים של ה־fork הראו בערך 4–6x ב־JSON גדול, 3–4x בנתיב ההודעות, 19–38x בנתיב שמירת sessions שנמדד, ו־2–4x ב־startup. אלה נתוני ייחוס ולא הבטחות; יש לשחזר אותם ב־Hermes עצמו.

יש לשמור על prompt caching, תאימות, fallbacks של Python/`asyncio`, אבטחה ויכולת rollback. ראו `README.md` ו־`SKILL.md`.
