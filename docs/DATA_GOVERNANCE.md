# Data governance for Search-NEIRO

Search-NEIRO processes client prompts, AI answers, screenshots, sources and browser-session metadata. Treat these materials as client evidence, not as public repository content.

## Data classes

### PUBLIC

- methodology and generic prompt templates;
- synthetic or fully anonymized fixtures;
- code, schemas and documentation.

### INTERNAL

- provider diagnostics without client identifiers;
- aggregate benchmark results;
- non-secret project decisions.

### CLIENT_CONFIDENTIAL

- company context, unpublished facts, contacts and access details;
- real AI answers tied to a client;
- screenshots, MHTML/HAR/DOM excerpts;
- reviews, HR material or legal documents collected for an audit;
- before/after evidence and repair backlog.

### SECRET

- API keys, cookies, browser profiles, OAuth tokens and passwords;
- session exports and authentication artifacts.

## Storage rules

- Keep CLIENT_CONFIDENTIAL and SECRET data outside Git history.
- Use `outputs/`, `browser_profile/`, `client_data/` or another ignored local directory.
- Store cloud evidence only in access-controlled client/project folders.
- Do not put cookies, tokens or browser-profile archives into Google Drive unless encrypted and explicitly required.
- Evidence filenames should use stable IDs rather than personal names when practical.

## Evidence integrity

- Preserve the raw answer and prompt.
- Record capture date, provider, mode, attempt and available geo/session metadata.
- Generate SHA-256 for answer and evidence files.
- Derived observations must reference the task/evidence that supports them.
- Never silently overwrite a prior observation; create a new event or version.

## Redaction before sharing

Remove or replace:

- personal email, phone and addresses not already public business data;
- account names, cookies, tokens and session IDs;
- private client comments and unpublished financial/legal details;
- browser chrome that reveals unrelated tabs, profiles or notifications.

## Retention

Suggested default unless a client agreement says otherwise:

- raw browser/session evidence: 90 days after final report;
- verified audit evidence and delta: 12 months;
- anonymized benchmark labels: retain while useful;
- secrets: never retain in reports or memory events.

Deletion must include local outputs, cloud copies and exports where feasible.

## MEMORY_ROAD rule

A memory event stores the minimum useful fact plus provenance. It must not copy secrets or unnecessary personal data. `raw_ai_claim` is not promoted to verified memory without a source, repeat, manual check or client confirmation.

## Public fixtures

Real answers may enter `tests/fixtures` only after anonymization and review. Prefer synthetic names/domains and remove URLs that expose a client.
