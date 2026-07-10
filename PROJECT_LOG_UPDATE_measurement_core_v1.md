# PROJECT_LOG_UPDATE — Measurement Core v1

Дата: 2026-07-10.

Решение: начать техническое улучшение Search-NEIRO с доказательного ядра, а не с новых провайдеров или SaaS-функций.

Причина: методология v2.3 требует повторов, уровней сигнала, evidence, before/after и MEMORY_ROAD, а текущий CSV-анализ хранит в основном текст ответа и факт упоминания бренда.

Что внесено:

- SQLite Measurement Core;
- стабильные company/query/run/task ID;
- attempt, capture mode, Web mode, geo, session и status;
- evidence store с SHA-256;
- структурированные observations и evidence spans;
- импорт существующего `ui_tasks.csv`;
- тесты и CI;
- дорожная карта и GitHub benchmark.

Что не меняется:

- существующая Streamlit-очередь продолжает работать;
- CSV/Markdown остаются экспортными форматами;
- клиентский бренд — НейроВижин;
- Search-NEIRO до оплат — внутренний cost-cutter.

Что запрещено:

- captcha/stealth/proxy/account-farming;
- автоматические внешние действия;
- признание машинной классификации фактом без проверки;
- переход к LangGraph/vector DB/SaaS без доказанного узкого места.

Следующий шаг: импортировать реальный `outputs/ui_tasks.csv`, сверить количество ответов и evidence, затем подключить запись в SQLite непосредственно из UI.
