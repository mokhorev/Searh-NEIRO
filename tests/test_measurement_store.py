import sqlite3
from pathlib import Path

import pytest

from neirosearch.measurement import (
    CapturedAnswer,
    CaptureMode,
    CompanyRecord,
    MeasurementRun,
    MeasurementStore,
    MeasurementTask,
    QueryRecord,
    TaskStatus,
)
from neirosearch.measurement.store import SCHEMA_VERSION, UnsupportedSchemaVersionError

EXPECTED_TABLES = {
    "answers",
    "companies",
    "evidence_items",
    "memory_events",
    "observations",
    "queries",
    "runs",
    "schema_meta",
    "tasks",
}


def schema_version(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
    assert row is not None
    return str(row[0])


def table_names(database: Path) -> set[str]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def journal_mode(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        row = connection.execute("PRAGMA journal_mode").fetchone()
    assert row is not None
    return str(row[0])


def create_versioned_database(database: Path, version: int) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?)",
            (str(version),),
        )
        connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel(value) VALUES('unchanged')")


def test_initialize_new_empty_database_at_version_one(tmp_path: Path) -> None:
    database = tmp_path / "new.db"

    with MeasurementStore(database) as store:
        store.initialize()

    assert schema_version(database) == str(SCHEMA_VERSION) == "1"
    assert EXPECTED_TABLES <= table_names(database)


def test_initialize_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "idempotent.db"
    with MeasurementStore(database) as store:
        store.initialize()
        store.connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        store.connection.execute("INSERT INTO sentinel(value) VALUES('kept')")
        store.commit()
        schema_before = store.connection.execute(
            "SELECT name, sql FROM sqlite_master ORDER BY name"
        ).fetchall()
        store.initialize()
        schema_after = store.connection.execute(
            "SELECT name, sql FROM sqlite_master ORDER BY name"
        ).fetchall()
        sentinel = store.connection.execute("SELECT value FROM sentinel").fetchone()

    assert schema_after == schema_before
    assert sentinel is not None and sentinel[0] == "kept"


def test_initialize_preserves_existing_version_one(tmp_path: Path) -> None:
    database = tmp_path / "existing-v1.db"
    with MeasurementStore(database) as store:
        store.initialize()

    with MeasurementStore(database) as store:
        store.initialize()
        stored_version = store.connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
        changes = store.connection.total_changes

    assert stored_version is not None and stored_version[0] == "1"
    assert changes == 0


def test_initialize_rejects_newer_schema_version(tmp_path: Path) -> None:
    database = tmp_path / "future.db"
    create_versioned_database(database, SCHEMA_VERSION + 1)

    with pytest.raises(
        UnsupportedSchemaVersionError,
        match=r"version 2 is newer than supported version 1",
    ):
        with MeasurementStore(database) as store:
            store.initialize()

    assert schema_version(database) == "2"


def test_newer_schema_error_leaves_database_unchanged(tmp_path: Path) -> None:
    database = tmp_path / "future-unchanged.db"
    create_versioned_database(database, SCHEMA_VERSION + 1)
    before_tables = table_names(database)
    before_journal_mode = journal_mode(database)

    with pytest.raises(UnsupportedSchemaVersionError):
        with MeasurementStore(database) as store:
            store.initialize()

    with sqlite3.connect(database) as connection:
        metadata = connection.execute(
            "SELECT key, value FROM schema_meta ORDER BY key"
        ).fetchall()
        sentinel = connection.execute("SELECT value FROM sentinel").fetchall()

    assert table_names(database) == before_tables == {"schema_meta", "sentinel"}
    assert journal_mode(database) == before_journal_mode == "delete"
    assert metadata == [("schema_version", "2")]
    assert sentinel == [("unchanged",)]


def test_store_roundtrip(tmp_path: Path) -> None:
    database = tmp_path / "measurement.db"
    with MeasurementStore(database) as store:
        store.initialize()
        store.upsert_company(CompanyRecord(company_id="company_1", brand="Альфа"))
        store.upsert_query(
            QueryRecord(query_id="query_1", company_id="company_1", prompt="Кого выбрать?")
        )
        store.upsert_run(MeasurementRun(run_id="run_1", company_id="company_1"))
        store.upsert_task(
            MeasurementTask(
                task_id="task_1",
                run_id="run_1",
                query_id="query_1",
                provider_id="manual",
                capture_mode=CaptureMode.MANUAL_WEB,
                status=TaskStatus.CAPTURED,
            )
        )
        store.store_answer(
            CapturedAnswer(
                task_id="task_1",
                text="Ответ с достаточной длиной.",
                answer_sha256="hash",
            )
        )
        store.commit()
        summary = store.summary(run_id="run_1")

    assert summary["companies"] == 1
    assert summary["queries"] == 1
    assert summary["tasks"] == 1
    assert summary["answers"] == 1
