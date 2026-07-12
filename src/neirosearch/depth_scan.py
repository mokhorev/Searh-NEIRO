from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .analyzer import candidate_key, extract_possible_company_names, find_position
from .manual import TASK_FIELDNAMES

DEPTH_SCAN_TAG = "depth_scan"
DEPTH_PROMPT_PREFIX = "D"


def is_depth_note(value: str) -> bool:
    return DEPTH_SCAN_TAG in str(value).casefold()


def depth_iteration_from_notes(value: str) -> int | None:
    match = re.search(r"depth_iter\s*=\s*(\d+)", str(value))
    return int(match.group(1)) if match else None


def depth_task_mask(df: pd.DataFrame, brand: str | None = None) -> pd.Series:
    if df.empty or "notes" not in df.columns:
        return pd.Series(False, index=df.index)
    mask = df["notes"].fillna("").astype(str).map(is_depth_note)
    if brand is not None and "brand" in df.columns:
        mask &= df["brand"].fillna("").astype(str).eq(brand)
    return mask


def depth_tasks(df: pd.DataFrame, brand: str | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(df.columns) + ["depth_iter"] if len(df.columns) else TASK_FIELDNAMES + ["depth_iter"])
    data = df[depth_task_mask(df, brand=brand)].copy()
    if data.empty:
        data["depth_iter"] = []
        return data
    data["depth_iter"] = data["notes"].fillna("").astype(str).map(depth_iteration_from_notes).fillna(0).astype(int)
    return data


def answered_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "answer" not in df.columns:
        return df.copy()
    return df[df["answer"].fillna("").astype(str).str.strip().ne("")].copy()


def normalize_candidates(candidates: list[str], brand: str = "") -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    brand_key = candidate_key(brand) if brand else ""
    for raw in candidates:
        candidate = str(raw).strip()
        if not candidate:
            continue
        key = candidate_key(candidate)
        if not key or key == brand_key or key in seen:
            continue
        result.append(candidate)
        seen.add(key)
    return result


def extract_depth_candidates(answer: str, brand: str, limit: int = 50) -> list[str]:
    return normalize_candidates(extract_possible_company_names(answer, brand=brand, limit=limit), brand=brand)


def collect_known_candidates(tasks: pd.DataFrame, brand: str, through_iteration: int | None = None) -> list[str]:
    data = answered_only(depth_tasks(tasks, brand=brand))
    if through_iteration is not None and "depth_iter" in data.columns:
        data = data[data["depth_iter"] <= through_iteration]
    candidates: list[str] = []
    for _, row in data.sort_values(["depth_iter", "provider_label"]).iterrows():
        candidates.extend(extract_depth_candidates(str(row.get("answer", "")), brand=brand))
    return normalize_candidates(candidates, brand=brand)


def build_depth_prompt(
    industry: str,
    region: str,
    iteration: int,
    candidate_limit: int = 7,
    known_candidates: list[str] | None = None,
) -> str:
    industry = industry.strip()
    region = region.strip()
    known_candidates = normalize_candidates(known_candidates or [])
    base = [
        "Ты имитируешь поведение обычного человека, который выбирает подрядчика на рынке.",
        "",
        f"Ниша: {industry}" if industry else "Ниша: не указана",
        f"Регион: {region}" if region else "Регион: не указан",
        "",
    ]
    if iteration <= 1 or not known_candidates:
        base.extend([
            f"Назови {candidate_limit} конкретных компаний или брендов, которые пользователь, скорее всего, увидит или вспомнит в первом проходе поиска.",
            "Не называй агрегаторы, справочники, карты, нейросети, сайты-отзовики и общие категории.",
            "Не выдумывай точные рейтинги, адреса и телефоны. Нужны только кандидаты рынка и короткая причина, почему они всплыли.",
        ])
    else:
        excluded = "\n".join(f"- {item}" for item in known_candidates)
        base.extend([
            "Продолжи поиск глубже по тому же рынку.",
            "Эти компании уже рассматривались и их нельзя повторять:",
            excluded,
            "",
            f"Найди ещё до {candidate_limit} конкретных компаний или брендов, которые могут всплыть во втором/третьем/следующем проходе поиска.",
            "Не повторяй уже перечисленных. Не называй агрегаторы, справочники, карты, нейросети, сайты-отзовики и общие категории.",
            "Если новых уверенных кандидатов нет, напиши: новых уверенных кандидатов нет.",
        ])
    base.extend([
        "",
        "Формат ответа строго такой:",
        "1. Название — почему всплыло",
        "2. Название — почему всплыло",
    ])
    return "\n".join(base).strip()


def build_depth_task_rows(
    company: dict[str, Any],
    providers: list[str],
    provider_labels: dict[str, str],
    iteration: int,
    candidate_limit: int,
    known_candidates: list[str] | None = None,
) -> pd.DataFrame:
    brand = str(company.get("brand", "")).strip()
    industry = str(company.get("industry", "")).strip()
    region = str(company.get("region", "")).strip()
    competitors = str(company.get("competitors", "")).strip()
    prompt = build_depth_prompt(
        industry=industry,
        region=region,
        iteration=iteration,
        candidate_limit=candidate_limit,
        known_candidates=known_candidates,
    )
    rows = []
    for provider in providers:
        rows.append(
            {
                "brand": brand,
                "industry": industry,
                "region": region,
                "competitors": competitors,
                "provider_id": provider,
                "provider_label": provider_labels.get(provider, provider),
                "model": "web/manual",
                "prompt_id": f"{DEPTH_PROMPT_PREFIX}{iteration}",
                "prompt": prompt,
                "answer": "",
                "citations": "",
                "notes": f"{DEPTH_SCAN_TAG}; depth_iter={iteration}; depth_limit={candidate_limit}",
            }
        )
    return pd.DataFrame(rows, columns=TASK_FIELDNAMES)


def max_depth_iteration(tasks: pd.DataFrame, brand: str) -> int:
    data = depth_tasks(tasks, brand=brand)
    if data.empty or "depth_iter" not in data.columns:
        return 0
    return int(data["depth_iter"].max())


def brand_found_in_answer(answer: str, brand: str) -> bool:
    return find_position(answer, brand) is not None


def first_brand_depth(tasks: pd.DataFrame, brand: str) -> int | None:
    data = answered_only(depth_tasks(tasks, brand=brand))
    if data.empty:
        return None
    found = data[data["answer"].fillna("").astype(str).map(lambda value: brand_found_in_answer(value, brand))]
    if found.empty:
        return None
    return int(found["depth_iter"].min())


def depth_label(first_depth: int | None, max_iterations: int = 5) -> str:
    if first_depth is None:
        return f"Клиент не найден за {max_iterations} проходов — AI пока не держит бренд в активном слое рекомендаций."
    if first_depth == 1:
        return "Клиент найден в 1-й волне — высокая AI-видимость в верхнем слое рынка."
    if first_depth == 2:
        return "Клиент найден во 2-й волне — бренд виден, но не всегда попадает в первый короткий список."
    if first_depth == 3:
        return "Клиент найден в 3-й волне — видимость слабая, бренд находится глубже очевидных рекомендаций."
    return f"Клиент найден в {first_depth}-й волне — бренд всплывает только при углублённом поиске."


def depth_answer_rows(tasks: pd.DataFrame, brand: str) -> pd.DataFrame:
    data = depth_tasks(tasks, brand=brand)
    rows: list[dict[str, Any]] = []
    for _, row in data.sort_values(["depth_iter", "provider_label"]).iterrows():
        answer = str(row.get("answer", ""))
        has_answer = bool(answer.strip())
        candidates = extract_depth_candidates(answer, brand=brand) if has_answer else []
        rows.append(
            {
                "проход": int(row.get("depth_iter", 0)),
                "нейросеть": row.get("provider_label", ""),
                "статус": "готов" if has_answer else "без ответа",
                "клиент найден": "да" if has_answer and brand_found_in_answer(answer, brand) else "нет",
                "кандидаты": ", ".join(candidates),
                "промпт": row.get("prompt", ""),
                "ответ": answer,
            }
        )
    return pd.DataFrame(rows)


def depth_wave_summary(tasks: pd.DataFrame, brand: str) -> pd.DataFrame:
    data = depth_tasks(tasks, brand=brand)
    if data.empty:
        return pd.DataFrame(columns=["проход", "задач", "ответов", "клиент найден", "новых кандидатов", "кандидаты"])
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for iteration in sorted(data["depth_iter"].dropna().astype(int).unique()):
        wave = data[data["depth_iter"] == iteration]
        answered = answered_only(wave)
        wave_candidates: list[str] = []
        for _, row in answered.iterrows():
            wave_candidates.extend(extract_depth_candidates(str(row.get("answer", "")), brand=brand))
        unique_wave_candidates = normalize_candidates(wave_candidates, brand=brand)
        new_candidates = []
        for candidate in unique_wave_candidates:
            key = candidate_key(candidate)
            if key not in seen:
                new_candidates.append(candidate)
                seen.add(key)
        client_found = any(brand_found_in_answer(str(row.get("answer", "")), brand) for _, row in answered.iterrows())
        rows.append(
            {
                "проход": int(iteration),
                "задач": len(wave),
                "ответов": len(answered),
                "клиент найден": "да" if client_found else "нет",
                "новых кандидатов": len(new_candidates),
                "кандидаты": ", ".join(new_candidates),
            }
        )
    return pd.DataFrame(rows)
