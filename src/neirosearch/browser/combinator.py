from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ..task_status import (
    STATUS_OK,
    STATUS_PENDING,
    STATUS_RETRY,
    STATUS_RUNNING,
    append_note,
    create_run_log_path,
    ensure_task_status_columns,
    increment_attempts,
    now_ts,
    parse_float,
    status_for_row,
    write_log_line,
)

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - handled at runtime
    sync_playwright = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TASKS_PATH = PROJECT_ROOT / "outputs" / "ui_tasks.csv"
LOGS_DIR = PROJECT_ROOT / "outputs" / "logs"
PROFILE_DIR = PROJECT_ROOT / "browser_profile"
CSV_SEP = ";"

PROVIDER_URLS = {
    "chatgpt_web": "https://chatgpt.com/",
    "gemini_web": "https://gemini.google.com/",
    "qwen_web": "https://chat.qwen.ai/",
    "gigachat_web": "https://giga.chat/",
    "perplexity_web": "https://www.perplexity.ai/",
    "deepseek_web": "https://chat.deepseek.com/",
    "grok_web": "https://grok.com/",
}

PROVIDER_LABELS = {
    "chatgpt_web": "ChatGPT",
    "gemini_web": "Gemini",
    "qwen_web": "Qwen",
    "gigachat_web": "GigaChat",
    "perplexity_web": "Perplexity",
    "deepseek_web": "DeepSeek",
    "grok_web": "Grok",
}

COMMON_INPUT_SELECTORS = [
    "#prompt-textarea",
    "textarea:not([disabled])",
    "div[contenteditable='true']",
    "[contenteditable='true']",
    "[role='textbox']",
    "div.ProseMirror",
]

PROVIDER_INPUT_SELECTORS = {
    "gemini_web": [
        "rich-textarea div.ql-editor",
        "div.ql-editor[contenteditable='true']",
        "div[aria-label*='Enter a prompt']",
        "div[aria-label*='Введите запрос']",
        "div[contenteditable='true'][role='textbox']",
        "[role='textbox']",
        "textarea:not([disabled])",
    ],
    "gigachat_web": [
        "textarea[placeholder*='Спрос']",
        "textarea[placeholder*='Напишите']",
        "textarea[placeholder*='Введите']",
        "textarea[placeholder*='сообщение']",
        "textarea[placeholder*='Сообщение']",
        "[data-testid*='chat-input']",
        "[data-testid*='textarea']",
        "[data-testid*='prompt']",
        "[class*='textarea'] textarea",
        "[class*='input'] textarea",
        "form textarea",
        "div[contenteditable='true'][data-lexical-editor='true']",
        "div[contenteditable='true']",
        "[role='textbox']",
    ],
    "grok_web": [
        "textarea[placeholder*='Ask Grok']",
        "textarea[placeholder*='Ask']",
        "textarea[placeholder*='Спрос']",
        "[data-testid*='composer'] textarea",
        "[data-testid*='input'] textarea",
        "div[contenteditable='true']",
        "[contenteditable='true']",
        "[role='textbox']",
        "form textarea",
    ],
    "perplexity_web": [
        "textarea[placeholder*='Ask']",
        "textarea[placeholder*='Follow']",
        "textarea[placeholder*='Спрос']",
        "[data-testid='search-input']",
        "[data-testid*='query']",
        "[contenteditable='true']",
        "[role='textbox']",
        "form textarea",
    ],
}

COMMON_SEND_SELECTORS = [
    "button[data-testid='send-button']",
    "button[aria-label*='Send']",
    "button[aria-label*='send']",
    "button[aria-label*='Отправ']",
    "button[title*='Send']",
    "button[title*='Отправ']",
    "button[type='submit']",
]

PROVIDER_SEND_SELECTORS = {
    "gemini_web": [
        "button[aria-label*='Send message']",
        "button[aria-label*='Submit']",
        "button[aria-label*='Отправить']",
        "button[aria-label*='Отправ']",
        "button.send-button",
        "button[data-testid*='send']",
        "button[type='submit']",
    ],
    "gigachat_web": [
        "button[aria-label*='Отправ']",
        "button[aria-label*='отправ']",
        "button[title*='Отправ']",
        "button[data-testid*='send']",
        "button[class*='send']",
        "form button[type='submit']",
        "button[type='submit']",
    ],
    "grok_web": [
        "button[aria-label*='Submit']",
        "button[aria-label*='Send']",
        "button[aria-label*='Отправ']",
        "button[data-testid*='send']",
        "button[type='submit']",
    ],
    "perplexity_web": [
        "button[aria-label*='Submit']",
        "button[aria-label*='Send']",
        "button[data-testid*='submit']",
        "button[data-testid*='send']",
        "form button[type='submit']",
        "button[type='submit']",
    ],
}

ANSWER_SELECTORS = {
    "chatgpt_web": ["div[data-message-author-role='assistant']", "article"],
    "perplexity_web": ["[data-testid='answer']", "main article", ".prose", "main"],
    "deepseek_web": [".ds-markdown", ".markdown", "main"],
    "qwen_web": [".markdown", ".prose", "main"],
    "gemini_web": ["message-content", "model-response", ".model-response-text", ".markdown", "main"],
    "gigachat_web": ["[data-testid*='assistant']", "[class*='assistant']", "[class*='message']", ".markdown", "main"],
    "grok_web": ["[data-testid*='message']", "article", ".markdown", ".prose", "main"],
}

COMMON_WINDOWS_BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

INCOMPLETE_MARKERS = [
    "думаю",
    "thinking",
    "generating",
    "ответ формируется",
    "continue generating",
    "продолжить генерацию",
]


@dataclass(slots=True)
class BrowserRunResult:
    processed: int = 0
    saved: int = 0
    failed: int = 0
    retried: int = 0
    logs: list[str] = field(default_factory=list)
    log_callback: Callable[[str], None] | None = None
    run_id: str = ""
    log_path: Path | None = None

    def add(self, message: str) -> None:
        self.logs.append(message)
        write_log_line(self.log_path, message)
        if self.log_callback:
            self.log_callback(message)


def require_playwright() -> None:
    if sync_playwright is None:
        raise RuntimeError("Playwright не установлен. Выполни: pip install playwright")


def find_local_browser() -> str | None:
    env_path = os.getenv("NEIRO_BROWSER_PATH") or os.getenv("BROWSER_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    for candidate in COMMON_WINDOWS_BROWSERS:
        if Path(candidate).exists():
            return candidate
    return None


def launch_visible_context(playwright: Any, profile_dir: Path):
    """Launch visible Chrome/Edge first, then fall back to Playwright browsers."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    executable = find_local_browser()
    common_args = ["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"]
    if executable:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=False, executable_path=executable, args=common_args
        )
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch_persistent_context(
                str(profile_dir), headless=False, channel=channel, args=common_args
            )
        except Exception:
            continue
    return playwright.chromium.launch_persistent_context(str(profile_dir), headless=False, args=common_args)


def read_tasks(path: Path = TASKS_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()
    return ensure_task_status_columns(df)


def save_tasks(df: pd.DataFrame, path: Path = TASKS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_task_status_columns(df).to_csv(path, sep=CSV_SEP, index=False, encoding="utf-8-sig")


def pending_task_indexes(df: pd.DataFrame, providers: list[str] | None = None) -> list[int]:
    df = ensure_task_status_columns(df)
    if df.empty or "answer" not in df.columns:
        return []
    providers_set = set(providers or [])
    indexes: list[int] = []
    for idx, row in df.iterrows():
        if str(row.get("answer", "")).strip():
            continue
        provider_id = str(row.get("provider_id", ""))
        if provider_id not in PROVIDER_URLS:
            continue
        if providers_set and provider_id not in providers_set:
            continue
        status = status_for_row(row)
        if status not in {STATUS_PENDING, STATUS_RETRY}:
            continue
        indexes.append(int(idx))
    return indexes


def pending_task_diagnostics(
    df: pd.DataFrame,
    providers: list[str] | None = None,
    tasks_path: Path = TASKS_PATH,
) -> list[str]:
    """Explain why no tasks are runnable without hiding the queue location."""
    path = tasks_path.resolve()
    if not tasks_path.exists():
        return [
            f"Файл очереди не найден: {path}",
            "Создай задачи в разделе «Поиск» основного интерфейса.",
        ]
    if df.empty:
        return [f"Файл очереди пуст: {path}", "Создай очередь заново в разделе «Поиск»."]

    work = ensure_task_status_columns(df)
    requested = set(providers or [])
    unsupported_requested = sorted(requested - set(PROVIDER_URLS))
    messages: list[str] = [f"Файл очереди: {path}"]
    if unsupported_requested:
        messages.append(f"Не поддерживаются автокомбайном: {', '.join(unsupported_requested)}.")
    if "provider_id" not in work.columns:
        messages.append("В очереди отсутствует обязательный столбец provider_id.")
        return messages

    provider_ids = work["provider_id"].astype(str).str.strip()
    selected_provider_ids = requested & set(PROVIDER_URLS) if requested else set(PROVIDER_URLS)
    selected = work[provider_ids.isin(selected_provider_ids)]
    if selected.empty:
        available = sorted({value for value in provider_ids if value})
        requested_text = ", ".join(sorted(requested)) if requested else "поддерживаемых провайдеров"
        messages.append(f"В очереди нет задач для: {requested_text}.")
        if available:
            messages.append(f"Провайдеры в очереди: {', '.join(available)}.")
        return messages

    selected = ensure_task_status_columns(selected)
    answered = int(selected["answer"].astype(str).str.strip().ne("").sum())
    pending = int((selected["status"] == STATUS_PENDING).sum())
    retry = int((selected["status"] == STATUS_RETRY).sum())
    running = int((selected["status"] == STATUS_RUNNING).sum())
    other = len(selected) - answered - pending - retry - running
    messages.append(
        "Для выбранных провайдеров: "
        f"всего {len(selected)}, готово {answered}, pending {pending}, retry {retry}, "
        f"running {running}, прочие статусы {max(0, other)}."
    )
    if pending or retry:
        messages.append(
            "Задачи pending/retry есть, но они не прошли фильтры запуска; "
            "проверь provider_id и данные промпта."
        )
    elif answered == len(selected):
        messages.append("Все задачи выбранных провайдеров уже имеют ответы.")
    else:
        messages.append(
            "Нет задач со статусом pending или retry. "
            "Running, error и skipped автоматически не запускаются."
        )
    return messages


def open_login_pages(
    providers: list[str],
    profile_dir: Path = PROFILE_DIR,
    wait_for_enter: bool = True,
    keep_open_sec: int = 180,
    log_callback: Callable[[str], None] | None = None,
) -> list[str]:
    require_playwright()
    logs: list[str] = []

    def log(message: str) -> None:
        logs.append(message)
        if log_callback:
            log_callback(message)

    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:  # type: ignore[operator]
        browser = launch_visible_context(p, profile_dir)
        for provider in providers:
            url = PROVIDER_URLS.get(provider)
            if url:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                log(f"Открыта страница входа: {PROVIDER_LABELS.get(provider, provider)}")
        if wait_for_enter:
            print("Войдите в нужные аккаунты в открытом браузере.")
            input("Когда закончите вход, нажмите Enter здесь. Браузер будет закрыт, входы сохранятся в browser_profile. ")
        else:
            log(f"Окно входа открыто на {keep_open_sec} секунд. Войдите в аккаунты в видимом браузере.")
            time.sleep(max(10, keep_open_sec))
        browser.close()
        log("Браузер входа закрыт. Профиль сохранён в browser_profile.")
    return logs


def selectors_for(provider_id: str, provider_map: dict[str, list[str]], common: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for selector in provider_map.get(provider_id, []) + common:
        if selector not in seen:
            result.append(selector)
            seen.add(selector)
    return result


def find_input(page: Any, provider_id: str = ""):
    for selector in selectors_for(provider_id, PROVIDER_INPUT_SELECTORS, COMMON_INPUT_SELECTORS):
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                candidate = locator.last
                candidate.wait_for(state="visible", timeout=5000)
                if candidate.is_enabled(timeout=1000):
                    return candidate
        except Exception:
            continue
    return None


def submit_prompt(page: Any, prompt: str, provider_id: str = "") -> bool:
    box = find_input(page, provider_id=provider_id)
    if box is None:
        return False
    box.click(timeout=5000)
    try:
        box.fill(prompt, timeout=5000)
    except Exception:
        page.keyboard.press("Control+A")
        page.keyboard.insert_text(prompt)
    time.sleep(0.8)
    for selector in selectors_for(provider_id, PROVIDER_SEND_SELECTORS, COMMON_SEND_SELECTORS):
        try:
            button = page.locator(selector).last
            if button.count() > 0 and button.is_enabled(timeout=1000):
                button.click(timeout=3000)
                return True
        except Exception:
            continue
    try:
        page.keyboard.press("Enter")
        return True
    except Exception:
        return False


def extract_answer(page: Any, provider_id: str) -> str:
    selectors = ANSWER_SELECTORS.get(provider_id, []) + ["main", "body"]
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            if count <= 0:
                continue
            text = locator.nth(count - 1).inner_text(timeout=5000).strip()
            if len(text) >= 30:
                return text
        except Exception:
            continue
    return ""


def looks_incomplete(text: str) -> bool:
    value = text.casefold().strip()
    if not value:
        return True
    if any(marker in value for marker in INCOMPLETE_MARKERS):
        return True
    return len(value) < 120 and "\n" not in value


def wait_for_answer(
    page: Any,
    provider_id: str,
    timeout_sec: int = 240,
    min_answer_chars: int = 300,
    stable_rounds_required: int = 8,
) -> str:
    """Wait until answer text stops growing and is long enough for an audit prompt."""
    started = time.time()
    last_text = ""
    stable_rounds = 0
    while time.time() - started < timeout_sec:
        text = extract_answer(page, provider_id)
        if len(text) > len(last_text):
            last_text = text
            stable_rounds = 0
        elif text and text == last_text:
            stable_rounds += 1

        enough_text = len(last_text.strip()) >= min_answer_chars
        stable_enough = stable_rounds >= stable_rounds_required
        if last_text and enough_text and stable_enough and not looks_incomplete(last_text):
            return last_text
        time.sleep(2)
    return last_text


def _mark_task_started(df: pd.DataFrame, idx: int, run_id: str) -> None:
    df.at[idx, "status"] = STATUS_RUNNING
    df.at[idx, "attempts"] = increment_attempts(df.at[idx, "attempts"] if "attempts" in df.columns else "0")
    df.at[idx, "last_run_at"] = now_ts()
    df.at[idx, "run_id"] = run_id
    df.at[idx, "error"] = ""


def _mark_task_ok(df: pd.DataFrame, idx: int, answer: str, started_at: float, run_id: str) -> None:
    df.at[idx, "answer"] = answer
    df.at[idx, "status"] = STATUS_OK
    df.at[idx, "error"] = ""
    df.at[idx, "run_id"] = run_id
    df.at[idx, "duration_sec"] = round(time.time() - started_at, 1)
    df.at[idx, "last_run_at"] = now_ts()
    df.at[idx, "notes"] = append_note(df.at[idx, "notes"], f"auto_browser; {now_ts()}")


def _mark_task_retry(df: pd.DataFrame, idx: int, message: str, started_at: float, run_id: str) -> None:
    df.at[idx, "status"] = STATUS_RETRY
    df.at[idx, "error"] = message
    df.at[idx, "run_id"] = run_id
    df.at[idx, "duration_sec"] = round(time.time() - started_at, 1)
    df.at[idx, "last_run_at"] = now_ts()
    df.at[idx, "notes"] = append_note(df.at[idx, "notes"], "auto_browser_retry")


def run_pending_tasks(
    providers: list[str] | None = None,
    limit: int = 3,
    delay_sec: int = 8,
    answer_timeout_sec: int = 240,
    profile_dir: Path = PROFILE_DIR,
    tasks_path: Path = TASKS_PATH,
    log_callback: Callable[[str], None] | None = None,
) -> BrowserRunResult:
    run_id, log_path = create_run_log_path(LOGS_DIR)
    result = BrowserRunResult(log_callback=log_callback, run_id=run_id, log_path=log_path)
    result.add(f"Старт автокомбайна: run_id={run_id}")
    df = read_tasks(tasks_path)
    indexes = pending_task_indexes(df, providers=providers)
    if limit > 0:
        indexes = indexes[:limit]
    if not indexes:
        result.add("Нет задач, готовых к запуску.")
        for message in pending_task_diagnostics(df, providers=providers, tasks_path=tasks_path):
            result.add(message)
        return result

    require_playwright()
    result.add(f"В очереди к запуску: {len(indexes)} задач. Лог: {log_path}")
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:  # type: ignore[operator]
        context = launch_visible_context(p, profile_dir)
        page = context.new_page()
        for idx in indexes:
            row = df.loc[idx]
            provider_id = str(row.get("provider_id", ""))
            label = PROVIDER_LABELS.get(provider_id, provider_id)
            url = PROVIDER_URLS.get(provider_id)
            prompt = str(row.get("prompt", ""))
            started_at = time.time()
            result.processed += 1
            if not url or not prompt:
                message = "нет URL или промпта"
                _mark_task_retry(df, idx, message, started_at, run_id)
                save_tasks(df, tasks_path)
                result.failed += 1
                result.retried += 1
                result.add(f"Пропуск #{idx}: {message}.")
                continue
            try:
                _mark_task_started(df, idx, run_id)
                save_tasks(df, tasks_path)
                result.add(f"Открываю {label}: задача #{idx}.")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(4)
                ok = submit_prompt(page, prompt, provider_id=provider_id)
                if not ok:
                    message = "не найдено поле ввода"
                    _mark_task_retry(df, idx, message, started_at, run_id)
                    save_tasks(df, tasks_path)
                    result.failed += 1
                    result.retried += 1
                    result.add(f"{label}: {message}. Проверь вход и селекторы, затем заполни вручную в очереди.")
                    continue
                result.add(f"{label}: промпт отправлен, жду полный ответ до {answer_timeout_sec} сек.")
                answer = wait_for_answer(page, provider_id, timeout_sec=answer_timeout_sec)
                if answer:
                    _mark_task_ok(df, idx, answer, started_at, run_id)
                    save_tasks(df, tasks_path)
                    result.saved += 1
                    short_note = "" if len(answer) >= 300 else " Возможно, ответ короткий — проверь вручную."
                    duration = parse_float(df.at[idx, "duration_sec"]) or 0
                    result.add(f"{label}: ответ сохранён, {len(answer)} символов, {duration:.1f} сек.{short_note}")
                else:
                    message = "ответ не удалось прочитать автоматически"
                    _mark_task_retry(df, idx, message, started_at, run_id)
                    save_tasks(df, tasks_path)
                    result.failed += 1
                    result.retried += 1
                    result.add(f"{label}: {message}.")
                time.sleep(delay_sec)
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                _mark_task_retry(df, idx, message, started_at, run_id)
                save_tasks(df, tasks_path)
                result.failed += 1
                result.retried += 1
                result.add(f"{label}: ошибка {message}")
        time.sleep(5)
        context.close()
    result.add(f"Финиш автокомбайна: обработано={result.processed}, сохранено={result.saved}, на повтор={result.retried}, ошибок={result.failed}")
    return result
