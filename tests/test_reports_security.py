import csv
from pathlib import Path

from neirosearch.models import ProviderResult
from neirosearch.reports import excel_safe_text, write_csv


def test_excel_safe_text_blocks_formula_prefixes() -> None:
    assert excel_safe_text('=HYPERLINK("https://evil.test")').startswith("'=")
    assert excel_safe_text("  +cmd").startswith("'  +")
    assert excel_safe_text("normal answer") == "normal answer"


def test_csv_export_sanitizes_llm_answer(tmp_path: Path) -> None:
    result = ProviderResult(
        provider_id="test",
        provider_label="Test",
        model="model",
        prompt="normal prompt",
        ok=True,
        answer='=HYPERLINK("https://evil.test","open")',
    )
    path = write_csv([result], tmp_path, brand="Альфа", competitors=[])
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle, delimiter=";"))
    assert row["answer"].startswith("'=")
