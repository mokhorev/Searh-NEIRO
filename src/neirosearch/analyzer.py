from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from .models import AnswerAnalysis, ProviderResult


STOP_COMPANY_CANDIDATES = {
    # Geo/platform/service noise.
    "томск",
    "томске",
    "москва",
    "москве",
    "красноярск",
    "красноярске",
    "россия",
    "рф",
    "google",
    "яндекс",
    "yandex",
    "2гис",
    "2 gis",
    "2gis",
    "chatgpt",
    "openai",
    "qwen",
    "deepseek",
    "perplexity",
    "gigachat",
    "giga chat",
    "grok",
    "gemini",
    "claude",
    "сбер",
    # UI/report words.
    "отзывы",
    "рейтинг",
    "адрес",
    "сайт",
    "телефон",
    "карта",
    "карты",
    "цены",
    "услуги",
    "пациенты",
    "клиенты",
    "вывод",
    "итог",
    "например",
    "важно",
    "рекомендую",
    "альтернативы",
    "варианты",
    "плюсы",
    "минусы",
    "лучшие",
    "список",
    "топ",
    # Over-generic org words. They are useful only when attached to a name.
    "клиника",
    "стоматология",
    "центр",
    "салон",
    "студия",
    "академия",
    "школа",
    "компания",
    "бренд",
    "сеть",
    "ооо",
    "ип",
    "ао",
    "пао",
    "зао",
    "ано",
    "чоу",
    "нко",
}

BAD_CANDIDATE_SUBSTRINGS = (
    "http",
    "www.",
    ".ru",
    ".com",
    ".рф",
    "яндекс карт",
    "yandex maps",
    "google maps",
    "2гис",
    "официальный сайт",
    "по данным",
    "в городе",
    "для услуги",
    "если бы",
    "кого посоветуешь",
    "какие компании",
    "какие плюсы",
    "какие минусы",
    "стоит ли",
    "сравни ",
    "не могу",
    "у меня нет",
    "актуальн",
    "проверьте",
    "проверить",
    "смотрите",
    "обратите внимание",
)

BAD_PREFIXES = (
    "если ",
    "при ",
    "чтобы ",
    "для ",
    "в ",
    "на ",
    "по ",
    "и ",
    "или ",
    "но ",
    "а ",
    "это ",
    "такие ",
    "следующие ",
    "лучше ",
    "лучшие ",
    "топ ",
    "плюсы ",
    "минусы ",
    "важно ",
    "вывод ",
    "итог ",
)

ORG_CONTEXT_WORDS = (
    "клиник",
    "стоматолог",
    "медицин",
    "центр",
    "салон",
    "студ",
    "академ",
    "школ",
    "компан",
    "ооо",
    "ип ",
    "ао ",
    "пао ",
    "нко ",
    "бренд",
    "сеть",
    "групп",
    "group",
    "clinic",
    "studio",
    "school",
    "academy",
    "center",
    "centre",
)

ORG_LEGAL_PREFIXES = (
    "ооо",
    "ип",
    "ао",
    "пао",
    "зао",
    "нко",
    "чоу",
    "ано",
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
    value = str(value).replace("\u00a0", " ")
    value = re.sub(r"^[\s\-–—•*#>\d.)]+", "", value.strip())
    value = re.sub(r"[*_`]+", "", value)
    value = re.sub(r"\s*\([^)]{0,80}\)\s*$", "", value)
    value = re.split(r"\s+[—–-]\s+|:\s+|\s+\|\s+", value, maxsplit=1)[0]
    value = re.sub(r"[\s,;:.!?]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()
    if len(value) >= 2 and value[0] in "«\"'" and value[-1] in "»\"'":
        value = value[1:-1]
    value = value.strip("()[]{}")
    return value.strip()


def _has_letter(value: str) -> bool:
    return bool(re.search(r"[A-Za-zА-Яа-яЁё]", value))


def _has_name_signal(value: str) -> bool:
    normalized = normalize_text(value)
    words = normalized.split()
    if not words:
        return False
    if any(word in ORG_LEGAL_PREFIXES for word in words):
        return True
    if any(part in normalized for part in ORG_CONTEXT_WORDS):
        return len(words) >= 2
    # Brand-like quoted/list names: at least one token starts with a capital letter or the name is Latin.
    raw_words = re.findall(r"[A-Za-zА-Яа-яЁё0-9\-]+", value)
    if any(re.match(r"[A-ZА-ЯЁ]", word) for word in raw_words):
        return True
    if re.search(r"[A-Za-z]", value) and len(words) <= 3:
        return True
    return False


def is_reasonable_company_candidate(value: str, brand: str = "") -> bool:
    candidate = clean_candidate(value)
    if len(candidate) < 3 or len(candidate) > 80:
        return False
    if not _has_letter(candidate):
        return False
    normalized = normalize_text(candidate)
    if not normalized or normalized in STOP_COMPANY_CANDIDATES:
        return False
    if any(part in normalized for part in BAD_CANDIDATE_SUBSTRINGS):
        return False
    if normalized.startswith(BAD_PREFIXES):
        return False
    if brand and normalized == normalize_text(brand):
        return False
    if re.fullmatch(r"[\d\W_]+", candidate):
        return False
    words = normalized.split()
    if len(words) > 6:
        return False
    if len(words) == 1:
        token = words[0]
        if token in STOP_COMPANY_CANDIDATES:
            return False
        # A single common word is almost always noise; a single capitalized/Latin brand is allowed.
        if not re.match(r"[A-ZА-ЯЁ]", candidate) and not re.search(r"[A-Za-z]", candidate):
            return False
    return _has_name_signal(candidate)


def candidate_key(value: str) -> str:
    normalized = normalize_text(value)
    normalized = re.sub(r"^(ооо|ип|ао|пао|зао|ано|чоу|нко)\s+", "", normalized)
    normalized = re.sub(r"^(клиника|стоматология|медцентр|медицинский центр|центр|салон|студия|академия|школа|сеть|компания)\s+", "", normalized)
    return normalized.strip()


def _append_candidate(candidates: list[str], raw: str) -> None:
    candidate = clean_candidate(raw)
    if candidate:
        candidates.append(candidate)


def _line_head_candidate(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[\-–—•*#>\d.)\s]+", "", line)
    # Markdown list item can be "**Название** — описание".
    bold = re.match(r"\*\*([^*\n]{3,80})\*\*", line)
    if bold:
        return bold.group(1)
    return re.split(r"\s+[—–-]\s+|:\s+|\.\s+", line, maxsplit=1)[0]


def extract_possible_company_names(answer: str, brand: str = "", limit: int = 15) -> list[str]:
    """Heuristically extract company/clinic names mentioned in an LLM/search answer.

    This is intentionally conservative and transparent: it is not full NER. It catches common
    answer shapes like quoted names, numbered/bullet lists, and organization-context phrases.
    The output should be treated as candidates for manual verification in the audit report.
    """
    if not answer:
        return []

    candidates: list[str] = []

    # Quoted names: «Клиника Сибирская», "Sigma Academy".
    for match in re.findall(r"[«\"]([^«»\"\n]{3,80})[»\"]", answer):
        _append_candidate(candidates, match)

    # Legal prefixes: ООО «Ромашка», ИП Иванов, АО НИИПП.
    legal_pattern = re.compile(
        r"\b((?:ООО|ИП|АО|ПАО|ЗАО|АНО|ЧОУ|НКО)\s+(?:[«\"][^«»\"\n]{3,70}[»\"]|[А-ЯA-ZЁ][^,;.!?\n—–-]{2,70}))",
        re.IGNORECASE,
    )
    for match in legal_pattern.finditer(answer):
        _append_candidate(candidates, match.group(1))

    # Context phrases: клиника X, стоматология Y, центр Z. Keep the context word because
    # "Сибирская" alone is weaker than "Клиника Сибирская".
    context_pattern = re.compile(
        r"\b((?:клиника|стоматология|медцентр|медицинский центр|центр|салон|студия|академия|школа|сеть|компания|clinic|studio|academy|school|center|group)\s+[«\"]?[А-ЯA-ZЁ][А-ЯA-ZЁа-яa-zё0-9\-&\s]{2,60}[»\"]?)",
        re.IGNORECASE,
    )
    for match in context_pattern.findall(answer):
        _append_candidate(candidates, match)

    # Bullet/numbered list starts: "1. Cosmodent — ...", "- Альфа: ...".
    for line in answer.splitlines():
        line = line.strip()
        if not line:
            continue
        looks_like_list = bool(re.match(r"^\s*(?:[-–—•*]|\d+[.)])\s+", line))
        has_markdown_bold = bool(re.match(r"^\s*[-–—•*]?\s*\*\*[^*]{3,80}\*\*", line))
        if not (looks_like_list or has_markdown_bold):
            continue
        head = _line_head_candidate(line)
        if 3 <= len(head) <= 80:
            _append_candidate(candidates, head)

    # Capitalized compact names. This is intentionally last and filtered hard.
    capitalized_pattern = re.compile(
        r"\b([А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z0-9&\-]*(?:\s+[А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z0-9&\-]*){0,3})\b"
    )
    for match in capitalized_pattern.findall(answer):
        normalized = normalize_text(match)
        if any(word in normalized for word in ORG_CONTEXT_WORDS) or re.search(r"[A-Z]", match):
            _append_candidate(candidates, match)

    result: list[str] = []
    seen: dict[str, int] = {}
    for raw in candidates:
        candidate = clean_candidate(raw)
        if not is_reasonable_company_candidate(candidate, brand=brand):
            continue
        key = candidate_key(candidate)
        if not key:
            continue
        if key in seen:
            # Prefer the more specific display form, e.g. ООО «Ромашка» over Ромашка.
            existing_index = seen[key]
            if len(candidate) > len(result[existing_index]):
                result[existing_index] = candidate
            continue
        seen[key] = len(result)
        result.append(candidate)
        if len(result) >= limit:
            break
    return result


def count_candidate_mentions(texts: list[str], brand: str = "", limit_per_text: int = 20) -> dict[str, int]:
    counts: dict[str, int] = {}
    canonical: dict[str, str] = {}
    for text in texts:
        for candidate in extract_possible_company_names(text, brand=brand, limit=limit_per_text):
            key = candidate_key(candidate)
            canonical.setdefault(key, candidate)
            if len(candidate) > len(canonical[key]):
                canonical[key] = candidate
            counts[key] = counts.get(key, 0) + 1
    return {canonical[key]: value for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))}


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
