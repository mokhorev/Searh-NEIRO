from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .measurement import MeasurementStore, import_ui_tasks_csv

app = typer.Typer(
    help="Search-NEIRO Measurement Core: SQLite queue, evidence store and repeatability metadata."
)
console = Console()


@app.command("init")
def init_database(
    database: Annotated[
        str, typer.Option("--db", help="SQLite database path")
    ] = "outputs/neirosearch.db",
) -> None:
    """Create or migrate the local Measurement Core database."""
    with MeasurementStore(database) as store:
        store.initialize()
        summary = store.summary()
    console.print(f"[bold green]Measurement database ready:[/bold green] {database}")
    console.print_json(json.dumps(summary, ensure_ascii=False))


@app.command("import-ui")
def import_ui(
    input_file: Annotated[
        str, typer.Option("--input", "-i", help="Existing ui_tasks.csv or compatible CSV")
    ] = "outputs/ui_tasks.csv",
    database: Annotated[
        str, typer.Option("--db", help="SQLite database path")
    ] = "outputs/neirosearch.db",
    evidence_root: Annotated[
        str, typer.Option("--evidence-root", help="Directory for immutable evidence artifacts")
    ] = "outputs/evidence",
    run_prefix: Annotated[
        str | None, typer.Option("--run-prefix", help="Optional stable prefix for imported runs")
    ] = None,
) -> None:
    """Import the legacy CSV queue without breaking the existing Streamlit workflow."""
    if not Path(input_file).exists():
        raise typer.BadParameter(f"Input file does not exist: {input_file}")
    stats = import_ui_tasks_csv(
        input_path=input_file,
        database_path=database,
        evidence_root=evidence_root,
        run_prefix=run_prefix,
    )
    console.print("[bold green]Import complete[/bold green]")
    table = Table(show_header=True)
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    for key, value in stats.to_dict().items():
        table.add_row(key, str(value))
    console.print(table)


@app.command("summary")
def summary(
    database: Annotated[
        str, typer.Option("--db", help="SQLite database path")
    ] = "outputs/neirosearch.db",
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Limit summary to one measurement run")
    ] = None,
) -> None:
    """Print database completeness, status and evidence counts."""
    if not Path(database).exists():
        raise typer.BadParameter(f"Database does not exist: {database}. Run init first.")
    with MeasurementStore(database) as store:
        store.initialize()
        payload = store.summary(run_id=run_id)
    console.print_json(json.dumps(payload, ensure_ascii=False, default=str))


if __name__ == "__main__":
    app()
