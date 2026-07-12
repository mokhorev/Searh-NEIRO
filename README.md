# Search-NEIRO

> Репозиторий и Python-дистрибутив пока сохраняют legacy-написание `Searh-NEIRO` / `searh-neiro` ради совместимости. В новой документации используется техническое имя **Search-NEIRO**. Клиентский бренд услуги — **НейроВижин**.

Search-NEIRO — внутренний инструмент НейроВижин для CUSTOMER_QUERY_SIMULATION: он прогоняет живые клиентские запросы «кого выбрать», «где заказать», «к кому обратиться», сохраняет ответы AI-систем, отделяет органическую видимость от упоминания бренда в самом промпте, фиксирует конкурентов и помогает повторить тот же замер после ремонта источников.

Проект не продаёт и не гарантирует место в ChatGPT, Алисе, поиске или картах.

## Режимы работы

### 1. Official API / local model

Используются настроенные API или локальные OpenAI-compatible endpoints. Провайдеры описаны в `config/providers.yaml`.

### 2. Manual web

Программа создаёт CSV-очередь. Пользователь вручную отправляет запросы в веб-версии AI-сервисов и вставляет ответы и видимые источники обратно в таблицу.

### 3. Assisted browser

Используется видимый локальный Chrome/Edge и пользовательские сессии. Режим предназначен для малых объёмов, зависит от интерфейсов сайтов и не обходит логин, капчу или лимиты сервисов.

Каждый web/browser-ответ — наблюдение в конкретной пользовательской сессии и дате, а не официальная статистика платформы.

## Что уже умеет проект

- формировать и обрабатывать очередь живых клиентских запросов;
- работать через API, локальные модели, ручной CSV и видимый браузер;
- хранить `status`, `attempts`, `error`, `run_id`, время выполнения и логи;
- запускать только задачи `pending` и `retry`;
- показывать статистику по провайдерам, компаниям и статусам;
- отделять органическое появление бренда от подсказанного промптом;
- извлекать заданных конкурентов и кандидатов-конкурентов;
- сохранять JSONL, Excel-safe CSV и Markdown-отчёты;
- выполнять WEB_FOOTPRINT_SCAN через локальный OpenSERP;
- импортировать завершённую CSV-очередь в Measurement Core v1: SQLite, immutable evidence, SHA-256 и structured observations.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

## Streamlit UI

Windows-запуск:

```powershell
cd C:\Projects\Searh-NEIRO
python -m pip install -e ".[dev]"
python -m streamlit run .\src\neirosearch\ui_app.py
```

Основные разделы:

- `Поиск` — создать очередь по компании, запросам и AI-системам;
- `Автокомбайн` — выполнить незаполненные и повторные задачи;
- `Очередь` — проверить незаполненные, готовые или все задачи;
- `По компаниям` — увидеть прогресс;
- `Статистика` — статусы, ошибки, повторы, провайдеры и последние логи;
- `Источники / Поиск` — WEB_FOOTPRINT_SCAN через OpenSERP;
- `Отчёт` — органическая видимость, рекомендации и конкуренты.

Для Qwen, Perplexity и GigaChat обычно требуется таймаут 300–360 секунд.

## Видимый браузерный автокомбайн

Первичный вход:

```powershell
python -m neirosearch.browser_cli login --providers "chatgpt_web,qwen_web,deepseek_web,gigachat_web,perplexity_web"
```

Малый запуск:

```powershell
python -m neirosearch.browser_cli run --providers "qwen_web" --limit 1 --delay 15 --timeout 360
python -m neirosearch.browser_cli run --providers "gigachat_web" --limit 1 --delay 15 --timeout 360
```

Сессии сохраняются локально в `browser_profile/`. Капчи, авторизация и ограничения сервисов не обходятся.

## Ручной режим без API-ключей

```bash
neirosearch manual-template \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --output outputs/manual_prompts.csv
```

После заполнения колонок `answer`, `citations`, `notes`:

```bash
neirosearch manual-import \
  --input outputs/manual_prompts.csv \
  --brand "Название Компании" \
  --competitors "Конкурент 1,Конкурент 2" \
  --output outputs/manual_report
```

Подробнее: `docs/NO_API_KEYS.md`.

## API-аудит

```bash
neirosearch run \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --competitors "Конкурент 1,Конкурент 2" \
  --providers "gigachat,yandexgpt,gemini,qwen,deepseek,perplexity" \
  --output outputs/moscow-repair
```

## Measurement Core v1

Существующий Streamlit/CSV-процесс остаётся рабочим. Завершённые строки импортируются в локальную evidence-базу:

```bash
neirosearch-measurement init --db outputs/neirosearch.db

neirosearch-measurement import-ui \
  --input outputs/ui_tasks.csv \
  --db outputs/neirosearch.db \
  --evidence-root outputs/evidence

neirosearch-measurement summary --db outputs/neirosearch.db
```

Measurement Core хранит:

- стабильные `company_id`, `query_id`, `run_id`, `task_id`;
- попытку, систему, модель, capture/Web mode, гео, персонализацию и сессию;
- исходный ответ, источники и metadata;
- content-addressed evidence с SHA-256;
- structured observations и evidence spans;
- явные статусы и error codes;
- основу для REPEATABILITY, DELTA и MEMORY_ROAD.

Подробнее: `docs/MEASUREMENT_CORE.md` и `docs/IMPLEMENTATION_CHECKLIST.md`.

## OpenSERP / WEB_FOOTPRINT_SCAN

OpenSERP — отдельный поисковый слой. Он нужен для сопоставления поискового следа и AI-рекомендаций.

```powershell
docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000

neirosearch search "лучшие компании по ремонту квартир Москва" `
  --engines "google,yandex,bing,duckduckgo" `
  --limit 10 `
  --lang RU `
  --region RU `
  --base-url "http://127.0.0.1:7000" `
  --mode balanced
```

Результаты сохраняются в `outputs/serp/<company_slug>/serp_results.csv`.

## Evidence и доверие

Сильный вывод требует хотя бы одного основания:

- повтор в нескольких системах;
- повтор в нескольких попытках;
- проверяемый источник;
- подтверждение клиента;
- датированный скриншот или экспорт точного ответа и запроса.

Машинная классификация — кандидат на вывод, а не факт. Неизменившийся evidence импортируется идемпотентно; изменившийся ответ создаёт новую content-addressed версию и не перезаписывает предыдущую.

## Приоритеты разработки

1. Measurement Core и сохранность evidence.
2. Прямая запись из UI, возобновляемые задачи и явные ошибки.
3. Human-labeled corpus и регрессионные тесты анализатора.
4. REPEATABILITY 1/3–3/3 и before/after DELTA.
5. FREE_AI_SCOUT и MEMORY_ROAD только после платного сигнала и подтверждённого bottleneck.

См. `docs/ROADMAP.md`, `docs/GITHUB_BENCHMARK.md`, `docs/DATA_GOVERNANCE.md`.

## Безопасность и гигиена автоматизации

Разрешено:

- малые пользовательские запуски;
- собственные аккаунты и сессии;
- сохранение ответов, скриншотов и источников;
- локальная очередь, логи и evidence;
- фиксация даты, Web mode, гео и сессии.

В проект не входят:

- обход или решение капчи;
- stealth-флаги, прокси-пулы и массовые аккаунты;
- скрытая отправка форм;
- агрессивный скрейпинг;
- спам, фейковые отзывы и фейковые аккаунты;
- автономные публикации или внешние действия без подтверждения.

Клиентские данные, browser profile, cookies, API-ключи и evidence не должны попадать в Git. См. `SECURITY.md` и `docs/DATA_GOVERNANCE.md`.

## Лицензия

MIT.
