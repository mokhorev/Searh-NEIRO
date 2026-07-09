# Searh-NEIRO

**Searh-NEIRO** — инструмент для проверки, какие нейросети рекомендуют компанию, бренд, товар или услугу.

Проект помогает делать аудит AI-видимости для России и глобальных AI-сервисов, включая провайдеров, которыми часто пользуются из РФ напрямую или через VPN: OpenAI/ChatGPT, Google Gemini, Qwen, DeepSeek, GigaChat, YandexGPT, Claude, Perplexity, xAI Grok, Mistral, Groq, OpenRouter, Together, Fireworks, Ollama и LM Studio.

> Важно: проект использует официальные API, локальные модели, ручной CSV-режим и видимый локальный браузер пользователя. Он не обходит авторизацию, капчи и защиты сервисов. OpenSERP используется только как отдельный поисковый слой по локальному endpoint пользователя.

## Что делает

- прогоняет один и тот же набор промптов по нескольким нейросетям;
- проверяет, найден ли бренд в ответе;
- определяет примерную позицию бренда в ответе;
- ищет упоминания конкурентов и кандидатов-конкурентов из AI-ответов;
- сохраняет отчёты в JSONL, CSV и Markdown;
- опционально использует OpenSERP как поисковый слой для свежих источников;
- поддерживает no-key режим через ручной CSV-опрос веб-версий нейросетей;
- поддерживает Streamlit-кабинет для очереди, автокомбайна, отчёта и WEB_FOOTPRINT_SCAN.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .
cp .env.example .env
```

Заполни `.env` ключами нужных провайдеров. Если ключей нет, используй ручной режим или Streamlit UI.

## Streamlit UI

Windows-запуск из локальной папки проекта:

```powershell
cd C:\Projects\Searh-NEIRO
python -m pip install -e .
python -m streamlit run .\src\neirosearch\ui_app.py
```

Основные разделы UI:

- `Поиск` — создать очередь запросов по компании, промптам и выбранным нейросетям;
- `Автокомбайн` — прогнать незаполненные задачи через видимый локальный браузер;
- `Очередь` — проверить незаполненные, готовые или все задачи;
- `По компаниям` — посмотреть прогресс по каждой компании;
- `Источники / Поиск` — запустить WEB_FOOTPRINT_SCAN через локальный OpenSERP;
- `Отчёт` — увидеть AI-видимость, рекомендации и кандидатов-конкурентов.

Для Qwen, Perplexity и GigaChat обычно ставь таймаут 300–360 секунд.

## Видимый браузерный автокомбайн

Первичный вход в выбранные веб-нейросети:

```powershell
python -m neirosearch.browser_cli login --providers "chatgpt_web,qwen_web,deepseek_web,gigachat_web,perplexity_web"
```

Отдельный вход в GigaChat после QR Сбербанк:

```powershell
python -m neirosearch.browser_cli login --providers "gigachat_web"
```

Запуск малой партии:

```powershell
python -m neirosearch.browser_cli run --providers "qwen_web" --limit 1 --delay 15 --timeout 360
python -m neirosearch.browser_cli run --providers "gigachat_web" --limit 1 --delay 15 --timeout 360
python -m neirosearch.browser_cli run --providers "gemini_web" --limit 1 --delay 15 --timeout 360
python -m neirosearch.browser_cli run --providers "grok_web" --limit 1 --delay 15 --timeout 360
```

Автокомбайн работает только с твоими аккаунтами в видимом браузере и сохраняет сессию в `browser_profile/`.

## Если API-ключей нет

Сгенерируй таблицу промптов:

```bash
neirosearch manual-template \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --output outputs/manual_prompts.csv
```

Открой CSV, вставь каждый промпт в веб-версии ChatGPT/Gemini/Qwen/GigaChat/Claude/Perplexity/DeepSeek/Grok, затем вставь ответы в колонку `answer`.

Потом собери отчёт:

```bash
neirosearch manual-import \
  --input outputs/manual_prompts.csv \
  --brand "Название Компании" \
  --competitors "Конкурент 1,Конкурент 2" \
  --output outputs/manual_report
```

Подробно: `docs/NO_API_KEYS.md`.

## Проверить готовность провайдеров

```bash
neirosearch providers
```

## Запуск аудита через API

```bash
neirosearch run \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --competitors "Конкурент 1,Конкурент 2" \
  --providers "gigachat,yandexgpt,gemini,qwen,deepseek,perplexity" \
  --output outputs/moscow-repair
```

После запуска появятся:

- `outputs/.../results.jsonl` — полный машинный лог;
- `outputs/.../summary.csv` — таблица для Excel/Google Sheets;
- `outputs/.../report.md` — текстовый отчёт.

## OpenSERP / WEB_FOOTPRINT_SCAN

OpenSERP — отдельный поисковый слой. Он нужен не вместо AI-автокомбайна, а для сравнения: кого видно в поиске и кого затем советуют AI.

Подними OpenSERP локально:

```powershell
docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000
```

Проверка через CLI:

```powershell
neirosearch search "лучшие компании по ремонту квартир Москва" `
  --engines "google,yandex,bing,duckduckgo" `
  --limit 10 `
  --lang RU `
  --region RU `
  --base-url "http://127.0.0.1:7000" `
  --mode balanced
```

Проверка через UI:

1. Запусти Streamlit UI.
2. Открой раздел `Источники / Поиск`.
3. Выбери компанию.
4. Проверь автоматически собранные поисковые запросы.
5. Нажми `Запустить WEB_FOOTPRINT_SCAN`.

Результат сохраняется в:

```text
outputs/serp/<company_slug>/serp_results.csv
```

В UI показывается:

- кто всплыл в поиске;
- полная таблица SERP results;
- сравнение `AI ответы` vs `поиск`, если по компании уже есть сохранённые AI-ответы.

## Поддерживаемые типы провайдеров

### OpenAI-compatible

Один универсальный адаптер для:

- OpenAI / ChatGPT API;
- Google Gemini OpenAI-compatible endpoint;
- Qwen / Alibaba Cloud Model Studio / DashScope;
- DeepSeek;
- xAI Grok;
- Mistral;
- Groq;
- OpenRouter;
- Together AI;
- Fireworks AI;
- LM Studio;
- любые свои OpenAI-compatible proxy/vLLM/LiteLLM endpoints.

### Отдельные адаптеры

- GigaChat — OAuth token + `/chat/completions`;
- YandexGPT — Yandex AI Studio Completion API;
- Claude — Anthropic Messages API;
- Perplexity — Sonar API;
- Ollama — локальные модели.

## Конфигурация

Провайдеры описаны в `config/providers.yaml`. Можно добавлять новые OpenAI-compatible сервисы без изменения кода: достаточно указать `base_url`, `model` и переменную окружения для ключа.

## Юридически и технически

Используй официальные API, свои аккаунты, локальный браузер и соблюдай правила провайдеров. VPN может быть нужен для доступа к некоторым сервисам, но проект не содержит механизмов обхода ограничений, капч или авторизации. Клиентская часть OpenSERP в проекте не настраивает прокси-пулы и не обещает попадание в AI-ответы или топ поисковой выдачи.
