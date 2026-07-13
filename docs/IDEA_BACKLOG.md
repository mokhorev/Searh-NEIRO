# Search-NEIRO Idea Backlog

## Purpose

Документ фиксирует идеи из внешнего tool radar и выгрузок, но не означает немедленную реализацию.

## Selection principles

- Идея должна приближать к аудиту, ремонту источников или повторному замеру.
- Нельзя строить SaaS до платных сигналов.
- Нельзя обходить капчи, лимиты, ToS, использовать прокси-пулы или серую автоматизацию.
- Ответы малых моделей не считаются фактами без evidence.

## P1 — EVIDENCE_HUB / SOURCE_REGISTRY

### Назначение

Единый слой источников для AI-ответов, сайта, карточек, отзывов, SERP, документов, PDF, соцсетей, DreamJob и ручных заметок.

### Почему важно

НейроВижин должен объяснять не только что ответила модель, но и какие источники формируют видимость компании.

### Статус

roadmap only.

## P1 — CLAIM_VALIDATION_QUEUE

### Назначение

Проверять сильные утверждения отчёта через evidence, статус доверия и разрешённую формулировку.

### Поля

claim, observation, evidence, verified_status, allowed_wording, forbidden_wording, risk.

### Статус

roadmap only.

## P1 — SITE_SNAPSHOT_AUDIT + CONTENT_GAP

### Назначение

Сохранять и анализировать страницы сайта клиента: услуги, контакты, офферы, CTA, NAP, schema, robots, sitemap, пиксели, формы, FAQ, технические и рекламные ошибки.

### Статус

documented in `docs/SITE_SNAPSHOT_AUDIT.md`, not implemented.

## P2 — RESEARCH_TASK_TEMPLATE

### Назначение

Шаблоны Deep Research для ниши, конкурентов, HR-репутации, отзывов, внешних источников и коммерческих запросов.

### Статус

roadmap only.

## P2 — REPORT_PACK_GENERATOR

### Назначение

Генерировать client-facing материалы из evidence: teaser, audit, before-pack, delta-report, slide outline.

### Статус

roadmap only.

## P2 — RUN_ENV_HEALTH_CHECK

### Назначение

Проверять окружение перед замером: сеть, доступ к temp/cache, браузеры, git status, версии Python, доступность outputs.

### Статус

roadmap only.

## P3 — MODEL_ROUTER_EXPERIMENT

### Назначение

Исследовать единый роутер дешёвых/бесплатных моделей для FREE_AI_SCOUT.

### Ограничения

Без обхода лимитов, без мультиаккаунт-абуза, без SaaS до оплат.

### Статус

later.

## Rejected / not now

- browser auto-click agents;
- mass website downloader;
- proxy pools;
- CAPTCHA bypass;
- fake reviews/accounts;
- public SaaS UI;
- image/video generators as core product;
- unrelated consumer productivity tools.
