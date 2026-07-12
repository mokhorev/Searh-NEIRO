# Режим без API-ключей

Если API-ключей нет, Searh-NEIRO всё равно можно использовать в трёх режимах.

## 1. Ручной режим через веб-версии нейросетей

Этот режим нужен, когда ты используешь ChatGPT, Gemini, Qwen, GigaChat, Claude, DeepSeek, Perplexity, Grok и другие сервисы через браузер, в том числе через VPN.

Сначала сгенерируй CSV-шаблон с промптами:

```bash
neirosearch manual-template \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --output outputs/manual_prompts.csv
```

Открой `outputs/manual_prompts.csv` в Excel / Google Sheets / LibreOffice.

В каждой строке:

1. скопируй `prompt`;
2. вставь его в нужную веб-нейросеть;
3. скопируй ответ;
4. вставь ответ в колонку `answer`;
5. если модель дала ссылки — вставь их в `citations` через запятую.

Потом импортируй заполненную таблицу:

```bash
neirosearch manual-import \
  --input outputs/manual_prompts.csv \
  --brand "Название Компании" \
  --competitors "Конкурент 1,Конкурент 2" \
  --output outputs/manual_report
```

На выходе появятся:

- `results.jsonl` — полный лог;
- `summary.csv` — таблица;
- `report.md` — отчёт.

## 2. Локальные модели без ключей

Можно использовать локальные модели через Ollama или LM Studio.

Пример Ollama:

```bash
ollama pull qwen2.5:7b
ollama serve
neirosearch run \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --providers "ollama" \
  --output outputs/ollama_test
```

Минус: локальные модели не знают свежий интернет без поискового слоя. Для свежести подключай OpenSERP.

## 3. OpenSERP без ключей

OpenSERP можно использовать как поисковый слой без ключей поисковиков.

```bash
neirosearch search "лучшие компании по ремонту квартир Москва" \
  --engines yandex,bing,duckduckgo,google \
  --limit 10 \
  --lang RU \
  --region RU
```

OpenSERP не заменяет нейросети. Он показывает, какие источники видны в поиске, чтобы потом сравнивать это с ответами нейросетей.

## Что нельзя сделать честно без ключей

Нельзя стабильно и законно автоматизировать закрытые веб-интерфейсы ChatGPT/Gemini/Claude/GigaChat как API. Поэтому в проекте нет браузерного обхода авторизации, капч и лимитов.

Правильные варианты без ключей:

- ручной CSV-режим;
- локальные модели;
- OpenSERP;
- локальный видимый Playwright-автокомбайн с пользовательским профилем браузера. Он не обходит авторизацию, капчи, лимиты или другие защиты и не предназначен для публичного сервиса.
