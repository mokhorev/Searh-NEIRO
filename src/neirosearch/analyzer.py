from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from .models import AnswerAnalysis, ProviderResult


def normalize_text(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^\w\s\-]+", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def find_position(answer: str, term: str) -> int | None:
    if not term:
        return None
    haystack = normalize_text(answer)
    needle = normalize_text(term)
    idx = haystack.find(needle)
    if idx < 0:
        return None
    before = haystack[:idx]
    return len(before.split()) + 1


def sentence_context(answer: str, term: str) -> str:
    if not term:
        return ""
    pattern = re.compile(r"([^.!?\n]*" + re.escape(term) + r"[^.!?\n]*[.!?]?)", re.IGNORECASE)
    match = pattern.search(answer)
    return match.group(1).strip() if match else ""


def classify_role(answer: str, brand: str, brand_found: bool, position: int | None) -> tuple[str, float, list[str]]:
    notes: list[str] = []
    if not brand_found:
        return "absent", 0.95, ["Бренд не найден в ответе."]

    context = sentence_context(answer, brand).casefold()
    positive_markers = [
        "рекоменд", "совет", "лучший", "подходит", "выбрать", "топ", "можно обратиться",
        "стоит рассмотреть", "хороший вариант", "один из"
    ]
    caution_markers = ["не рекоменд", "нельзя рекоменд", "жалоб", "риск", "плохо", "негатив"]

    if any(marker in context for marker in caution_markers):
        notes.append("Бренд найден рядом с осторожной/негативной формулировкой.")
        return "negative_or_caution", 0.7, notes
    if position is not None and position <= 80 and any(marker in context for marker in positive_markers):
        notes.append("Бренд найден рано и рядом с рекомендательной формулировкой.")
        return "recommended", 0.75, notes
    if any(marker in context for marker in positive_markers):
        notes.append("Бренд найден рядом с рекомендательной формулировкой, но не обязательно в топе.")
        return "mentioned_positive", 0.65, notes
    notes.append("Бренд найден, но роль требует ручной проверки.")
    return "mentioned", 0.55, notes


def analyze_answer(answer: str, brand: str, competitors: list[str] | None = None) -> AnswerAnalysis:
    competitors = competitors or []
    position = find_position(answer, brand)
    brand_found = position is not None
    competitors_found = [c for c in competitors if find_position(answer, c) is not None]
    role, confidence, notes = classify_role(answer, brand, brand_found, position)
    if competitors_found and not brand_found:
        notes.append("Найдены конкуренты, но бренд отсутствует.")
    if competitors_found and brand_found:
        notes.append("Бренд найден вместе с конкурентами.")
    return AnswerAnalysis(
        brand=brand,
        brand_found=brand_found,
        brand_position=position,
        competitors_found=competitors_found,
        role=role,
        confidence=confidence,
        notes=notes,
    )


def summarize_results(results: list[ProviderResult], brand: str, competitors: list[str] | None = None) -> dict[str, Any]:
    analyses = [analyze_answer(r.answer, brand, competitors).to_dict() for r in results if r.ok]
    ok_count = sum(1 for r in results if r.ok)
    found_count = sum(1 for a in analyses if a["brand_found"])
    recommended_count = sum(1 for a in analyses if a["role"] == "recommended")
    return {
        "brand": brand,
        "total_results": len(results),
        "ok_results": ok_count,
        "brand_found": found_count,
        "brand_recommended": recommended_count,
        "visibility_rate": round(found_count / ok_count, 3) if ok_count else 0,
        "recommendation_rate": round(recommended_count / ok_count, 3) if ok_count else 0,
        "analyses": analyses,
    }


def result_record(result: ProviderResult, brand: str, competitors: list[str] | None = None) -> dict[str, Any]:
    analysis = analyze_answer(result.answer, brand, competitors) if result.ok else None
    record = result.to_dict()
    record["analysis"] = asdict(analysis) if analysis else None
    return record
