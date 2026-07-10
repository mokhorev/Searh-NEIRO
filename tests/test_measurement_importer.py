from pathlib import Path

from neirosearch.measurement import MeasurementStore, import_ui_tasks_csv


def test_import_ui_tasks_and_evidence_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "ui_tasks.csv"
    source.write_text(
        "brand;industry;region;competitors;provider_id;provider_label;model;"
        "prompt_id;prompt;answer;citations;notes\n"
        "Альфа;ремонт;Москва;Бета;chatgpt_web;ChatGPT;web/manual;1;Кого выбрать для ремонта?;"
        "Стоит рассмотреть Альфа. Также рекомендуют Бета.;https://example.test;manual\n",
        encoding="utf-8-sig",
    )
    database = tmp_path / "measurement.db"
    evidence = tmp_path / "evidence"

    first = import_ui_tasks_csv(
        input_path=source,
        database_path=database,
        evidence_root=evidence,
        run_prefix="test_run",
    )
    second = import_ui_tasks_csv(
        input_path=source,
        database_path=database,
        evidence_root=evidence,
        run_prefix="test_run",
    )

    assert first.companies == 1
    assert first.tasks == 1
    assert first.answers == 1
    assert first.evidence_items == 3
    assert second.tasks == 1
    assert list(evidence.rglob("answer.md"))
    assert len(list(evidence.rglob("answer.md"))) == 1

    with MeasurementStore(database) as store:
        store.initialize()
        summary = store.summary()
    assert summary["answers"] == 1
    assert summary["evidence_items"] == 3
