# Search-NEIRO roadmap

## North-star outcome

Produce a reproducible, source-backed CUSTOMER_QUERY_SIMULATION audit that can be repeated after repair with the same query bank and compared as DELTA.

## Phase 0 — Measurement Core v1 (implemented in this patch)

**Goal:** preserve evidence and repeatability metadata without breaking the current UI.

Deliverables:

- SQLite schema and versioning;
- stable company/query/run/task IDs;
- attempts, status, capture mode, Web mode, geo and session fields;
- immutable evidence files and SHA-256 hashes;
- structured observations with evidence spans;
- CSV importer and CLI summary;
- tests and CI.

Acceptance:

- legacy `ui_tasks.csv` imports without data loss;
- every non-empty answer creates answer, metadata and sources artifacts;
- counts are visible via `neirosearch-measurement summary`;
- tests pass on Python 3.10 and 3.12.

## Phase 1 — UI integration and browser hygiene

**Goal:** write to SQLite/evidence at capture time.

- add `run_id`, `attempt`, status and error code columns to the UI;
- save screenshots and DOM excerpts on failures;
- split browser providers into versioned adapters;
- remove automation-evasion flags;
- add explicit `CAPTCHA_SHOWN`, `LOGIN_REQUIRED`, `PROVIDER_UI_CHANGED` states;
- never auto-retry captcha/login failures.

Acceptance: one full real company run can be resumed after restart without duplicate tasks.

## Phase 2 — Analyzer quality and evals

**Goal:** move from keyword guesses to measured extraction quality.

- build `tests/fixtures/labeled_answers.jsonl` from 50–100 real answers;
- label mention, recommendation, competitors, answer class, reason codes and evidence spans;
- measure precision/recall by field;
- add deterministic + optional structured-LLM extraction;
- version prompts, analyzers and judge models;
- gate releases on regression thresholds.

Acceptance: no analyzer release without a benchmark report.

## Phase 3 — Repeatability and client report

**Goal:** implement the v2.3 REPEATABILITY_PROTOCOL in product output.

- measurement plans with 1/3–3/3 attempts;
- cross-system and repeated signal aggregation;
- intent-aware metrics;
- report sections: FACT → SIGNAL LEVEL → EVIDENCE → MEANING → ACTION;
- before/after delta export.

Acceptance: critical client claims are traceable to task IDs and evidence files.

## Phase 4 — FREE_AI_SCOUT

**Gate:** first paid audits completed and manual bottleneck documented.

- cheap/free models collect candidates, sources, contradictions and questions;
- strict structured output;
- deduplication and verification queues;
- paid model receives only a compact `synthesis_pack`;
- no autonomous external actions.

Acceptance: measurable reduction in paid-model tokens or analyst time.

## Phase 5 — MEMORY_ROAD

**Gate:** hundreds of verified events across several projects.

- append-only memory events;
- provenance and supersession;
- SQLite FTS5 + entity index first;
- temporal retrieval and synthesis checkpoints;
- optional Graphiti/Mem0 patterns only after local benchmark.

Acceptance: every synthesized fact links to one or more source events.

## Phase 6 — API gateway and durable orchestration

**Gate:** repeatable paid usage requires it.

- LiteLLM-compatible provider gateway;
- cost/latency/error normalization;
- optional OpenTelemetry/Langfuse;
- LangGraph/Pydantic durable execution only for resumable multi-step jobs.

## STOP list

Do not build now:

- multi-user SaaS;
- billing or personal accounts;
- proxy/captcha/stealth infrastructure;
- autonomous publishing or outreach;
- vector DB by default;
- endless provider expansion without a client need.
