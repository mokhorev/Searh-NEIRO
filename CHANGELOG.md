# Changelog

## 0.2.0 — Measurement Core v1

- Added validated domain schemas for companies, queries, runs, tasks, answers, evidence, observations and memory events.
- Added local SQLite storage with WAL, schema versioning and resumable task metadata.
- Added immutable answer evidence (`answer.md`, `sources.json`, `metadata.json`) with SHA-256 hashes.
- Added a backward-compatible importer for `outputs/ui_tasks.csv`.
- Added a separate `neirosearch-measurement` CLI.
- Added structured baseline observations with evidence spans and manual-review flags.
- Added unit tests and GitHub Actions CI.
- Rewrote README to describe API, manual and assisted-browser modes accurately.
- Added implementation roadmap and GitHub benchmark.
