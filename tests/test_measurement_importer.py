from pathlib import Path

from neirosearch.measurement import MeasurementStore, import_ui_tasks_csv


def write_sample(source: Path, answer: str) -> None:
    source.write_text(
        "brand;industry;region;competitors;provider_id;provider_label;model;"
        "prompt_id;prompt;answer;citations;notes\n"
        "Альфа;ремонт;Москва;Бета;chatgpt_web;ChatGPT;web/manual;1;Кого выбрать для ремонта?;"
        f"{answer};https://example.test;manual\n",
        encoding="utf-8-sig",
    )


def test_import_ui_tasks_and_evidence_is_idempotent_and_versioned(tmp_path: Path) -> None:
    source = tmp_path / "ui_tasks.csv"
    write_sample(source, "Стоит рассмотреть Альфа. Также рекомендуют Бета.")
    database = tmp_path / "measurement.db"
    evidence = tmp_path / "evidence"

    first = import_ui_tasks_csv(
        input_path=source,
        database_path=database,
        evidence_root=evidence,
    )
    second = import_ui_tasks_csv(
        input_path=source,
        database_path=database,
        evidence_root=evidence,
    )

    assert first.companies == 1
    assert first.tasks == 1
    assert first.answers == 1
    assert first.evidence_items == 3
    assert second.tasks == 1
    assert len(list(evidence.rglob("answer.md"))) == 1

    write_sample(source, "Альфа упомянута, но для сложной задачи лучше Бета.")
    third = import_ui_tasks_csv(
        input_path=source,
        database_path=database,
        evidence_root=evidence,
    )
    assert third.answers == 1
    assert len(list(evidence.rglob("answer.md"))) == 2

    with MeasurementStore(database) as store:
        store.initialize()
        summary = store.summary()
    assert summary["runs"] == 1
    assert summary["answers"] == 1
    assert summary["evidence_items"] == 6
