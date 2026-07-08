# Searh-NEIRO

**Searh-NEIRO** — инструмент для проверки, какие нейросети рекомендуют компанию, бренд, товар или услугу.

Проект помогает делать аудит AI-видимости для России и глобальных AI-сервисов, включая провайдеров, которыми часто пользуются из РФ напрямую или через VPN: OpenAI/ChatGPT, Google Gemini, Qwen, DeepSeek, GigaChat, YandexGPT, Claude, Perplexity, xAI Grok, Mistral, Groq, OpenRouter, Together, Fireworks, Ollama и LM Studio.

> Важно: проект использует официальные API и локальные модели. Он не парсит закрытые веб-интерфейсы ChatGPT/Gemini/Claude/GigaChat и не обходит авторизацию сервисов.

## Что делает

- прогоняет один и тот же набор промптов по нескольким нейросетям;
- проверяет, найден ли бренд в ответе;
- определяет примерную позицию бренда в ответе;
- ищет упоминания конкурентов;
- сохраняет отчёты в JSONL, CSV и Markdown;
- опционально использует OpenSERP как поисковый слой для свежих источников.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .
cp .env.example .env
```

Заполни `.env` ключами нужных провайдеров.

## Проверить готовность провайдеров

```bash
neirosearch providers
```

## Запуск аудита

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

## OpenSERP-поиск

Если локально поднят OpenSERP:

```bash
neirosearch search "лучшие компании по ремонту квартир Москва" \
  --engines yandex,bing,duckduckgo,google \
  --limit 10 \
  --lang RU \
  --region RU
```

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

Используй официальные API, свои ключи и соблюдай правила провайдеров. VPN может быть нужен для доступа к некоторым сервисам, но проект не содержит механизмов обхода ограничений, капч или авторизации.
