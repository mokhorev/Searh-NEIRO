# Measurement Core v1

Measurement Core is the local evidence and repeatability layer for Search-NEIRO. It is deliberately additive: the existing Streamlit CSV queue keeps working while completed rows can be imported into SQLite.

## Why

The project methodology requires more than `brand_found`:

- stable `run_id`, `task_id`, `query_id` and `attempt`;
- capture mode, Web mode, geo, personalization and session;
- immutable answer evidence with hashes;
- explicit error/status codes;
- structured observations and evidence spans;
- a path toward repeatability, DELTA and MEMORY_ROAD.

## Quick start

```bash
pip install -e ".[dev]"
neirosearch-measurement init --db outputs/neirosearch.db
neirosearch-measurement import-ui \
  --input outputs/ui_tasks.csv \
  --db outputs/neirosearch.db \
  --evidence-root outputs/evidence
neirosearch-measurement summary --db outputs/neirosearch.db
```

## Evidence layout

```text
outputs/evidence/
  <company_id>/
    <run_id>/
      <provider_id>/
        <query_id>/
          attempt_01/
            capture_<hash>/
              answer.md
              sources.json
              metadata.json
```

The capture hash covers the answer, citations and import metadata. Re-importing the same row is idempotent; changed content creates a new capture directory instead of overwriting prior evidence.

Every answer and evidence file is hashed with SHA-256. `metadata.json` records the prompt, provider, attempt, capture mode, Web mode, geo and session information available at import time.

## Database tables

- `companies`
- `queries`
- `runs`
- `tasks`
- `answers`
- `observations`
- `evidence_items`
- `memory_events`

SQLite is the operational source of truth. CSV, Markdown and Google Sheets remain exchange/export formats.

## Migration policy

1. Do not remove `outputs/ui_tasks.csv` yet.
2. Import it into SQLite after a run.
3. Compare row counts and evidence counts.
4. Integrate the UI only after the importer has been used on at least two real cases.
5. Keep every schema change versioned in `schema_meta`.

## Trust model

Machine extraction is never treated as a final fact. New observations are marked `RAW_SIGNAL`, include evidence spans, and default to manual review where confidence, citations or entity extraction are weak.
