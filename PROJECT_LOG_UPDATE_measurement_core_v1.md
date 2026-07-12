# PROJECT_LOG_UPDATE — Measurement Core v1

Дата: 2026-07-13.

Решение: интегрировать доказательное ядро Search-NEIRO поверх уже проверенного операционного слоя очереди, статистики и органической AI-видимости.

Причина: методология v2.3 требует повторов, уровней сигнала, evidence, before/after и MEMORY_ROAD, а операционная ветка уже добавила status/retry/run_id, логи, статистику и разделение подсказанной и органической видимости.

Что внесено:

- SQLite Measurement Core;
- стабильные company/query/run/task ID;
- attempt, capture mode, Web mode, geo, session и status;
- content-addressed evidence store с SHA-256;
- структурированные observations и evidence spans;
- импорт существующего `ui_tasks.csv`;
- Excel-safe CSV;
- cross-platform CI;
- дорожная карта, data governance и GitHub benchmark;
- согласованные README, pyproject, CI, ignores и reports с операционной веткой.

Что не меняется:

- существующая Streamlit-очередь продолжает работать;
- статусы, retry, browser logs и страница статистики сохраняются;
- CSV/Markdown остаются экспортными форматами;
- клиентский бренд — НейроВижин;
- Search-NEIRO до оплат — внутренний cost-cutter.

Что запрещено:

- captcha/stealth/proxy/account-farming;
- автоматические внешние действия;
- признание машинной классификации фактом без проверки;
- переход к LangGraph/vector DB/SaaS без доказанного узкого места.

Проверка интеграции:

- PR #1 с операционным слоем слит в `main` после зелёного CI;
- PR #2 нацелен на `integration/measurement-core-v1`;
- конфликтующие файлы приведены к одинаковой объединённой версии;
- итоговый merge допускается только после зелёного CI на объединённом дереве.

Следующий шаг: импортировать реальный `outputs/ui_tasks.csv`, сверить количество ответов и evidence, затем подключить запись в SQLite непосредственно из UI.
