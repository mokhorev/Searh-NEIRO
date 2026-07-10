# Changelog

## 0.2.0 — Measurement Core v1

- Added validated domain schemas for companies, queries, runs, tasks, answers, evidence, observations and memory events.
- Added local SQLite storage with WAL, schema versioning and resumable task metadata.
- Added immutable, content-addressed answer evidence (`answer.md`, `sources.json`, `metadata.json`) with SHA-256 hashes and idempotent re-import.
- Added a backward-compatible importer for `outputs/ui_tasks.csv`.
- Added a separate `neirosearch-measurement` CLI.
- Added structured baseline observations with evidence spans and manual-review flags.
- Added Excel formula-injection protection for CSV report text fields.
- Added unit tests and GitHub Actions CI on Linux/Python 3.10–3.12 and Windows/Python 3.12.
- Rewrote README to describe API, manual and assisted-browser modes accurately.
- Added implementation roadmap, rollout checklist, GitHub benchmark, security policy and client-data governance.
