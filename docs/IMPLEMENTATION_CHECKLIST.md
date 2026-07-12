# Measurement Core v1 implementation checklist

## 0. Before merge

- [ ] Open draft PR #2 and verify the changed-file list.
- [ ] Confirm CI is green on Python 3.10 and 3.12.
- [ ] Back up the current local `outputs/ui_tasks.csv` and `outputs/` folder.
- [ ] Confirm no client evidence, browser profile or secret is staged in Git.

## 1. Local trial on a copy of real data

```bash
pip install -e ".[dev]"
neirosearch-measurement init --db outputs/neirosearch_trial.db
neirosearch-measurement import-ui \
  --input outputs/ui_tasks.csv \
  --db outputs/neirosearch_trial.db \
  --evidence-root outputs/evidence_trial \
  --run-prefix trial
neirosearch-measurement summary --db outputs/neirosearch_trial.db
```

Verify:

- [ ] CSV row count equals tasks + intentionally skipped rows.
- [ ] Every non-empty answer appears in `answers`.
- [ ] Every imported answer creates `answer.md`, `metadata.json`, `sources.json`.
- [ ] SHA-256 is present in metadata/database.
- [ ] Existing Streamlit workflow still opens and saves CSV normally.

## 2. Inspect three representative answers

Choose:

- [ ] client absent, competitor recommended;
- [ ] client mentioned but not recommended;
- [ ] client clearly recommended.

For each, verify:

- [ ] observation is directionally correct;
- [ ] evidence span quotes the supporting sentence;
- [ ] uncertain/entity-heavy cases are marked for manual review;
- [ ] no machine label is treated as a final client claim.

## 3. Merge gate

Merge only when:

- [ ] CI green;
- [ ] trial import completed;
- [ ] no data loss or duplicate tasks;
- [ ] evidence paths are readable on the target Windows machine;
- [ ] README operating modes match actual use;
- [ ] rollback is simply switching back to legacy CSV workflow.

Recommended merge method: squash.

## 4. After merge

- [ ] Tag or note version `0.2.0`.
- [ ] Use Measurement Core import on two real cases.
- [ ] Record import defects as issues, not ad-hoc schema edits.
- [ ] Start issue #3 only after the two imports are stable.
- [ ] Do not start FREE_AI_SCOUT or MEMORY_ROAD implementation yet.

## 5. Next development order

1. Issue #3 — Streamlit/SQLite integration.
2. Issue #4 — provider adapters and browser hygiene.
3. Issue #5 — labeled answer corpus and regression evals.
4. Issue #6 — repeatability and DELTA reports.
5. Issue #7 — FREE_AI_SCOUT / MEMORY_ROAD after paid workflow signal.
