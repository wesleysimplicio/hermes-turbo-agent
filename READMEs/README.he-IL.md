# Hermes Turbo Agent

Skill הניתנת להרצה להתקנה ולאופטימיזציית ביצועים עבור Hermes Agent. זה אינו fork הניתן להרצה: היא מודדת צווארי בקבוק ומיישמת שינויים מבניים קטנים, ניתנים לבדיקה ולהחזרה.

## המלצות

- `orjson`: JSON מהיר יותר עם fallback ל־`json`.
- `msgspec`: parsing טיפוסי של הודעות ו־tool calls יציבים.
- `uvloop`: event loop אופציונלי עם fallback ל־`asyncio`.
- כתיבת sessions באצווה כדי לצמצם I/O ועסקאות SQLite.
- האצת startup ו־tool discovery באמצעות cache עם גרסה וביטול תקין.
- cache למטא־נתונים חיצוניים עם TTL וכתיבה אטומית, ללא secrets.
- להקביל רק פעולות בלתי תלויות, תוך שמירה על סדר דטרמיניסטי, מגבלות, timeout וביטול.

## יתרונות צפויים

Benchmarks קודמים של ה־fork הראו בערך 4–6x ב־JSON גדול, 3–4x בנתיב ההודעות, 19–38x בנתיב ההתמדה שנמדד ו־2–4x ב־startup. אלה ערכי ייחוס ולא הבטחות; יש לשחזר אותם ב־Hermes האמיתי.

יש לשמור על prompt caching, תאימות, fallbacks של Python/`asyncio`, אבטחה ו־rollback. ראו `README.md` ו־`SKILL.md`.
