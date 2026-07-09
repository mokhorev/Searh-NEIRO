from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Works both as package entrypoint and as `streamlit run src\neirosearch\ui_app.py`.
try:
    from .analyzer import analyze_answer, summarize_results
    from .browser.combinator import (
        PROVIDER_LABELS as BROWSER_PROVIDER_LABELS,
        PROVIDER_URLS as BROWSER_PROVIDER_URLS,
        open_login_pages,
        run_pending_tasks,
    )
    from .manual import MANUAL_PROVIDERS, TASK_FIELDNAMES
    from .models import ProviderResult
    from .reports import write_all_reports
except ImportError:
    root = Path(__file__).resolve().parents[2]
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from neirosearch.analyzer import analyze_answer, summarize_results
    from neirosearch.browser.combinator import (
        PROVIDER_LABELS as BROWSER_PROVIDER_LABELS,
        PROVIDER_URLS as BROWSER_PROVIDER_URLS,
        open_login_pages,
        run_pending_tasks,
    )
    from neirosearch.manual import MANUAL_PROVIDERS, TASK_FIELDNAMES
    from neirosearch.models import ProviderResult
    from neirosearch.reports import write_all_reports

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
PROVIDER_LABELS.update(BROWSER_PROVIDER_LABELS)

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
PROVIDER_URLS.update(BROWSER_PROVIDER_URLS)

BROWSER_PROVIDERS = list(BROWSER_PROVIDER_URLS.keys())

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
        pd.DataFrame([
            {
                "brand": "В отражении",
                "industry": "сложное окрашивание волос",
                "region": "Красноярск",
                "competitors": "Салон 1,Салон 2",
            }
        ]).to_csv(COMPANIES_PATH, sep=CSV_SEP, index=False, encoding="utf-8-sig")
    if not PROMPTS_PATH.exists():
        PROMPTS_PATH.write_text("\n".join(DEFAULT_PROMPTS), encoding="utf-8")
    if not PROVIDERS_PATH.exists():
        PROVIDERS_PATH.write_text("\n".join(BROWSER_PROVIDERS), encoding="utf-8")


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


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=CSV_SEP, index=False, encoding="utf-8-sig")


def load_companies() -> pd.DataFrame:
    return read_csv_any(COMPANIES_PATH, COMPANY_COLS)


def save_companies(df: pd.DataFrame) -> None:
    df = df[COMPANY_COLS].fillna("")
    df = df[df["brand"].astype(str).str.strip() != ""]
    write_csv(df, COMPANIES_PATH)


def load_prompts_text() -> str:
    return PROMPTS_PATH.read_text(encoding="utf-8") if PROMPTS_PATH.exists() else "\n".join(DEFAULT_PROMPTS)


def save_prompts_text(text: str) -> None:
    PROMPTS_PATH.write_text(text.strip() + "\n", encoding="utf-8")


def parse_prompts(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def load_provider_ids() -> list[str]:
    if not PROVIDERS_PATH.exists():
        return ["chatgpt_web", "gemini_web", "qwen_web", "gigachat_web", "perplexity_web"]
    return [
        line.strip()
        for line in PROVIDERS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() in MANUAL_PROVIDERS
    ]


def save_provider_ids(ids: list[str]) -> None:
    PROVIDERS_PATH.write_text("\n".join(ids), encoding="utf-8")


def build_tasks(companies: pd.DataFrame, prompts: list[str], providers: list[str]) -> pd.DataFrame:
    rows = []
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
                rows.append({
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
                })
    return pd.DataFrame(rows, columns=TASK_FIELDNAMES)


def load_tasks() -> pd.DataFrame:
    return read_csv_any(TASKS_PATH, TASK_FIELDNAMES)


def save_tasks(df: pd.DataFrame) -> None:
    for col in TASK_FIELDNAMES:
        if col not in df.columns:
            df[col] = ""
    write_csv(df[TASK_FIELDNAMES].fillna(""), TASKS_PATH)


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


def selected_company_frame(companies: pd.DataFrame, brand: str) -> pd.DataFrame:
    return companies[companies["brand"].astype(str) == brand].copy()


def provider_multiselect(default_ids: list[str], key: str, only_browser: bool = False) -> list[str]:
    allowed = BROWSER_PROVIDERS if only_browser else MANUAL_PROVIDERS
    labels = {pid: f"{PROVIDER_LABELS.get(pid, pid)} ({pid})" for pid in allowed}
    selected_labels = st.multiselect(
        "Какие нейросети использовать",
        [labels[pid] for pid in allowed],
        default=[labels[pid] for pid in default_ids if pid in labels],
        key=key,
    )
    return [pid for pid in allowed if labels[pid] in selected_labels]


def page_search() -> None:
    st.header("Поиск по нейросетям")
    st.caption("Выбери компанию, вставь промпты, выбери нейросети и нажми «Запустить поиск». Программа создаст очередь запросов и соберёт отчёт по ответам.")

    companies = load_companies()
    if companies.empty:
        st.warning("Сначала добавь компанию в разделе «Компании».")
        return

    brand = st.selectbox("Компания", companies["brand"].astype(str).tolist())
    company = selected_company_frame(companies, brand)
    if company.empty:
        st.warning("Компания не найдена.")
        return
    info = company.iloc[0]
    st.info(f"Ниша: {info['industry']} · Регион: {info['region']} · Конкуренты: {info['competitors']}")

    prompts_text = st.text_area(
        "Промпты поиска — один промпт на строку",
        value=load_prompts_text(),
        height=260,
        help="Можно использовать переменные {brand}, {industry}, {region}.",
    )
    providers = provider_multiselect(load_provider_ids(), key="search_providers")

    col_a, col_b = st.columns([1, 2])
    with col_a:
        replace_company_tasks = st.checkbox("Очистить старые задачи этой компании", value=True)
    with col_b:
        st.write("После запуска переходи в «Очередь» или «Автокомбайн».")

    if st.button("Запустить поиск", type="primary"):
        prompts = parse_prompts(prompts_text)
        if not prompts:
            st.error("Добавь хотя бы один промпт.")
            return
        if not providers:
            st.error("Выбери хотя бы одну нейросеть.")
            return
        save_prompts_text(prompts_text)
        save_provider_ids(providers)
        new_tasks = build_tasks(company, prompts, providers)
        old_tasks = load_tasks()
        if replace_company_tasks and not old_tasks.empty:
            old_tasks = old_tasks[old_tasks["brand"].astype(str) != brand]
        all_tasks = pd.concat([old_tasks, new_tasks], ignore_index=True) if not old_tasks.empty else new_tasks
        save_tasks(all_tasks)
        st.success(f"Поиск создан: {len(new_tasks)} запросов для компании «{brand}».")
        st.session_state["page"] = "Автокомбайн"
        st.rerun()


def page_companies() -> None:
    st.header("Компании")
    st.caption("Одна строка — одна компания. Можно вставлять строки из Excel.")
    edited = st.data_editor(
        load_companies(),
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        height=360,
        column_config={
            "brand": st.column_config.TextColumn("Компания", required=True),
            "industry": st.column_config.TextColumn("Ниша / услуга"),
            "region": st.column_config.TextColumn("Город / регион"),
            "competitors": st.column_config.TextColumn("Конкуренты через запятую"),
        },
    )
    if st.button("Сохранить компании", type="primary"):
        save_companies(edited)
        st.success("Компании сохранены")


def page_prompts() -> None:
    st.header("Промпты")
    text = st.text_area(
        "Один промпт на строку. Переменные: {brand}, {industry}, {region}.",
        value=load_prompts_text(),
        height=360,
    )
    if st.button("Сохранить промпты", type="primary"):
        save_prompts_text(text)
        st.success("Промпты сохранены")
    with st.expander("Примеры"):
        st.code("\n".join(DEFAULT_PROMPTS), language="text")


def page_providers() -> None:
    st.header("Нейросети")
    selected = provider_multiselect(load_provider_ids(), key="provider_settings")
    if st.button("Сохранить список нейросетей", type="primary"):
        save_provider_ids(selected)
        st.success("Список сохранён")
    st.subheader("Быстрые ссылки")
    cols = st.columns(3)
    for i, pid in enumerate(selected or load_provider_ids()):
        with cols[i % 3]:
            if pid in PROVIDER_URLS:
                st.link_button(PROVIDER_LABELS.get(pid, pid), PROVIDER_URLS[pid])


def page_browser() -> None:
    st.header("Автокомбайн")
    st.caption("Работает только через видимый локальный браузер и аккаунты пользователя. Капчи и авторизация не обходятся.")

    tasks = load_tasks()
    total, done, pending = task_progress(tasks)
    c1, c2, c3 = st.columns(3)
    c1.metric("Всего задач", total)
    c2.metric("Ответов", done)
    c3.metric("Осталось", pending)

    default_auto = [pid for pid in load_provider_ids() if pid in BROWSER_PROVIDERS]
    providers = provider_multiselect(default_auto, key="browser_providers", only_browser=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.number_input("Лимит задач", min_value=1, max_value=100, value=1, step=1)
    with col2:
        delay = st.number_input("Задержка между запросами, сек", min_value=0, max_value=120, value=10, step=1)
    with col3:
        timeout = st.number_input("Таймаут ответа, сек", min_value=30, max_value=600, value=120, step=10)

    login_seconds = st.number_input("Сколько держать окно входа открытым, сек", min_value=30, max_value=900, value=180, step=30)
    log_box = st.empty()
    live_logs: list[str] = []

    def ui_log(message: str) -> None:
        live_logs.append(message)
        log_box.code("\n".join(live_logs[-80:]), language="text")

    left, right = st.columns(2)
    with left:
        if st.button("Войти в нейросети", type="secondary"):
            if not providers:
                st.error("Выбери хотя бы одну нейросеть.")
                return
            with st.spinner("Открываю видимый браузер для входа..."):
                try:
                    open_login_pages(
                        providers,
                        wait_for_enter=False,
                        keep_open_sec=int(login_seconds),
                        log_callback=ui_log,
                    )
                    st.success("Окно входа закрыто, профиль сохранён.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Ошибка входа: {exc}")
    with right:
        if st.button("Запустить автокомбайн", type="primary"):
            if not providers:
                st.error("Выбери хотя бы одну нейросеть.")
                return
            with st.spinner("Автокомбайн выполняет очередь в видимом браузере..."):
                try:
                    result = run_pending_tasks(
                        providers=providers,
                        limit=int(limit),
                        delay_sec=int(delay),
                        answer_timeout_sec=int(timeout),
                        log_callback=ui_log,
                    )
                    st.success(f"Готово. Обработано: {result.processed}, сохранено: {result.saved}, ошибок: {result.failed}.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Ошибка автокомбайна: {exc}")

    with st.expander("Команды для ручной проверки"):
        selected_arg = ",".join(providers) if providers else "qwen_web"
        st.code(
            "\n".join([
                f'python -m neirosearch.browser_cli login --providers "{selected_arg}"',
                f'python -m neirosearch.browser_cli run --providers "{selected_arg}" --limit {int(limit)} --delay {int(delay)} --timeout {int(timeout)}',
                'python -m neirosearch.browser_cli run --providers "perplexity_web" --limit 1 --delay 10 --timeout 120',
                'python -m neirosearch.browser_cli run --providers "gigachat_web" --limit 1 --delay 10 --timeout 120',
            ]),
            language="powershell",
        )


def page_queue() -> None:
    st.header("Очередь запросов")
    tasks = load_tasks()
    total, done, pending = task_progress(tasks)
    st.progress(done / total if total else 0)
    st.caption(f"Готово {done} из {total}. Осталось {pending}.")
    if tasks.empty:
        st.warning("Очередь пустая. Открой раздел «Поиск» и нажми «Запустить поиск».")
        return

    pending_tasks = tasks[tasks["answer"].fillna("").astype(str).str.strip().eq("")]
    work_source = pending_tasks if not pending_tasks.empty else tasks
    options = [
        f"{idx} | {row['brand']} | {row['provider_label']} | #{row['prompt_id']} | {str(row['prompt'])[:90]}"
        for idx, row in work_source.iterrows()
    ]
    selected = st.selectbox("Текущий запрос", options)
    idx = int(str(selected).split(" | ", 1)[0])
    row = tasks.loc[idx]
    provider_id = str(row["provider_id"])

    left, right = st.columns([2, 1])
    with left:
        st.subheader(f"{row['brand']} → {row['provider_label']} → вопрос #{row['prompt_id']}")
    with right:
        if provider_id in PROVIDER_URLS:
            st.link_button(f"Открыть {row['provider_label']}", PROVIDER_URLS[provider_id])

    st.text_area("Промпт для копирования", value=str(row["prompt"]), height=130, key=f"prompt_{idx}")
    answer = st.text_area("Вставь ответ нейросети", value=str(row.get("answer", "")), height=280, key=f"answer_{idx}")
    citations = st.text_input("Ссылки / цитаты через запятую", value=str(row.get("citations", "")), key=f"citations_{idx}")
    notes = st.text_input("Заметки", value=str(row.get("notes", "")), key=f"notes_{idx}")

    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("Сохранить ответ", type="primary"):
            tasks.at[idx, "answer"] = answer
            tasks.at[idx, "citations"] = citations
            tasks.at[idx, "notes"] = notes
            save_tasks(tasks)
            st.success("Ответ сохранён")
            st.rerun()
    with c2:
        st.write("После сохранения автоматически откроется следующий незаполненный запрос.")

    st.divider()
    st.dataframe(tasks[["brand", "provider_label", "prompt_id", "prompt", "answer"]], hide_index=True, height=260, use_container_width=True)


def page_company_view() -> None:
    st.header("По компаниям")
    tasks = load_tasks()
    if tasks.empty:
        st.warning("Очередь пустая.")
        return
    brand = st.selectbox("Компания", sorted(tasks["brand"].dropna().astype(str).unique()))
    data = tasks[tasks["brand"] == brand].copy()
    done = data["answer"].fillna("").astype(str).str.strip().ne("")
    c1, c2, c3 = st.columns(3)
    c1.metric("Задач", len(data))
    c2.metric("Ответов", int(done.sum()))
    c3.metric("Осталось", int((~done).sum()))
    pivot = data.assign(done=done).groupby("provider_label")["done"].agg(["sum", "count"]).reset_index()
    pivot["progress"] = pivot["sum"].astype(str) + " / " + pivot["count"].astype(str)
    st.dataframe(pivot[["provider_label", "progress"]], hide_index=True, use_container_width=True)
    st.dataframe(data[["provider_label", "prompt_id", "prompt", "answer", "notes"]], hide_index=True, height=420, use_container_width=True)


def build_report_rows(data: pd.DataFrame, brand: str, competitors: list[str]) -> pd.DataFrame:
    rows = []
    for _, row in data.iterrows():
        analysis = analyze_answer(str(row["answer"]), brand, competitors)
        rows.append({
            "вопрос": int(row["prompt_id"]) if str(row["prompt_id"]).isdigit() else row["prompt_id"],
            "нейросеть": row["provider_label"],
            "бренд найден": "да" if analysis.brand_found else "нет",
            "рекомендован": "да" if analysis.role == "recommended" else "нет",
            "позиция": analysis.brand_position or "",
            "роль": analysis.role,
            "конкуренты": ", ".join(analysis.competitors_found),
            "промпт": row["prompt"],
            "ответ": row["answer"],
        })
    return pd.DataFrame(rows)


def page_report() -> None:
    st.header("Отчёт")
    tasks = load_tasks()
    answered = tasks[tasks["answer"].fillna("").astype(str).str.strip().ne("")].copy()
    if answered.empty:
        st.warning("Пока нет ответов.")
        return
    brand = st.selectbox("Компания", sorted(answered["brand"].dropna().astype(str).unique()))
    data = answered[answered["brand"] == brand].copy()
    competitors = split_competitors(str(data["competitors"].iloc[0] if not data.empty else ""))
    results = [row_to_result(row) for _, row in data.iterrows()]
    summary = summarize_results(results, brand=brand, competitors=competitors)
    report_rows = build_report_rows(data, brand, competitors)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ответов", summary["ok_results"])
    c2.metric("Бренд найден", summary["brand_found"])
    c3.metric("Рекомендован", summary["brand_recommended"])
    c4.metric("Видимость", summary["visibility_rate"])

    st.subheader("Сводка по конкурентам")
    competitor_series = report_rows["конкуренты"].str.split(", ").explode().replace("", pd.NA).dropna()
    if competitor_series.empty:
        st.info("Повторяющиеся конкуренты из заданного списка пока не найдены.")
    else:
        competitor_counts = competitor_series.value_counts().reset_index()
        competitor_counts.columns = ["конкурент", "сколько раз встречается"]
        st.dataframe(competitor_counts, hide_index=True, use_container_width=True)

    st.subheader("Группировка по вопросу")
    grouped = []
    for (prompt_id, prompt), group in data.groupby(["prompt_id", "prompt"], sort=True):
        rows_for_prompt = report_rows[report_rows["вопрос"].astype(str) == str(prompt_id)]
        grouped.append({
            "вопрос": prompt_id,
            "промпт": prompt,
            "ответов": len(group),
            "где бренд найден": ", ".join(rows_for_prompt.loc[rows_for_prompt["бренд найден"] == "да", "нейросеть"].astype(str)),
            "где бренд не найден": ", ".join(rows_for_prompt.loc[rows_for_prompt["бренд найден"] == "нет", "нейросеть"].astype(str)),
            "где рекомендован": ", ".join(rows_for_prompt.loc[rows_for_prompt["рекомендован"] == "да", "нейросеть"].astype(str)),
            "кого советуют вместо": ", ".join(sorted(set(", ".join(rows_for_prompt["конкуренты"].astype(str)).replace(", ,", ",").split(", ")) - {""})),
        })
    st.dataframe(pd.DataFrame(grouped), hide_index=True, height=260, use_container_width=True)

    st.subheader("Сравнение ответов разных нейросетей")
    for (prompt_id, prompt), group in data.groupby(["prompt_id", "prompt"], sort=True):
        with st.expander(f"Вопрос #{prompt_id}: {prompt}"):
            rows_for_prompt = report_rows[report_rows["вопрос"].astype(str) == str(prompt_id)]
            st.dataframe(
                rows_for_prompt[["нейросеть", "бренд найден", "рекомендован", "позиция", "роль", "конкуренты"]],
                hide_index=True,
                use_container_width=True,
            )
            for _, row in group.iterrows():
                st.markdown(f"**{row['provider_label']}**")
                st.write(str(row["answer"])[:4000])

    st.subheader("Полная таблица")
    st.dataframe(report_rows, hide_index=True, height=420, use_container_width=True)

    if st.button("Сформировать файлы отчёта", type="primary"):
        paths = write_all_reports(results, Path("outputs/ui_report") / slugify(brand), brand=brand, competitors=competitors)
        st.success("Отчёт сформирован")
        for path in paths:
            st.write(str(path))


def render_app() -> None:
    ensure_files()
    st.set_page_config(page_title="Searh-NEIRO", layout="wide")
    tasks = load_tasks()
    total, done, pending = task_progress(tasks)
    pages = ["Поиск", "Компании", "Промпты", "Нейросети", "Автокомбайн", "Очередь", "По компаниям", "Отчёт"]
    if "page" not in st.session_state:
        st.session_state["page"] = "Поиск"
    with st.sidebar:
        st.title("Searh-NEIRO")
        st.caption("Кабинет аудита AI-видимости")
        st.metric("Всего", total)
        st.metric("Готово", done)
        st.metric("Осталось", pending)
        page = st.radio(
            "Раздел",
            pages,
            index=pages.index(st.session_state.get("page", "Поиск")) if st.session_state.get("page", "Поиск") in pages else 0,
            label_visibility="collapsed",
        )
        st.session_state["page"] = page
    if page == "Поиск":
        page_search()
    elif page == "Компании":
        page_companies()
    elif page == "Промпты":
        page_prompts()
    elif page == "Нейросети":
        page_providers()
    elif page == "Автокомбайн":
        page_browser()
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
