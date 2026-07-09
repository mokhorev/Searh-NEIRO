from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_OK = "ok"
STATUS_RETRY = "retry"
STATUS_ERROR = "error"
STATUS_SKIPPED = "skipped"

TASK_STATUS_FIELDNAMES = [
    "status",
    "attempts",
    "error",
    "last_run_at",
    "duration_sec",
    "run_id",
]

STATUS_LABELS = {
    STATUS_PENDING: "⚪ Незаполнено",
    STATUS_RUNNING: "🔵 Выполняется",
    STATUS_OK: "🟢 OK",
    STATUS_RETRY: "🟡 На повтор",
    STATUS_ERROR: "🔴 Ошибка",
    STATUS_SKIPPED: "⚫ Пропуск",
}


_INTERNAL_EMPTY = {"", "nan", "none", "null"}


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_cell(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.casefold() in _INTERNAL_EMPTY else text


def normalize_status(value: Any, answer: Any = "", error: Any = "") -> str:
    raw = normalize_cell(value).casefold()
    answer_text = normalize_cell(answer)
    error_text = normalize_cell(error)
    if answer_text:
        return STATUS_OK
    if raw in {STATUS_PENDING, STATUS_RUNNING, STATUS_OK, STATUS_RETRY, STATUS_ERROR, STATUS_SKIPPED}:
        return raw
    if error_text:
        return STATUS_RETRY
    return STATUS_PENDING


def ensure_task_status_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        result = pd.DataFrame() if df is None else df.copy()
    else:
        result = df.copy()
    for col in TASK_STATUS_FIELDNAMES:
        if col not in result.columns:
            result[col] = ""
    if "answer" not in result.columns:
        result["answer"] = ""
    if "notes" not in result.columns:
        result["notes"] = ""
    if "attempts" in result.columns:
        result["attempts"] = result["attempts"].apply(lambda value: normalize_cell(value) or "0")
    if not result.empty:
        result["status"] = result.apply(
            lambda row: normalize_status(row.get("status", ""), row.get("answer", ""), row.get("error", "")),
            axis=1,
        )
    return result.fillna("")


def status_label(status: Any, answer: Any = "", error: Any = "") -> str:
    normalized = normalize_status(status, answer=answer, error=error)
    return STATUS_LABELS.get(normalized, str(status or ""))


def status_for_row(row: pd.Series) -> str:
    return normalize_status(row.get("status", ""), row.get("answer", ""), row.get("error", ""))


def status_label_for_row(row: pd.Series) -> str:
    return status_label(row.get("status", ""), answer=row.get("answer", ""), error=row.get("error", ""))


def append_note(existing: Any, note: str) -> str:
    existing_text = normalize_cell(existing)
    note_text = normalize_cell(note)
    if not note_text:
        return existing_text
    if not existing_text:
        return note_text
    if note_text in existing_text:
        return existing_text
    return f"{existing_text}; {note_text}"


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or "").replace(",", ".")))
    except Exception:
        return default


def parse_float(value: Any) -> float | None:
    try:
        text = normalize_cell(value).replace(",", ".")
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def increment_attempts(value: Any) -> str:
    return str(parse_int(value) + 1)


def task_identity(row: pd.Series) -> tuple[str, str, str, str]:
    return (
        normalize_cell(row.get("brand", "")).casefold(),
        normalize_cell(row.get("provider_id", "")).casefold(),
        normalize_cell(row.get("prompt_id", "")).casefold(),
        normalize_cell(row.get("prompt", "")).casefold(),
    )


def duplicate_task_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="bool")
    keys = df.apply(task_identity, axis=1)
    return keys.duplicated(keep=False)


def drop_duplicate_tasks(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0
    keys = df.apply(task_identity, axis=1)
    mask = keys.duplicated(keep="first")
    return df.loc[~mask].copy(), int(mask.sum())


def create_run_log_path(output_dir: Path = Path("outputs/logs")) -> tuple[str, Path]:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_id, output_dir / f"browser_run_{run_id}.log"


def write_log_line(path: Path | None, message: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{now_ts()}] {message}\n")
