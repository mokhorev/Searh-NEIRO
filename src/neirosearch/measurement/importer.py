from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .evidence import write_answer_evidence
from .models import (
    CaptureMode,
    CompanyRecord,
    MeasurementRun,
    MeasurementTask,
    QueryRecord,
    TaskStatus,
    WebMode,
    stable_id,
    utc_now,
)
from .normalize import build_observation, infer_intent
from .store import MeasurementStore


@dataclass(slots=True)
class ImportStats:
    companies: int = 0
    runs: int = 0
    queries: int = 0
    tasks: int = 0
    answers: int = 0
    evidence_items: int = 0
    observations: int = 0
    skipped_rows: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "companies": self.companies,
            "runs": self.runs,
            "queries": self.queries,
            "tasks": self.tasks,
            "answers": self.answers,
            "evidence_items": self.evidence_items,
            "observations": self.observations,
            "skipped_rows": self.skipped_rows,
        }


def read_rows(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return [
            {str(key): str(value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle, dialect=dialect)
        ]


def parse_list(value: str) -> list[str]:
    normalized = value.replace("\n", ",").replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def parse_attempt(value: str) -> int:
    try:
        return max(1, int(value.strip()))
    except (TypeError, ValueError, AttributeError):
        return 1


def detect_capture_mode(row: dict[str, str]) -> CaptureMode:
    notes = row.get("notes", "").casefold()
    model = row.get("model", "").casefold()
    if "auto_browser" in notes or "browser" in notes:
        return CaptureMode.ASSISTED_BROWSER
    if "web/manual" in model or row.get("provider_id", "").endswith("_web"):
        return CaptureMode.MANUAL_WEB
    if model:
        return CaptureMode.API
    return CaptureMode.IMPORTED


def import_ui_tasks_csv(
    *,
    input_path: str | Path,
    database_path: str | Path = "outputs/neirosearch.db",
    evidence_root: str | Path = "outputs/evidence",
    run_prefix: str | None = None,
) -> ImportStats:
    source = Path(input_path)
    rows = read_rows(source)
    run_prefix = run_prefix or f"import_{source.stem}"
    stats = ImportStats()
    seen_companies: set[str] = set()
    seen_runs: set[str] = set()
    seen_queries: set[str] = set()
    runs_by_id: dict[str, MeasurementRun] = {}
    run_has_pending: dict[str, bool] = {}

    with MeasurementStore(database_path) as store:
        store.initialize()
        for row_number, row in enumerate(rows, start=2):
            brand = row.get("brand", "").strip()
            prompt = row.get("prompt", "").strip()
            provider_id = row.get("provider_id", "").strip() or "manual"
            if not brand or not prompt:
                stats.skipped_rows += 1
                continue

            company_id = row.get("company_id", "").strip() or stable_id(
                "company", brand, row.get("region", ""), row.get("industry", "")
            )
            run_id = row.get("run_id", "").strip() or stable_id(
                "run", run_prefix, company_id
            )
            prompt_id = row.get("prompt_id", "").strip()
            query_id = row.get("query_id", "").strip() or stable_id(
                "query", company_id, prompt_id, prompt
            )
            attempt = parse_attempt(row.get("attempt", ""))
            task_id = row.get("task_id", "").strip() or stable_id(
                "task", run_id, query_id, provider_id, attempt
            )
            competitors = parse_list(row.get("competitors", ""))
            citations = parse_list(row.get("citations", ""))
            answer_text = row.get("answer", "").strip()

            company = CompanyRecord(
                company_id=company_id,
                brand=brand,
                industry=row.get("industry", ""),
                region=row.get("region", ""),
                metadata={"import_source": str(source)},
            )
            query = QueryRecord(
                query_id=query_id,
                company_id=company_id,
                prompt_id=prompt_id,
                prompt=prompt,
                intent_class=infer_intent(prompt, brand=brand),
                critical=row.get("critical", "").casefold() in {"1", "true", "yes", "да"},
                needs_repeat=row.get("needs_repeat", "").casefold()
                in {"1", "true", "yes", "да"},
                metadata={"import_row": row_number},
            )
            run = MeasurementRun(
                run_id=run_id,
                company_id=company_id,
                status=TaskStatus.RUNNING,
                metadata={"import_source": str(source), "run_prefix": run_prefix},
            )
            task = MeasurementTask(
                task_id=task_id,
                run_id=run_id,
                query_id=query_id,
                provider_id=provider_id,
                provider_label=row.get("provider_label", "") or provider_id,
                model=row.get("model", ""),
                attempt=attempt,
                capture_mode=detect_capture_mode(row),
                web_mode=WebMode(row.get("web_mode", "unknown"))
                if row.get("web_mode", "unknown") in {item.value for item in WebMode}
                else WebMode.UNKNOWN,
                geo=row.get("geo", "") or row.get("region", ""),
                personalization=row.get("personalization", "unknown") or "unknown",
                session_id=row.get("session_id", ""),
                status=TaskStatus.CAPTURED if answer_text else TaskStatus.PENDING,
                finished_at=utc_now() if answer_text else None,
                metadata={"notes": row.get("notes", ""), "import_row": row_number},
            )

            runs_by_id.setdefault(run_id, run)
            run_has_pending[run_id] = run_has_pending.get(run_id, False) or not bool(
                answer_text
            )

            store.upsert_company(company)
            store.upsert_run(run)
            store.upsert_query(query)
            store.upsert_task(task)
            stats.tasks += 1
            if company_id not in seen_companies:
                seen_companies.add(company_id)
                stats.companies += 1
            if run_id not in seen_runs:
                seen_runs.add(run_id)
                stats.runs += 1
            if query_id not in seen_queries:
                seen_queries.add(query_id)
                stats.queries += 1

            if not answer_text:
                continue

            captured, evidence_items = write_answer_evidence(
                root=evidence_root,
                company=company,
                query=query,
                task=task,
                answer_text=answer_text,
                citations=citations,
                extra_metadata={
                    "captured_at_note": row.get("captured_at", ""),
                    "source_file": str(source),
                    "source_row": row_number,
                },
            )
            task.answer_sha256 = captured.answer_sha256
            task.evidence_path = str(Path(evidence_items[0].path_or_url).parent)
            task.raw_path = evidence_items[0].path_or_url
            task.updated_at = utc_now()
            store.upsert_task(task)
            store.store_answer(captured)
            for item in evidence_items:
                store.add_evidence(item)
            observation = build_observation(
                task_id=task_id,
                answer=answer_text,
                brand=brand,
                competitors=competitors,
                citations=citations,
            )
            store.store_observation(observation)
            stats.answers += 1
            stats.evidence_items += len(evidence_items)
            stats.observations += 1

        for run_id, run in runs_by_id.items():
            if run_has_pending.get(run_id, False):
                run.status = TaskStatus.RUNNING
                run.completed_at = None
            else:
                run.status = TaskStatus.CAPTURED
                run.completed_at = utc_now()
            store.upsert_run(run)
        store.commit()
    return stats
