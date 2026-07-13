from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, Iterable

from .models import (
    AnswerObservation,
    CapturedAnswer,
    CompanyRecord,
    EvidenceItem,
    MeasurementRun,
    MeasurementTask,
    MemoryEvent,
    QueryRecord,
    utc_now,
)

SCHEMA_VERSION = 1


class UnsupportedSchemaVersionError(RuntimeError):
    """Raised when a database was created by a newer unsupported schema."""


Migration = Callable[[sqlite3.Connection], None]


SCHEMA_V1_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT '',
    region TEXT NOT NULL DEFAULT '',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queries (
    query_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    prompt_id TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL,
    intent_class TEXT NOT NULL,
    critical INTEGER NOT NULL DEFAULT 0,
    needs_repeat INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    query_id TEXT NOT NULL REFERENCES queries(query_id) ON DELETE CASCADE,
    provider_id TEXT NOT NULL,
    provider_label TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    attempt INTEGER NOT NULL DEFAULT 1,
    capture_mode TEXT NOT NULL,
    web_mode TEXT NOT NULL,
    geo TEXT NOT NULL DEFAULT '',
    personalization TEXT NOT NULL DEFAULT 'unknown',
    session_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_code TEXT,
    error_message TEXT NOT NULL DEFAULT '',
    raw_path TEXT NOT NULL DEFAULT '',
    evidence_path TEXT NOT NULL DEFAULT '',
    answer_sha256 TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(run_id, query_id, provider_id, attempt)
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE REFERENCES tasks(task_id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    citations_json TEXT NOT NULL DEFAULT '[]',
    captured_at TEXT NOT NULL,
    answer_sha256 TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS observations (
    task_id TEXT PRIMARY KEY REFERENCES tasks(task_id) ON DELETE CASCADE,
    observation_json TEXT NOT NULL,
    signal_level TEXT NOT NULL,
    requires_manual_review INTEGER NOT NULL,
    analyzer_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path_or_url TEXT NOT NULL,
    sha256 TEXT NOT NULL DEFAULT '',
    captured_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memory_events (
    event_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL DEFAULT '',
    raw_path TEXT NOT NULL DEFAULT '',
    event_json TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    supersedes_event_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_queries_company ON queries(company_id);
CREATE INDEX IF NOT EXISTS idx_runs_company ON runs(company_id);
CREATE INDEX IF NOT EXISTS idx_tasks_run_status ON tasks(run_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_provider ON tasks(provider_id);
CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence_items(task_id);
CREATE INDEX IF NOT EXISTS idx_memory_company_time ON memory_events(company_id, occurred_at);
"""


def _execute_sql_statements(connection: sqlite3.Connection, script: str) -> None:
    for statement in script.split(";"):
        if sql := statement.strip():
            connection.execute(sql)


def _migrate_to_v1(connection: sqlite3.Connection) -> None:
    _execute_sql_statements(connection, SCHEMA_V1_SQL)


MIGRATIONS: dict[int, Migration] = {
    1: _migrate_to_v1,
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class MeasurementStore:
    def __init__(self, path: str | Path = "outputs/neirosearch.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")

    def __enter__(self) -> "MeasurementStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.connection.close()

    def _read_schema_version(self) -> int:
        table = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'"
        ).fetchone()
        if table is None:
            return 0

        row = self.connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            return 0

        raw_version = str(row["value"])
        try:
            version = int(raw_version)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid database schema version: {raw_version!r}"
            ) from exc
        if version < 0:
            raise RuntimeError(f"Invalid database schema version: {version}")
        return version

    def initialize(self) -> None:
        current_version = self._read_schema_version()
        if current_version > SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                "Database schema version "
                f"{current_version} is newer than supported version {SCHEMA_VERSION}; "
                "upgrade Search-NEIRO before opening this database."
            )
        self.connection.execute("PRAGMA journal_mode = WAL")
        if current_version == SCHEMA_VERSION:
            return

        pending_versions = list(range(current_version + 1, SCHEMA_VERSION + 1))
        missing_versions = [version for version in pending_versions if version not in MIGRATIONS]
        if missing_versions:
            missing = ", ".join(str(version) for version in missing_versions)
            raise RuntimeError(f"Missing database migrations for schema version(s): {missing}")

        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for version in pending_versions:
                MIGRATIONS[version](self.connection)
                self.connection.execute(
                    "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(version),),
                )
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def upsert_company(self, company: CompanyRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO companies(
                company_id, brand, industry, region, aliases_json, metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                brand=excluded.brand,
                industry=excluded.industry,
                region=excluded.region,
                aliases_json=excluded.aliases_json,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
            """,
            (
                company.company_id,
                company.brand,
                company.industry,
                company.region,
                _json(company.aliases),
                _json(company.metadata),
                _iso(company.created_at),
                _iso(company.updated_at),
            ),
        )

    def upsert_query(self, query: QueryRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO queries(
                query_id, company_id, prompt_id, prompt, intent_class, critical, needs_repeat,
                metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(query_id) DO UPDATE SET
                prompt_id=excluded.prompt_id,
                prompt=excluded.prompt,
                intent_class=excluded.intent_class,
                critical=excluded.critical,
                needs_repeat=excluded.needs_repeat,
                metadata_json=excluded.metadata_json
            """,
            (
                query.query_id,
                query.company_id,
                query.prompt_id,
                query.prompt,
                query.intent_class.value,
                int(query.critical),
                int(query.needs_repeat),
                _json(query.metadata),
                _iso(query.created_at),
            ),
        )

    def upsert_run(self, run: MeasurementRun) -> None:
        self.connection.execute(
            """
            INSERT INTO runs(run_id, company_id, status, started_at, completed_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                completed_at=excluded.completed_at,
                metadata_json=excluded.metadata_json
            """,
            (
                run.run_id,
                run.company_id,
                run.status.value,
                _iso(run.started_at),
                _iso(run.completed_at),
                _json(run.metadata),
            ),
        )

    def upsert_task(self, task: MeasurementTask) -> None:
        self.connection.execute(
            """
            INSERT INTO tasks(
                task_id, run_id, query_id, provider_id, provider_label, model, attempt,
                capture_mode, web_mode, geo, personalization, session_id, status, started_at,
                finished_at, error_code, error_message, raw_path, evidence_path, answer_sha256,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                status=excluded.status,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                error_code=excluded.error_code,
                error_message=excluded.error_message,
                raw_path=excluded.raw_path,
                evidence_path=excluded.evidence_path,
                answer_sha256=excluded.answer_sha256,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
            """,
            (
                task.task_id,
                task.run_id,
                task.query_id,
                task.provider_id,
                task.provider_label,
                task.model,
                task.attempt,
                task.capture_mode.value,
                task.web_mode.value,
                task.geo,
                task.personalization,
                task.session_id,
                task.status.value,
                _iso(task.started_at),
                _iso(task.finished_at),
                task.error_code.value if task.error_code else None,
                task.error_message,
                task.raw_path,
                task.evidence_path,
                task.answer_sha256,
                _json(task.metadata),
                _iso(task.created_at),
                _iso(task.updated_at),
            ),
        )

    def store_answer(self, answer: CapturedAnswer) -> None:
        self.connection.execute(
            """
            INSERT INTO answers(
                answer_id, task_id, answer_text, citations_json, captured_at, answer_sha256,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                answer_text=excluded.answer_text,
                citations_json=excluded.citations_json,
                captured_at=excluded.captured_at,
                answer_sha256=excluded.answer_sha256,
                metadata_json=excluded.metadata_json
            """,
            (
                answer.answer_id,
                answer.task_id,
                answer.text,
                _json(answer.citations),
                _iso(answer.captured_at),
                answer.answer_sha256,
                _json(answer.metadata),
            ),
        )

    def store_observation(self, observation: AnswerObservation) -> None:
        self.connection.execute(
            """
            INSERT INTO observations(
                task_id, observation_json, signal_level, requires_manual_review,
                analyzer_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                observation_json=excluded.observation_json,
                signal_level=excluded.signal_level,
                requires_manual_review=excluded.requires_manual_review,
                analyzer_version=excluded.analyzer_version,
                created_at=excluded.created_at
            """,
            (
                observation.task_id,
                observation.model_dump_json(),
                observation.signal_level.value,
                int(observation.requires_manual_review),
                observation.analyzer_version,
                _iso(observation.created_at),
            ),
        )

    def add_evidence(self, item: EvidenceItem) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO evidence_items(
                evidence_id, task_id, kind, path_or_url, sha256, captured_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.evidence_id,
                item.task_id,
                item.kind.value,
                item.path_or_url,
                item.sha256,
                _iso(item.captured_at),
                _json(item.metadata),
            ),
        )

    def add_memory_event(self, event: MemoryEvent) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO memory_events(
                event_id, project_id, company_id, source_type, model, query, raw_path,
                event_json, verification_status, occurred_at, valid_from, valid_to,
                supersedes_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.project_id,
                event.company_id,
                event.source_type,
                event.model,
                event.query,
                event.raw_path,
                event.model_dump_json(),
                event.verification_status.value,
                _iso(event.occurred_at),
                _iso(event.valid_from),
                _iso(event.valid_to),
                event.supersedes_event_id,
            ),
        )

    def commit(self) -> None:
        self.connection.commit()

    def scalar(self, query: str, parameters: Iterable[Any] = ()) -> int:
        row = self.connection.execute(query, tuple(parameters)).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def summary(self, run_id: str | None = None) -> dict[str, Any]:
        task_where = " WHERE run_id = ?" if run_id else ""
        task_params: tuple[Any, ...] = (run_id,) if run_id else ()
        answer_where = (
            " WHERE task_id IN (SELECT task_id FROM tasks WHERE run_id = ?)" if run_id else ""
        )
        evidence_where = (
            " WHERE task_id IN (SELECT task_id FROM tasks WHERE run_id = ?)" if run_id else ""
        )
        summary: dict[str, Any] = {
            "database": str(self.path),
            "schema_version": SCHEMA_VERSION,
            "companies": self.scalar("SELECT COUNT(*) FROM companies"),
            "queries": self.scalar("SELECT COUNT(*) FROM queries"),
            "runs": self.scalar("SELECT COUNT(*) FROM runs"),
            "tasks": self.scalar(f"SELECT COUNT(*) FROM tasks{task_where}", task_params),
            "answers": self.scalar(f"SELECT COUNT(*) FROM answers{answer_where}", task_params),
            "evidence_items": self.scalar(
                f"SELECT COUNT(*) FROM evidence_items{evidence_where}", task_params
            ),
            "manual_review": self.scalar(
                "SELECT COUNT(*) FROM observations WHERE requires_manual_review = 1"
                + (
                    " AND task_id IN (SELECT task_id FROM tasks WHERE run_id = ?)"
                    if run_id
                    else ""
                ),
                task_params,
            ),
            "generated_at": _iso(utc_now()),
        }
        status_rows = self.connection.execute(
            f"SELECT status, COUNT(*) AS count FROM tasks{task_where} GROUP BY status",
            task_params,
        ).fetchall()
        summary["task_statuses"] = {row["status"]: row["count"] for row in status_rows}
        provider_rows = self.connection.execute(
            f"SELECT provider_id, COUNT(*) AS count FROM tasks{task_where} GROUP BY provider_id",
            task_params,
        ).fetchall()
        summary["providers"] = {row["provider_id"]: row["count"] for row in provider_rows}
        return summary
