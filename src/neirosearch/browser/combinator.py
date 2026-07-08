from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - handled at runtime
    sync_playwright = None  # type: ignore[assignment]

TASKS_PATH = Path("outputs/ui_tasks.csv")
PROFILE_DIR = Path("browser_profile")
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

INPUT_SELECTORS = [
    "#prompt-textarea",
    "textarea",
    "div[contenteditable='true']",
    "[role='textbox']",
    "div.ProseMirror",
]

SEND_SELECTORS = [
    "button[data-testid='send-button']",
    "button[aria-label*='Send']",
    "button[aria-label*='Отправ']",
    "button[type='submit']",
]

ANSWER_SELECTORS = {
    "chatgpt_web": ["div[data-message-author-role='assistant']", "article"],
    "perplexity_web": ["[data-testid='answer']", "main article", ".prose"],
    "deepseek_web": [".ds-markdown", ".markdown", "main"],
    "qwen_web": [".markdown", ".prose", "main"],
    "gemini_web": ["message-content", ".markdown", "main"],
    "gigachat_web": [".markdown", ".message", "main"],
    "grok_web": ["article", ".markdown", "main"],
}

COMMON_WINDOWS_BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


@dataclass(slots=True)
class BrowserRunResult:
    processed: int = 0
    saved: int = 0
    failed: int = 0
    logs: list[str] | None = None

    def add(self, message: str) -> None:
        if self.logs is None:
            self.logs = []
        self.logs.append(message)


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
    """Launch visible browser using installed Chrome/Edge first.

    This avoids `playwright install chromium`, which can fail behind corporate or antivirus
    certificate inspection. If no installed browser is found, it falls back to Playwright's bundled
    browser and prints a clear error if that browser is missing.
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    executable = find_local_browser()
    common_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
    ]
    if executable:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            executable_path=executable,
            args=common_args,
        )
    try:
        return playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            channel="chrome",
            args=common_args,
        )
    except Exception:
        try:
            return playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                channel="msedge",
                args=common_args,
            )
        except Exception:
            return playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                args=common_args,
            )


def read_tasks(path: Path = TASKS_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()


def save_tasks(df: pd.DataFrame, path: Path = TASKS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=CSV_SEP, index=False, encoding="utf-8-sig")


def pending_task_indexes(df: pd.DataFrame, providers: list[str] | None = None) -> list[int]:
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
        indexes.append(int(idx))
    return indexes


def open_login_pages(providers: list[str], profile_dir: Path = PROFILE_DIR) -> None:
    require_playwright()
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:  # type: ignore[operator]
        browser = launch_visible_context(p, profile_dir)
        for provider in providers:
            url = PROVIDER_URLS.get(provider)
            if url:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("Войдите в нужные аккаунты в открытом браузере.")
        input("Когда закончите вход, нажмите Enter здесь. Браузер будет закрыт, входы сохранятся в browser_profile. ")
        browser.close()


def find_input(page: Any):
    for selector in INPUT_SELECTORS:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                candidate = locator.last
                candidate.wait_for(state="visible", timeout=5000)
                return candidate
        except Exception:
            continue
    return None


def submit_prompt(page: Any, prompt: str) -> bool:
    box = find_input(page)
    if box is None:
        return False
    box.click(timeout=5000)
    try:
        box.fill(prompt, timeout=5000)
    except Exception:
        page.keyboard.press("Control+A")
        page.keyboard.insert_text(prompt)
    time.sleep(0.5)
    for selector in SEND_SELECTORS:
        try:
            button = page.locator(selector).last
            if button.count() > 0:
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


def wait_for_answer(page: Any, provider_id: str, timeout_sec: int = 90) -> str:
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
        if last_text and stable_rounds >= 4:
            return last_text
        time.sleep(2)
    return last_text


def run_pending_tasks(
    providers: list[str] | None = None,
    limit: int = 3,
    delay_sec: int = 8,
    answer_timeout_sec: int = 90,
    profile_dir: Path = PROFILE_DIR,
    tasks_path: Path = TASKS_PATH,
) -> BrowserRunResult:
    require_playwright()
    result = BrowserRunResult(logs=[])
    df = read_tasks(tasks_path)
    indexes = pending_task_indexes(df, providers=providers)
    if limit > 0:
        indexes = indexes[:limit]
    if not indexes:
        result.add("Нет незаполненных задач для выбранных нейросетей.")
        return result

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
            result.processed += 1
            if not url or not prompt:
                result.failed += 1
                result.add(f"Пропуск #{idx}: нет URL или промпта.")
                continue
            try:
                result.add(f"Открываю {label}: задача #{idx}.")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)
                ok = submit_prompt(page, prompt)
                if not ok:
                    result.failed += 1
                    result.add(f"{label}: не нашёл поле ввода. Заполни вручную в очереди.")
                    continue
                result.add(f"{label}: промпт отправлен, жду ответ.")
                answer = wait_for_answer(page, provider_id, timeout_sec=answer_timeout_sec)
                if answer:
                    df.at[idx, "answer"] = answer
                    df.at[idx, "notes"] = f"auto_browser; {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    save_tasks(df, tasks_path)
                    result.saved += 1
                    result.add(f"{label}: ответ сохранён, {len(answer)} символов.")
                else:
                    result.failed += 1
                    result.add(f"{label}: ответ не удалось прочитать автоматически.")
                time.sleep(delay_sec)
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.add(f"{label}: ошибка {exc}")
        context.close()
    return result
