# Массовая проверка

Цель этапа — прогнать 10–15 компаний и проверить устойчивость связки:

```text
Поиск → Очередь → Автокомбайн → Статистика → Отчёт
```

## Что добавлено перед тестом

- статусы задач в `outputs/ui_tasks.csv`;
- журнал каждого запуска в `outputs/logs/browser_run_<run_id>.log`;
- автоматический перевод ошибок в статус `retry`;
- сохранение количества попыток, последнего запуска и длительности;
- отдельная Streamlit-страница `Статистика`;
- проверка дублей по связке `компания + нейросеть + prompt_id + prompt`.

## Статусы

```text
pending  — задача ещё не запускалась
running  — задача сейчас в запуске
ok       — ответ сохранён
retry    — нужна повторная попытка
error    — зарезервировано для ручной фиксации критической ошибки
skipped  — зарезервировано для пропуска
```

Автокомбайн берёт задачи без ответа, включая `pending` и `retry`.

## Рекомендуемый первый объём

```text
10 компаний × 6 промптов × 5–7 нейросетей = 300–420 задач
```

Для первичного краш-теста лучше идти партиями:

```powershell
python -m neirosearch.browser_cli run --providers "chatgpt_web" --limit 10 --delay 10 --timeout 300
python -m neirosearch.browser_cli run --providers "qwen_web" --limit 5 --delay 15 --timeout 360
python -m neirosearch.browser_cli run --providers "gigachat_web" --limit 5 --delay 15 --timeout 360
python -m neirosearch.browser_cli run --providers "perplexity_web" --limit 5 --delay 15 --timeout 360
```

После каждой партии открыть страницу `Статистика` и проверить:

- сколько `OK`;
- сколько `retry`;
- какие нейросети падают чаще;
- есть ли дубли;
- какие ошибки повторяются в логах.

## Где смотреть файлы

```text
outputs/ui_tasks.csv          — очередь и статусы
outputs/logs/                 — журналы запусков автокомбайна
outputs/ui_report/<company>/  — отчёты по компаниям
outputs/serp/<company>/       — поисковый слой OpenSERP
```
