# Запуск Searh-NEIRO на Windows

Инструкция для запуска проекта на обычном компьютере без API-ключей. API-режим можно подключить позже.

## 1. Установи Python

Нужен Python 3.10 или новее.

Проверь в PowerShell:

```powershell
python --version
```

Если Python не найден, установи его с python.org и поставь галочку **Add python.exe to PATH**.

## 2. Установи Git

Проверь:

```powershell
git --version
```

Если Git не найден, установи Git for Windows.

## 3. Скачай проект

Открой PowerShell в папке, где будут проекты, например `C:\Projects`:

```powershell
mkdir C:\Projects
cd C:\Projects
git clone https://github.com/mokhorev/Searh-NEIRO.git
cd Searh-NEIRO
```

## 4. Создай виртуальное окружение

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Если PowerShell запрещает запуск скрипта активации:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 5. Установи проект

```powershell
python -m pip install --upgrade pip
pip install -e .
```

## 6. Проверь, что CLI работает

```powershell
neirosearch --help
neirosearch providers
```

Если команда `neirosearch` не найдена, используй так:

```powershell
python -m neirosearch.cli --help
```

## 7. Запуск без API-ключей

Создай CSV-шаблон промптов:

```powershell
neirosearch manual-template `
  --brand "Название Компании" `
  --industry "ремонт квартир под ключ" `
  --region "Москва" `
  --output outputs\manual_prompts.csv
```

Открой файл:

```powershell
start outputs\manual_prompts.csv
```

Дальше:

1. копируй промпт из колонки `prompt`;
2. вставляй его в ChatGPT / Gemini / Qwen / GigaChat / Claude / Perplexity / DeepSeek / Grok через браузер;
3. копируй ответ;
4. вставляй ответ в колонку `answer`;
5. сохраняй CSV.

## 8. Собери отчёт из заполненного CSV

```powershell
neirosearch manual-import `
  --input outputs\manual_prompts.csv `
  --brand "Название Компании" `
  --competitors "Конкурент 1,Конкурент 2" `
  --output outputs\manual_report
```

Результаты появятся тут:

```text
outputs\manual_report\results.jsonl
outputs\manual_report\summary.csv
outputs\manual_report\report.md
```

## 9. Запуск с API-ключами позже

Скопируй пример окружения:

```powershell
copy .env.example .env
notepad .env
```

Вставь ключи нужных провайдеров, потом проверь:

```powershell
neirosearch providers
```

Запуск API-аудита:

```powershell
neirosearch run `
  --brand "Название Компании" `
  --industry "ремонт квартир под ключ" `
  --region "Москва" `
  --providers "gigachat,yandexgpt,gemini,qwen,deepseek" `
  --output outputs\api_report
```

## 10. Частые ошибки

### `python` не найден

Переустанови Python и включи **Add python.exe to PATH**.

### `neirosearch` не найден

Активируй окружение:

```powershell
.\.venv\Scripts\Activate.ps1
```

Или запускай через Python:

```powershell
python -m neirosearch.cli --help
```

### PowerShell запрещает activate

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### CSV открылся кракозябрами

Открывай через Excel с кодировкой UTF-8 или через Google Sheets. Файл пишется в UTF-8-SIG, обычно Excel Windows должен открыть его нормально.
