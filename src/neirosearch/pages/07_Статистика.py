from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from neirosearch.task_status import (
        STATUS_OK,
        STATUS_PENDING,
        STATUS_RETRY,
        STATUS_RUNNING,
        duplicate_task_mask,
        ensure_task_status_columns,
        parse_float,
        status_label_for_row,
    )
except ImportError:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from neirosearch.task_status import (
        STATUS_OK,
        STATUS_PENDING,
        STATUS_RETRY,
        STATUS_RUNNING,
        duplicate_task_mask,
        ensure_task_status_columns,
        parse_float,
        status_label_for_row,
    )

TASKS_PATH = Path("outputs/ui_tasks.csv")
LOGS_DIR = Path("outputs/logs")
CSV_SEP = ";"


def read_tasks() -> pd.DataFrame:
    if not TASKS_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(TASKS_PATH, sep=None, engine="python", encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()
    return ensure_task_status_columns(df)


def duration_value(value: object) -> float | None:
    return parse_float(value)


def provider_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    work["status_norm"] = work.apply(lambda row: row.get("status", ""), axis=1)
    work["duration_num"] = work["duration_sec"].apply(duration_value)
    rows = []
    for provider, group in work.groupby("provider_label", dropna=False):
        rows.append(
            {
                "нейросеть": provider or "—",
                "всего": len(group),
                "OK": int((group["status"] == STATUS_OK).sum()),
                "на повтор": int((group["status"] == STATUS_RETRY).sum()),
                "выполняется": int((group["status"] == STATUS_RUNNING).sum()),
                "не начато": int((group["status"] == STATUS_PENDING).sum()),
                "ошибок/сообщений": int(group["error"].astype(str).str.strip().ne("").sum()),
                "среднее время, сек": round(float(group["duration_num"].dropna().mean()), 1)
                if group["duration_num"].dropna().size
                else "",
                "средние попытки": round(pd.to_numeric(group["attempts"], errors="coerce").fillna(0).mean(), 2),
            }
        )
    return pd.DataFrame(rows).sort_values(["OK", "на повтор", "всего"], ascending=[False, False, False])


def company_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for brand, group in df.groupby("brand", dropna=False):
        rows.append(
            {
                "компания": brand or "—",
                "всего": len(group),
                "OK": int((group["status"] == STATUS_OK).sum()),
                "на повтор": int((group["status"] == STATUS_RETRY).sum()),
                "не начато": int((group["status"] == STATUS_PENDING).sum()),
                "готовность": f"{int((group['status'] == STATUS_OK).sum())} / {len(group)}",
            }
        )
    return pd.DataFrame(rows).sort_values(["OK", "всего"], ascending=[False, False])


def latest_logs(limit: int = 5) -> list[Path]:
    if not LOGS_DIR.exists():
        return []
    return sorted(LOGS_DIR.glob("browser_run_*.log"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def main() -> None:
    st.set_page_config(page_title="Searh-NEIRO — Статистика", layout="wide")
    st.title("Статистика массовой проверки")
    st.caption("Контроль очереди перед большим прогоном: статусы, повторы, ошибки, дубли и журналы запусков.")

    df = read_tasks()
    if df.empty:
        st.warning("Очередь пустая. Сначала создай задачи в основном UI.")
        return

    total = len(df)
    ok = int((df["status"] == STATUS_OK).sum())
    retry = int((df["status"] == STATUS_RETRY).sum())
    running = int((df["status"] == STATUS_RUNNING).sum())
    pending = int((df["status"] == STATUS_PENDING).sum())
    errors = int(df["error"].astype(str).str.strip().ne("").sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Всего", total)
    c2.metric("OK", ok)
    c3.metric("На повтор", retry)
    c4.metric("Выполняется", running)
    c5.metric("Не начато", pending)
    c6.metric("Ошибок", errors)

    st.subheader("Статистика по нейросетям")
    st.dataframe(provider_stats(df), hide_index=True, use_container_width=True)

    st.subheader("Статистика по компаниям")
    st.dataframe(company_stats(df), hide_index=True, use_container_width=True)

    st.subheader("Очередь со статусами")
    view = df.copy()
    view["статус"] = view.apply(status_label_for_row, axis=1)
    cols = [
        "статус",
        "brand",
        "provider_label",
        "prompt_id",
        "attempts",
        "duration_sec",
        "last_run_at",
        "error",
        "prompt",
    ]
    st.dataframe(view[[col for col in cols if col in view.columns]], hide_index=True, height=360, use_container_width=True)

    st.subheader("Проверка дублей")
    dup_mask = duplicate_task_mask(df)
    dup_count = int(dup_mask.sum()) if not dup_mask.empty else 0
    if dup_count:
        st.warning(f"Найдено потенциальных дублей: {dup_count}")
        dup_cols = ["brand", "provider_label", "prompt_id", "prompt", "status", "answer", "notes"]
        st.dataframe(df.loc[dup_mask, [col for col in dup_cols if col in df.columns]], hide_index=True, height=260, use_container_width=True)
    else:
        st.success("Дубли по связке компания + нейросеть + номер промпта + текст промпта не найдены.")

    st.subheader("Последние журналы автокомбайна")
    logs = latest_logs()
    if not logs:
        st.info("Журналов пока нет. Они появятся после запуска автокомбайна.")
    for path in logs:
        with st.expander(str(path.resolve())):
            try:
                st.code(path.read_text(encoding="utf-8")[-8000:], language="text")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Не удалось прочитать лог: {exc}")

    st.caption(f"Файл очереди: {TASKS_PATH.resolve()}")
    st.caption(f"Папка логов: {LOGS_DIR.resolve()}")


if __name__ == "__main__":
    main()
