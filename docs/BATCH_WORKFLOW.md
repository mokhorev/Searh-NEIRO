# Пакетный режим: несколько компаний и несколько промптов

Этот режим нужен для ежедневной работы: 4–7 компаний в день, 5–10 промптов на компанию.

## 1. Обновить проект на компьютере

```powershell
git pull
pip install -e .
```

## 2. Создать пример файла компаний

```powershell
neirosearch companies-example --output inputs\companies.csv
```

Формат:

```csv
brand,industry,region,competitors
В отражении,сложное окрашивание волос,Красноярск,"Салон 1,Салон 2"
Компания 2,ремонт квартир под ключ,Москва,"Конкурент 1,Конкурент 2"
```

## 3. Отредактировать промпты

Файл промптов уже есть:

```text
inputs\prompts.txt
```

Можно вставить туда 5–10 своих промптов. Поддерживаются переменные:

- `{brand}` — название компании;
- `{industry}` — ниша/услуга;
- `{region}` — город/регион.

## 4. Создать общую таблицу задач

```powershell
neirosearch batch-manual-template `
  --companies inputs\companies.csv `
  --prompts inputs\prompts.txt `
  --providers "chatgpt_web,gemini_web,qwen_web,gigachat_web,perplexity_web,deepseek_web,grok_web" `
  --output outputs\batch_manual_prompts.csv
```

Открой таблицу:

```powershell
start outputs\batch_manual_prompts.csv
```

В таблице будут все сочетания:

```text
компания × нейросеть × промпт
```

Вставляй ответы в колонку `answer`. Если нейросеть дала ссылки, вставляй их в `citations` через запятую.

## 5. Собрать отчёты по всем компаниям

```powershell
neirosearch batch-manual-import `
  --input outputs\batch_manual_prompts.csv `
  --output outputs\batch_report
```

На выходе будет отдельная папка по каждой компании:

```text
outputs\batch_report\в_отражении\report.md
outputs\batch_report\в_отражении\summary.csv
outputs\batch_report\в_отражении\results.jsonl
```

## Удобный дневной сценарий

```powershell
cd C:\Projects\Searh-NEIRO
.\.venv\Scripts\Activate.ps1
git pull
pip install -e .
notepad inputs\companies.csv
notepad inputs\prompts.txt
neirosearch batch-manual-template --companies inputs\companies.csv --prompts inputs\prompts.txt --output outputs\batch_manual_prompts.csv
start outputs\batch_manual_prompts.csv
```

После заполнения ответов:

```powershell
neirosearch batch-manual-import --input outputs\batch_manual_prompts.csv --output outputs\batch_report
start outputs\batch_report
```

## Следующее улучшение

Следующий удобный шаг — assisted browser mode: программа будет открывать вкладки веб-нейросетей, копировать промпт в буфер обмена и помогать собирать ответы. Если конкретная веб-страница поменяется, отчётный режим всё равно останется рабочим через CSV.
