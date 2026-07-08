from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from .analyzer import analyze_answer, summarize_results
from .manual import MANUAL_PROVIDERS, TASK_FIELDNAMES
from .models import ProviderResult
from .reports import write_all_reports

COMPANY_COLS = ["brand", "industry", "region", "competitors"]
TASKS_PATH = Path("outputs/ui_tasks.csv")
COMPANIES_PATH = Path("inputs/companies.csv")
PROMPTS_PATH = Path("inputs/prompts.txt")
PROVIDERS_PATH = Path("inputs/providers.txt")
CSV_SEP = ";"

PROVIDER_LABELS = {
    "chatgpt_web": "ChatGPT",
    "gemini_web": "Gemini",
    "qwen_web": "Qwen",
    "gigachat_web": "GigaChat",
    "yandexgpt_web": "YandexGPT / Алиса",
    "claude_web": "Claude",
    "perplexity_web": "Perplexity",
    "deepseek_web": "DeepSeek",
    "grok_web": "Grok",
    "kimi_web": "Kimi",
    "glm_web": "GLM / Z.ai",
}

PROVIDER_URLS = {
    "chatgpt_web": "https://chatgpt.com/",
    "gemini_web": "https://gemini.google.com/",
    "qwen_web": "https://chat.qwen.ai/",
    "gigachat_web": "https://giga.chat/",
    "yandexgpt_web": "https://ya.ru/ai/",
    "claude_web": "https://claude.ai/",
    "perplexity_web": "https://www.perplexity.ai/",
    "deepseek_web": "https://chat.deepseek.com/",
    "grok_web": "https://grok.com/",
    "kimi_web": "https://www.kimi.com/",
    "glm_web": "https://chat.z.ai/",
}

DEFAULT_PROMPTS = [
    "Кого посоветуешь для услуги: {industry} в городе {region}? Дай 5 вариантов.",
    "Какие компании чаще всего рекомендуют для {industry} в {region}?",
    "Стоит ли выбирать {brand} для {industry} в {region}? Какие есть альтернативы?",
    "Сравни {brand} с другими компаниями по направлению {industry} в {region}.",
    "Какие плюсы и минусы у {brand} для услуги {industry} в {region}?",
    "Если бы ты выбирал подрядчика для {industry} в {region}, кого бы ты включил в короткий список?",
]


def ensure_files() -> None:
    Path("inputs").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)
    if not COMPANIES_PATH.exists():
        pd.DataFrame(
            [
                {
                    "brand": "В отражении",
                    "industry": "сложное окрашивание волос",
                    "region": "Красноярск",
                    "competitors": "Салон 1,Салон 2",
                }
            ]
        ).to_csv(COMPANIES_PATH, sep=CSV_SEP, index=False, encoding="utf-8-sig")
    if not PROMPTS_PATH.exists():
        PROMPTS_PATH.write_text("\n".join(DEFAULT_PROMPTS), encoding="utf-8")
    if not PROVIDERS_PATH.exists():
        PROVIDERS_PATH.write_text(
            "\n".join(
                [
                    "chatgpt_web",
                    "gemini_web",
                    "qwen_web",
                    "gigachat_web",
                    "perplexity_web",
                    "deepseek_web",
                    "grok_web",
                ]
            ),
            encoding="utf-8",
        )


def read_csv_any(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    except Exception:
        df = pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].fillna("")


def write_csv_excel(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=CSV_SEP, index=False, encoding="utf-8-sig")


def load_companies() -> pd.DataFrame:
    return read_csv_any(COMPANIES_PATH, COMPANY_COLS)


def save_companies(df: pd.DataFrame) -> None:
    df = df[COMPANY_COLS].fillna("")
    df = df[df["brand"].astype(str).str.strip() != ""]
    write_csv_excel(df, COMPANIES_PATH)


def load_prompts_text() -> str:
    return PROMPTS_PATH.read_text(encoding="utf-8") if PROMPTS_PATH.exists() else "\n".join(DEFAULT_PROMPTS)


def save_prompts_text(text: str) -> None:
    PROMPTS_PATH.parent.mkdir(exist_ok=True)
    PROMPTS_PATH.write_text(text.strip() + "\n", encoding="utf-8")


def parse_prompts(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def load_provider_ids() -> list[str]:
    if not PROVIDERS_PATH.exists():
        return ["chatgpt_web", "gemini_web", "qwen_web", "gigachat_web", "perplexity_web"]
    ids = [line.strip() for line in PROVIDERS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [pid for pid in ids if pid in MANUAL_PROVIDERS]


def save_provider_ids(ids: list[str]) -> None:
    PROVIDERS_PATH.write_text("\n".join(ids), encoding="utf-8")


def build_tasks(companies: pd.DataFrame, prompts: list[str], providers: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, company in companies.iterrows():
        brand = str(company.get("brand", "")).strip()
        if not brand:
            continue
        industry = str(company.get("industry", "")).strip()
        region = str(company.get("region", "")).strip()
        competitors = str(company.get("competitors", "")).strip()
        for provider in providers:
            for prompt_id, template in enumerate(prompts, start=1):
                try:
                    prompt = template.format(brand=brand, industry=industry, region=region)
                except Exception:
                    prompt = template
                rows.append(
                    {
                        "brand": brand,
                        "industry": industry,
                        "region": region,
                        "competitors": competitors,
                        "provider_id": provider,
                        "provider_label": PROVIDER_LABELS.get(provider, provider),
                        "model": "web/manual",
                        "prompt_id": prompt_id,
                        "prompt": prompt,
                        "answer": "",
                        "citations": "",
                        "notes": "",
                    }
                )
    return pd.DataFrame(rows, columns=TASK_FIELDNAMES)


def load_tasks() -> pd.DataFrame:
    return read_csv_any(TASKS_PATH, TASK_FIELDNAMES)


def save_tasks(df: pd.DataFrame) -> None:
    for col in TASK_FIELDNAMES:
        if col not in df.columns:
            df[col] = ""
    write_csv_excel(df[TASK_FIELDNAMES].fillna(""), TASKS_PATH)


def task_progress(tasks: pd.DataFrame) -> tuple[int, int, int]:
    total = len(tasks)
    done = int(tasks["answer"].fillna("").astype(str).str.strip().ne("").sum()) if total else 0
    return total, done, total - done


def row_to_result(row: pd.Series) -> ProviderResult:
    citations = [item.strip() for item in str(row.get("citations", "")).split(",") if item.strip()]
    return ProviderResult(
        provider_id=str(row.get("provider_id", "manual")),
        provider_label=str(row.get("provider_label", "Manual")),
        model=str(row.get("model", "web/manual")),
        prompt=str(row.get("prompt", "")),
        ok=True,
        answer=str(row.get("answer", "")),
        citations=citations,
        raw={
            "prompt_id": row.get("prompt_id", ""),
            "industry": row.get("industry", ""),
            "region": row.get("region", ""),
            "notes": row.get("notes", ""),
        },
    )


def split_competitors(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def slugify(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value.strip().lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_") or "company"


def sidebar(tasks: pd.DataFrame) -> str:
    total, done, pending = task_progress(tasks)
    with st.sidebar:
        st.title("Searh-NEIRO")
        st.caption("Локальный кабинет аудита AI-видимости")
        st.metric("Всего задач", total)
        st.metric("Готово", done)
        st.metric("Осталось", pending)
        st.divider()
        return st.radio(
            "Раздел",
            ["Компании", "Промпты", "Нейросети", "Очередь", "По компаниям", "Отчёт"],
            label_visibility="collapsed",
        )


def page_companies() -> None:
    st.header("1. Компании")
    st.caption("Список как в Airtable/Notion: одна строка — одна компания.")
    companies = load_companies()
    edited = st.data_editor(
        companies,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        height=320,
        column_config={
            "brand": st.column_config.TextColumn("Компания", required=True, width="medium"),
            "industry": st.column_config.TextColumn("Ниша / услуга", width="large"),
            "region": st.column_config.TextColumn("Город / регион", width="medium"),
            "competitors": st.column_config.TextColumn("Конкуренты через запятую", width="large"),
        },
    )
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Сохранить компании", type="primary"):
            save_companies(edited)
            st.success("Сохранено")
    with col2:
        st.info("Можно вставлять строки прямо из Excel. Главное: заполнить колонку «Компания».")


def page_prompts() -> None:
    st.header("2. Промпты")
    st.caption("Один промпт на строку. Доступны переменные: {brand}, {industry}, {region}.")
    text = st.text_area("Список промптов", value=load_prompts_text(), height=360)
    if st.button("Сохранить промпты", type="primary"):
        save_prompts_text(text)
        st.success("Промпты сохранены")
    with st.expander("Пример хороших промптов"):
        st.code("\n".join(DEFAULT_PROMPTS), language="text")


def page_providers() -> None:
    st.header("3. Нейросети")
    st.caption("Выбери веб-нейросети, которые тебе реально доступны через браузер/VPN.")
    current = load_provider_ids()
    labels = {pid: f"{PROVIDER_LABELS.get(pid, pid)} ({pid})" for pid in MANUAL_PROVIDERS}
    selected_labels = st.multiselect(
        "Провайдеры",
        options=[labels[pid] for pid in MANUAL_PROVIDERS],
        default=[labels[pid] for pid in current if pid in labels],
    )
    selected = [pid for pid in MANUAL_PROVIDERS if labels[pid] in selected_labels]
    if st.button("Сохранить список нейросетей", type="primary"):
        save_provider_ids(selected)
        st.success("Список сохранён")
    st.subheader("Быстрые ссылки")
    cols = st.columns(3)
    for i, pid in enumerate(selected or current):
        with cols[i % 3]:
            if pid in PROVIDER_URLS:
                st.link_button(PROVIDER_LABELS.get(pid, pid), PROVIDER_URLS[pid])


def page_queue() -> None:
    st.header("4. Очередь задач")
    companies = load_companies()
    prompts = parse_prompts(load_prompts_text())
    providers = load_provider_ids()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Компаний", len(companies))
    with col2:
        st.metric("Промптов", len(prompts))
    with col3:
        st.metric("Нейросетей", len(providers))

    if st.button("Сгенерировать новую очередь", type="primary"):
        tasks = build_tasks(companies, prompts, providers)
        save_tasks(tasks)
        st.success(f"Создано задач: {len(tasks)}")
        st.rerun()

    tasks = load_tasks()
    total, done, pending = task_progress(tasks)
    st.progress(done / total if total else 0)
    st.caption(f"Готово {done} из {total}. Осталось {pending}.")

    if tasks.empty:
        st.warning("Очередь пустая. Нажми «Сгенерировать новую очередь».")
        return

    status = st.selectbox("Показать", ["Остались", "Готовые", "Все"])
    view = tasks.copy()
    is_done = view["answer"].fillna("").astype(str).str.strip().ne("")
    if status == "Остались":
        view = view[~is_done]
    elif status == "Готовые":
        view = view[is_done]

    st.dataframe(
        view[["brand", "provider_label", "prompt_id", "prompt", "answer"]],
        hide_index=False,
        height=260,
        width="stretch",
    )

    pending_tasks = tasks[tasks["answer"].fillna("").astype(str).str.strip().eq("")]
    work_source = pending_tasks if not pending_tasks.empty else tasks
    options = [
        f"{idx} | {row['brand']} | {row['provider_label']} | #{row['prompt_id']} | {str(row['prompt'])[:80]}"
        for idx, row in work_source.iterrows()
    ]
    selected = st.selectbox("Текущая задача", options) if options else None
    if not selected:
        return
    idx = int(str(selected).split(" | ", 1)[0])
    row = tasks.loc[idx]

    st.subheader(f"{row['brand']} → {row['provider_label']}")
    url = PROVIDER_URLS.get(str(row["provider_id"]))
    if url:
        st.link_button(f"Открыть {row['provider_label']}", url)
    st.text_area("Промпт для копирования", value=str(row["prompt"]), height=130, key=f"prompt_{idx}")
    answer = st.text_area("Вставь ответ нейросети", value=str(row.get("answer", "")), height=260, key=f"answer_{idx}")
    citations = st.text_input("Ссылки / цитаты через запятую", value=str(row.get("citations", "")), key=f"citations_{idx}")
    notes = st.text_input("Заметки", value=str(row.get("notes", "")), key=f"notes_{idx}")

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("Сохранить ответ", type="primary"):
            tasks.at[idx, "answer"] = answer
            tasks.at[idx, "citations"] = citations
            tasks.at[idx, "notes"] = notes
            save_tasks(tasks)
            st.success("Ответ сохранён")
            st.rerun()
    with col_clear:
        if st.button("Очистить ответ"):
            tasks.at[idx, "answer"] = ""
            tasks.at[idx, "citations"] = ""
            tasks.at[idx, "notes"] = ""
            save_tasks(tasks)
            st.warning("Ответ очищен")
            st.rerun()


def page_company_view() -> None:
    st.header("5. Вид по каждой компании")
    tasks = load_tasks()
    if tasks.empty:
        st.warning("Очередь пока пустая.")
        return
    companies = sorted(tasks["brand"].dropna().astype(str).unique())
    brand = st.selectbox("Компания", companies)
    data = tasks[tasks["brand"] == brand].copy()
    is_done = data["answer"].fillna("").astype(str).str.strip().ne("")
    col1, col2, col3 = st.columns(3)
    col1.metric("Задач", len(data))
    col2.metric("Ответов", int(is_done.sum()))
    col3.metric("Осталось", int((~is_done).sum()))
    pivot = data.assign(done=is_done).groupby("provider_label")["done"].agg(["sum", "count"]).reset_index()
    pivot["progress"] = pivot["sum"].astype(str) + " / " + pivot["count"].astype(str)
    st.dataframe(pivot[["provider_label", "progress"]], hide_index=True, width="stretch")
    st.dataframe(data[["provider_label", "prompt_id", "prompt", "answer", "notes"]], hide_index=True, height=420, width="stretch")


def page_report() -> None:
    st.header("6. Отчёт")
    tasks = load_tasks()
    answered = tasks[tasks["answer"].fillna("").astype(str).str.strip().ne("")].copy()
    if answered.empty:
        st.warning("Пока нет заполненных ответов.")
        return
    companies = sorted(answered["brand"].dropna().astype(str).unique())
    brand = st.selectbox("Компания для отчёта", companies)
    data = answered[answered["brand"] == brand]
    competitors = split_competitors(str(data["competitors"].iloc[0] if not data.empty else ""))
    results = [row_to_result(row) for _, row in data.iterrows()]
    summary = summarize_results(results, brand=brand, competitors=competitors)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ответов", summary["ok_results"])
    col2.metric("Бренд найден", summary["brand_found"])
    col3.metric("Рекомендован", summary["brand_recommended"])
    col4.metric("Видимость", summary["visibility_rate"])

    rows = []
    for _, row in data.iterrows():
        analysis = analyze_answer(str(row["answer"]), brand, competitors)
        rows.append(
            {
                "provider": row["provider_label"],
                "prompt_id": row["prompt_id"],
                "brand_found": analysis.brand_found,
                "position": analysis.brand_position,
                "role": analysis.role,
                "competitors_found": ", ".join(analysis.competitors_found),
                "prompt": row["prompt"],
                "answer": row["answer"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, height=420, width="stretch")

    if st.button("Сформировать файлы отчёта", type="primary"):
        out_dir = Path("outputs/ui_report") / slugify(brand)
        paths = write_all_reports(results, out_dir, brand=brand, competitors=competitors)
        st.success("Отчёт сформирован")
        for path in paths:
            st.write(str(path))


def render_app() -> None:
    ensure_files()
    st.set_page_config(page_title="Searh-NEIRO", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem;}
        div[data-testid="stMetric"] {background: #f6f8fa; padding: 10px; border-radius: 12px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    tasks = load_tasks()
    page = sidebar(tasks)
    if page == "Компании":
        page_companies()
    elif page == "Промпты":
        page_prompts()
    elif page == "Нейросети":
        page_providers()
    elif page == "Очередь":
        page_queue()
    elif page == "По компаниям":
        page_company_view()
    else:
        page_report()


def main() -> None:
    script = Path(__file__).resolve()
    cmd = [sys.executable, "-m", "streamlit", "run", str(script)]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    render_app()
