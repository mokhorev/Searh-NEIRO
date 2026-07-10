from pathlib import Path

from neirosearch.measurement import (
    CaptureMode,
    CapturedAnswer,
    CompanyRecord,
    MeasurementRun,
    MeasurementStore,
    MeasurementTask,
    QueryRecord,
    TaskStatus,
)


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
