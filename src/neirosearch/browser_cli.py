from __future__ import annotations

import subprocess
import sys
from typing import Annotated

import typer
from rich.console import Console

from .browser.combinator import PROVIDER_LABELS, find_local_browser, open_login_pages, run_pending_tasks

app = typer.Typer(help="Видимый браузерный автокомбайн Searh-NEIRO.")
console = Console()

DEFAULT_PROVIDERS = "chatgpt_web,qwen_web,deepseek_web,gigachat_web,perplexity_web"


def parse_provider_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.command("install")
def install_browser() -> None:
    """Legacy helper: install Playwright Chromium only if local Chrome/Edge is not found."""
    local_browser = find_local_browser()
    if local_browser:
        console.print(f"[green]Найден локальный браузер:[/green] {local_browser}")
        console.print("Playwright Chromium отдельно скачивать не нужно.")
        return
    console.print("[yellow]Локальный Chrome/Edge не найден. Пробую установить Playwright Chromium...[/yellow]")
    raise SystemExit(subprocess.call([sys.executable, "-m", "playwright", "install", "chromium"]))


@app.command("login")
def login(
    providers: Annotated[str, typer.Option("--providers", "-p", help="Провайдеры через запятую")] = DEFAULT_PROVIDERS,
) -> None:
    """Open selected AI services in a persistent browser profile so you can log in once."""
    provider_ids = parse_provider_ids(providers)
    console.print("[bold]Открою страницы для входа:[/bold]")
    for pid in provider_ids:
        console.print(f"- {PROVIDER_LABELS.get(pid, pid)}")
    open_login_pages(provider_ids)


@app.command("run")
def run(
    providers: Annotated[str, typer.Option("--providers", "-p", help="Провайдеры через запятую. Пусто = все поддержанные")] = "",
    limit: Annotated[int, typer.Option("--limit", "-n", help="Сколько незаполненных задач пройти за один запуск")] = 3,
    delay: Annotated[int, typer.Option("--delay", help="Пауза между запросами, секунд")] = 10,
    timeout: Annotated[int, typer.Option("--timeout", help="Сколько ждать ответ, секунд")] = 90,
) -> None:
    """Run a small visible browser batch over pending tasks from outputs/ui_tasks.csv."""
    provider_ids = parse_provider_ids(providers) if providers else None
    result = run_pending_tasks(
        providers=provider_ids,
        limit=limit,
        delay_sec=delay,
        answer_timeout_sec=timeout,
    )
    console.print(f"[bold]Обработано:[/bold] {result.processed}")
    console.print(f"[green]Сохранено:[/green] {result.saved}")
    console.print(f"[red]Ошибок:[/red] {result.failed}")
    if result.logs:
        console.print("[bold]Лог:[/bold]")
        for line in result.logs:
            console.print(f"- {line}")


if __name__ == "__main__":
    app()
