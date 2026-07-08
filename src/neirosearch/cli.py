from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .config import DEFAULT_CONFIG, filter_provider_configs, load_config
from .openserp import openserp_search
from .prompts import DEFAULT_SYSTEM, load_prompts
from .providers import build_provider, is_configured
from .reports import write_all_reports

app = typer.Typer(help="Searh-NEIRO: probe multiple AI systems and audit brand visibility.")
console = Console()


@app.command("providers")
def list_providers(
    config: Annotated[str, typer.Option("--config", "-c", help="Path to providers.yaml")] = str(DEFAULT_CONFIG),
) -> None:
    """Show configured providers and whether required env vars are present."""
    load_dotenv()
    data = load_config(config)
    table = Table(title="Configured AI providers")
    table.add_column("ID")
    table.add_column("Label")
    table.add_column("Type")
    table.add_column("Model")
    table.add_column("Market")
    table.add_column("Ready")
    table.add_column("Reason")
    for cfg in data["providers"]:
        ready, reason = is_configured(cfg)
        table.add_row(
            str(cfg.get("id")),
            str(cfg.get("label", "")),
            str(cfg.get("type", "")),
            str(cfg.get("model") or cfg.get("model_env") or ""),
            str(cfg.get("market", "")),
            "yes" if ready else "no",
            reason or "",
        )
    console.print(table)


@app.command("run")
def run_probe(
    brand: Annotated[str, typer.Option("--brand", "-b", help="Brand/company to audit")],
    industry: Annotated[str, typer.Option("--industry", "-i", help="Service/product niche")],
    region: Annotated[str, typer.Option("--region", "-r", help="City/region/country")] = "Россия",
    competitors: Annotated[str, typer.Option("--competitors", help="Comma-separated competitor names")] = "",
    provider_ids: Annotated[str, typer.Option("--providers", "-p", help="Comma-separated provider IDs. Empty = all ready providers")] = "",
    prompts_file: Annotated[str | None, typer.Option("--prompts", help="Prompt file with {brand}, {industry}, {region}")] = None,
    config: Annotated[str, typer.Option("--config", "-c")] = str(DEFAULT_CONFIG),
    output: Annotated[str, typer.Option("--output", "-o", help="Output directory")] = "outputs/latest",
    timeout: Annotated[int, typer.Option("--timeout", help="HTTP timeout per request, seconds")] = 90,
    include_not_ready: Annotated[bool, typer.Option("--include-not-ready", help="Write errors for providers without keys")] = False,
) -> None:
    """Run prompts against selected LLM providers and write JSONL/CSV/Markdown reports."""
    load_dotenv()
    data = load_config(config)
    selected = [item.strip() for item in provider_ids.split(",") if item.strip()]
    provider_cfgs = filter_provider_configs(data["providers"], selected or None)
    prompts = load_prompts(prompts_file, brand=brand, industry=industry, region=region)
    competitor_list = [item.strip() for item in competitors.split(",") if item.strip()]

    console.print(f"[bold]Brand:[/bold] {brand}")
    console.print(f"[bold]Industry:[/bold] {industry}")
    console.print(f"[bold]Region:[/bold] {region}")
    console.print(f"[bold]Prompts:[/bold] {len(prompts)}")

    results = []
    system = DEFAULT_SYSTEM

    for cfg in provider_cfgs:
        ready, reason = is_configured(cfg)
        provider_id = cfg.get("id")
        if not ready and not include_not_ready:
            console.print(f"[yellow]skip[/yellow] {provider_id}: {reason}")
            continue
        provider = build_provider(cfg)
        for prompt in prompts:
            console.print(f"[cyan]ask[/cyan] {provider_id}: {prompt[:80]}")
            if ready:
                result = provider.ask(prompt, system=system, timeout=timeout)
            else:
                from .models import ProviderResult

                result = ProviderResult(
                    provider_id=str(cfg.get("id")),
                    provider_label=str(cfg.get("label", cfg.get("id"))),
                    model=str(cfg.get("model", "")),
                    prompt=prompt,
                    ok=False,
                    error=reason,
                )
            results.append(result)
            if result.ok:
                console.print(f"[green]ok[/green] {provider_id}: {len(result.answer)} chars")
            else:
                console.print(f"[red]error[/red] {provider_id}: {result.error}")

    paths = write_all_reports(results, Path(output), brand=brand, competitors=competitor_list)
    console.print("[bold green]Reports written:[/bold green]")
    for path in paths:
        console.print(f"- {path}")


@app.command("search")
def search_web(
    query: Annotated[str, typer.Argument(help="Search query")],
    engines: Annotated[str, typer.Option("--engines", "-e")] = "yandex,bing,duckduckgo,google",
    limit: Annotated[int, typer.Option("--limit", "-n")] = 10,
    lang: Annotated[str, typer.Option("--lang")] = "RU",
    region: Annotated[str, typer.Option("--region")] = "RU",
) -> None:
    """Run an optional OpenSERP search and print JSON."""
    load_dotenv()
    data = openserp_search(query=query, engines=engines, limit=limit, lang=lang, region=region)
    console.print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
