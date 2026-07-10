# Search-NEIRO

> Repository and Python distribution currently keep the legacy spelling `Searh-NEIRO` / `searh-neiro` for compatibility. New technical and client-facing documentation uses **Search-NEIRO**.

Search-NEIRO is an internal tool for **НейроВижин** audits. It models live customer questions such as “кого выбрать”, “где заказать” and “к кому обратиться”, records what AI systems answer, identifies competitors and evidence gaps, and supports a repeat measurement after source repair.

It does **not** sell or guarantee placement in ChatGPT, Алиса, search engines or maps.

## Operating modes

### 1. Official API / local model mode

Uses configured APIs or local OpenAI-compatible endpoints. Provider definitions live in `config/providers.yaml`.

### 2. Manual web mode

Generates a CSV task list. A user opens each AI service, submits the prompt, and pastes the answer and visible sources back into the table.

### 3. Assisted browser mode

Uses a visible local Chrome/Edge profile and the user's own sessions to reduce repetitive work. This mode is UI-fragile and must be used in small volumes. It does not bypass login, captcha or service limits.

Every browser/manual result is an observation from a specific user session and date, not official platform statistics.

## Current capabilities

- query bank generation and batch/manual workflows;
- API and local-provider adapters;
- visible-browser queue for selected services;
- brand mention and recommendation heuristics;
- competitor candidates;
- JSONL, Excel-safe CSV and Markdown reports;
- optional OpenSERP search;
- **Measurement Core v1:** SQLite runs/tasks, immutable evidence hashes, structured observations and CSV import.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
cp .env.example .env
```

## Existing workflow without API keys

```bash
neirosearch manual-template \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --output outputs/manual_prompts.csv
```

Fill `answer`, `citations` and `notes`, then:

```bash
neirosearch manual-import \
  --input outputs/manual_prompts.csv \
  --brand "Название Компании" \
  --competitors "Конкурент 1,Конкурент 2" \
  --output outputs/manual_report
```

## Measurement Core v1

The current Streamlit CSV workflow remains intact. Import completed rows into a local evidence database:

```bash
neirosearch-measurement init --db outputs/neirosearch.db

neirosearch-measurement import-ui \
  --input outputs/ui_tasks.csv \
  --db outputs/neirosearch.db \
  --evidence-root outputs/evidence

neirosearch-measurement summary --db outputs/neirosearch.db
```

See [docs/MEASUREMENT_CORE.md](docs/MEASUREMENT_CORE.md) and follow the staged [implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md) before merging the new core into the main workflow.

## API audit

```bash
neirosearch run \
  --brand "Название Компании" \
  --industry "ремонт квартир под ключ" \
  --region "Москва" \
  --competitors "Конкурент 1,Конкурент 2" \
  --providers "gigachat,yandexgpt,gemini,qwen,deepseek,perplexity" \
  --output outputs/moscow-repair
```

## Evidence and trust

Strong conclusions require at least one of:

- repetition across systems;
- repetition across attempts;
- a verifiable source;
- client confirmation;
- a dated screenshot/export of the exact answer and query.

Machine extraction is a candidate, not a fact. Measurement Core stores evidence spans and flags uncertain observations for manual review. Re-importing unchanged evidence is idempotent; changed content creates a new content-addressed capture rather than overwriting the prior artifact.

## Development priorities

1. Measurement Core and immutable evidence.
2. UI integration, resumable tasks and explicit error states.
3. A human-labeled answer dataset and regression tests.
4. Repeatability aggregation and before/after reports.
5. FREE_AI_SCOUT and MEMORY_ROAD only after paid workflow signals.

See [docs/ROADMAP.md](docs/ROADMAP.md), [docs/GITHUB_BENCHMARK.md](docs/GITHUB_BENCHMARK.md) and [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md).

## Safety and automation hygiene

Allowed:

- small-volume user-initiated runs;
- personal sessions;
- answer/screenshot export;
- date, Web mode, geo and session logging;
- local queues and evidence storage.

Not allowed in this project:

- captcha bypass or solving;
- proxy pools or account farming;
- hidden form submissions;
- aggressive scraping;
- spam, fake reviews or fake accounts;
- autonomous publication or external actions without explicit approval.

## License

MIT.
