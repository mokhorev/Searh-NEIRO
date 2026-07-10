# GitHub benchmark: what Search-NEIRO should borrow

Reviewed: 2026-07-10.

## Adopt now

| Project | Strong pattern | Search-NEIRO adoption |
|---|---|---|
| Promptfoo | test case × provider × assertion; repeatable comparison | Golden dataset and regression matrix for real AI answers |
| DeepEval | pytest-like LLM evaluation; custom metrics and JSON correctness | Unit tests for answer classification, evidence completeness and prompt alignment |
| Inspect AI | extensible eval components, scorers and reproducible development workflow | Separate dataset, solver/capture and scorer/analysis layers |
| Pydantic AI | validated structured outputs, type safety, human approval | Pydantic schemas for tasks, evidence, observations and memory events |
| Langfuse | traces, datasets, manual labels, evaluations | Local trace/evidence schema first; optional OTel/Langfuse later |
| Stagehand | combine deterministic code with AI only where needed; cache repeatable actions | Provider adapters and deterministic selectors; AI fallback only after a selector failure |

## Adopt later

| Project | Strong pattern | Gate |
|---|---|---|
| LiteLLM | one provider interface, normalized errors, cost tracking | After paid API-mode demand appears |
| LangGraph | durable execution, checkpoints, human-in-the-loop | When FREE_AI_SCOUT has multi-step resumable workflows |
| Mem0 | append-only memory, entity linking, temporal retrieval | After several projects generate hundreds of memory events |
| Graphiti | provenance episodes, validity windows, hybrid retrieval | When SQLite FTS5 is insufficient and temporal entity relations matter |
| Browser Use | browser task benchmarking and reusable agent tooling | Borrow benchmarks/diagnostics only; do not adopt stealth, proxy rotation or captcha solving |

## Explicit non-adoptions

- No proxy pools, captcha solving, stealth or account farming.
- No free-form multi-agent debate as the core workflow.
- No vector database before SQLite + FTS5 is measured and insufficient.
- No SaaS/account/billing layer before repeatable paid audits.
- No LLM judge without a human-labeled regression set and recorded judge version.

## Architectural consequence

The next moat is not another provider. It is a labeled evidence corpus linking:

```text
customer query → model answer → structured observation → source repair → repeated delta
```
