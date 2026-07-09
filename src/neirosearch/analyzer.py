from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from .models import AnswerAnalysis, ProviderResult


STOP_COMPANY_CANDIDATES = {
    "томск",
    "томске",
    "россия",
    "google",
    "яндекс",
    "2гис",
    "chatgpt",
    "qwen",
    "deepseek",
    "perplexity",
    "gigachat",
    "grok",
    "gemini",
    "отзывы",
    "рейтинг",
    "адрес",
    "сайт",
    "телефон",
    "пациенты",
    "клиника",
    "стоматология",
    "центр",
    "вывод",
    "итог",
    "например",
    "важно",
    "рекомендую",
}

ORG_CONTEXT_WORDS = (
    "клиник",
    "стоматолог",
    "центр",
    "салон",
    "студ",
    "академ",
    "школ",
    "компан",
    "ооо",
    "ип ",
    "бренд",
    "сеть",
)



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
        "рекоменд",
        "совет",
        "лучший",
        "подходит",
        "выбрать",
        "топ",
        "можно обратиться",
        "стоит рассмотреть",
        "хороший вариант",
        "один из",
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



def clean_candidate(value: str) -> str:
    value = re.sub(r"^[\s\-–—•*\d.)]+", "", value.strip())
    value = re.sub(r"[\s,;:.!?]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip("«»\"'()[]{}")
    return value.strip()



def is_reasonable_company_candidate(value: str, brand: str = "") -> bool:
    candidate = clean_candidate(value)
    if len(candidate) < 3 or len(candidate) > 80:
        return False
    normalized = normalize_text(candidate)
    if not normalized or normalized in STOP_COMPANY_CANDIDATES:
        return False
    if brand and normalized == normalize_text(brand):
        return False
    if re.fullmatch(r"[\d\W_]+", candidate):
        return False
    words = normalized.split()
    if len(words) > 6:
        return False
    if len(words) == 1 and words[0] in STOP_COMPANY_CANDIDATES:
        return False
    return True



def extract_possible_company_names(answer: str, brand: str = "", limit: int = 15) -> list[str]:
    """Heuristically extract company/clinic names mentioned in an LLM answer.

    This is intentionally conservative and transparent: it is not NER. It catches common answer
    shapes like quoted names, bullet lists, numbered lists, and organization-context phrases.
    The output should be treated as candidates for manual verification in the audit report.
    """
    if not answer:
        return []

    candidates: list[str] = []

    # Quoted names: «Клиника», "Brand".
    for match in re.findall(r"[«\"]([^«»\"\n]{3,80})[»\"]", answer):
        candidates.append(match)

    # Bullet/numbered list starts: "1. Cosmodent — ...", "- Альфа: ...".
    for line in answer.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-–—•*\d.)\s]+", "", line)
        head = re.split(r"\s+[—–-]\s+|:\s+|\.\s+", line, maxsplit=1)[0]
        if 3 <= len(head) <= 80:
            candidates.append(head)

    # Context phrases: клиника X, стоматология Y, центр Z.
    context_pattern = re.compile(
        r"(?:клиника|стоматология|центр|салон|студия|академия|школа|сеть|компания)\s+([А-ЯA-ZЁ][А-ЯA-ZЁа-яa-zё0-9\-\s]{2,60})",
        re.IGNORECASE,
    )
    for match in context_pattern.findall(answer):
        candidates.append(match)

    # Capitalized compact names, including Latin brands and Russian names.
    capitalized_pattern = re.compile(
        r"\b([А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z0-9\-]*(?:\s+[А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z0-9\-]*){0,3})\b"
    )
    for match in capitalized_pattern.findall(answer):
        if any(word in normalize_text(match) for word in ORG_CONTEXT_WORDS) or len(match.split()) <= 3:
            candidates.append(match)

    result: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        candidate = clean_candidate(raw)
        normalized = normalize_text(candidate)
        if not is_reasonable_company_candidate(candidate, brand=brand):
            continue
        # Drop generic fragments that often appear in long text.
        if normalized.startswith(("если ", "при ", "чтобы ", "для ", "в ", "на ", "по ")):
            continue
        if normalized not in seen:
            result.append(candidate)
            seen.add(normalized)
        if len(result) >= limit:
            break
    return result



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
    record["possible_companies"] = extract_possible_company_names(result.answer, brand=brand) if result.ok else []
    return record
