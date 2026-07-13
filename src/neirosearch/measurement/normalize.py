from __future__ import annotations

import re

from .models import AnswerObservation, EvidenceSpan, IntentClass, SignalLevel

ANALYZER_VERSION = "measurement-core-v1"

POSITIVE_MARKERS = (
    "рекоменд",
    "совет",
    "лучший",
    "подходит",
    "можно обратиться",
    "стоит рассмотреть",
    "хороший вариант",
    "включить в короткий список",
    "один из вариантов",
)
NEGATIVE_MARKERS = (
    "не рекоменд",
    "не могу рекоменд",
    "не стоит",
    "лучше не",
    "жалоб",
    "риск",
    "негатив",
    "не удалось подтвердить",
    "нет достаточных данных",
)
COMMERCIAL_MARKERS = (
    "кого выбрать",
    "где заказать",
    "где купить",
    "к кому обратиться",
    "посоветуй",
    "рекомендуй",
    "лучшие компании",
    "надежный подрядчик",
    "надёжный подрядчик",
)
COMPARISON_MARKERS = (
    "сравни",
    "кто лучше",
    "кто надежнее",
    "кто надёжнее",
    "на что смотреть",
    "какие риски",
    "как выбрать",
)
SCENARIO_MARKERS = (
    "мне нужно",
    "нужно ",
    "хочу ",
    "ищу ",
    "надо ",
)
ENTITY_MARKERS = (
    "официальный сайт",
    "какое юрлицо",
    "инн",
    "огрн",
    "связаны ли",
    "не является ли",
)


def normalize_text(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^\w\s\-]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def infer_intent(prompt: str, brand: str = "") -> IntentClass:
    normalized = normalize_text(prompt)
    if any(marker in normalized for marker in ENTITY_MARKERS):
        return IntentClass.ENTITY_CHECK
    if any(marker in normalized for marker in COMPARISON_MARKERS):
        return IntentClass.COMPARISON
    if any(marker in normalized for marker in COMMERCIAL_MARKERS):
        return IntentClass.COMMERCIAL
    brand_norm = normalize_text(brand)
    if brand_norm and brand_norm in normalized:
        return IntentClass.BRAND
    if any(marker in normalized for marker in SCENARIO_MARKERS):
        return IntentClass.SCENARIO
    return IntentClass.SCENARIO


def sentence_matches(answer: str, term: str) -> list[tuple[str, int, int]]:
    if not term.strip():
        return []
    result: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[^.!?\n]+[.!?]?", answer):
        sentence = match.group(0).strip()
        if normalize_text(term) in normalize_text(sentence):
            result.append((sentence, match.start(), match.end()))
    return result


def extract_candidate_entities(answer: str, brand: str = "", limit: int = 20) -> list[str]:
    candidates: list[str] = []
    for quoted in re.findall(r"[«\"]([^«»\"\n]{2,80})[»\"]", answer):
        candidates.append(quoted.strip())
    for line in answer.splitlines():
        line = re.sub(r"^[\s\-–—•*\d.)]+", "", line.strip())
        if not line:
            continue
        head = re.split(r"\s+[—–-]\s+|:\s+|\.\s+", line, maxsplit=1)[0].strip()
        if 2 <= len(head) <= 80:
            candidates.append(head)
    result: list[str] = []
    seen: set[str] = set()
    brand_norm = normalize_text(brand)
    generic = {
        "россия",
        "москва",
        "яндекс",
        "google",
        "chatgpt",
        "gemini",
        "qwen",
        "deepseek",
        "perplexity",
        "gigachat",
        "grok",
        "вывод",
        "итог",
        "рекомендации",
    }
    for candidate in candidates:
        cleaned = candidate.strip(" «»\"'()[]{}.,:;!?")
        normalized = normalize_text(cleaned)
        if not normalized or normalized == brand_norm or normalized in generic:
            continue
        if len(cleaned.split()) > 7 or len(cleaned) < 2:
            continue
        if normalized not in seen:
            seen.add(normalized)
            result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _rank_from_text(answer: str, brand: str) -> int | None:
    normalized_answer = normalize_text(answer)
    normalized_brand = normalize_text(brand)
    index = normalized_answer.find(normalized_brand)
    if index < 0:
        return None
    return len(normalized_answer[:index].split()) + 1


def build_observation(
    *,
    task_id: str,
    answer: str,
    brand: str,
    competitors: list[str] | None = None,
    citations: list[str] | None = None,
) -> AnswerObservation:
    competitors = competitors or []
    citations = citations or []
    contexts = sentence_matches(answer, brand)
    client_mentioned = bool(contexts)
    client_recommended = False
    strength = "absent"
    confidence = 0.95 if not client_mentioned else 0.55
    evidence_spans: list[EvidenceSpan] = []

    for sentence, start, end in contexts:
        normalized = normalize_text(sentence)
        evidence_spans.append(
            EvidenceSpan(label="brand_context", quote=sentence, start=start, end=end)
        )
        negative = any(marker in normalized for marker in NEGATIVE_MARKERS)
        positive = any(marker in normalized for marker in POSITIVE_MARKERS)
        if negative:
            strength = "negative_or_caution"
            confidence = max(confidence, 0.75)
        elif positive:
            client_recommended = True
            strength = "recommended"
            confidence = max(confidence, 0.78)
        elif strength == "absent":
            strength = "mentioned"

    competitors_mentioned: list[str] = []
    competitors_recommended: list[str] = []
    for competitor in competitors:
        matches = sentence_matches(answer, competitor)
        if not matches:
            continue
        competitors_mentioned.append(competitor)
        for sentence, start, end in matches:
            normalized = normalize_text(sentence)
            evidence_spans.append(
                EvidenceSpan(
                    label=f"competitor_context:{competitor}",
                    quote=sentence,
                    start=start,
                    end=end,
                )
            )
            if any(marker in normalized for marker in POSITIVE_MARKERS) and not any(
                marker in normalized for marker in NEGATIVE_MARKERS
            ):
                competitors_recommended.append(competitor)
                break

    answer_classes: list[str] = []
    reason_codes: list[str] = []
    if not client_mentioned:
        answer_classes.append("NO_MENTION")
        reason_codes.append("NO_AI_MENTION")
    elif client_recommended:
        answer_classes.append("RECOMMENDED_CLIENT")
    else:
        answer_classes.append("MENTIONED_NOT_RECOMMENDED")
    if competitors_recommended and not client_recommended:
        answer_classes.append("COMPETITOR_RECOMMENDED")
        reason_codes.append("COMPETITOR_RECOMMENDED")
    if not citations:
        answer_classes.append("SOURCELESS_ANSWER")

    candidate_entities = extract_candidate_entities(answer, brand=brand)
    manual_review = confidence < 0.8 or bool(candidate_entities) or not citations
    context_text = contexts[0][0] if contexts else ""
    return AnswerObservation(
        task_id=task_id,
        client_mentioned=client_mentioned,
        client_recommended=client_recommended,
        mention_context=context_text,
        recommendation_strength=strength,
        recommendation_rank=_rank_from_text(answer, brand),
        competitors_mentioned=competitors_mentioned,
        competitors_recommended=competitors_recommended,
        candidate_entities=candidate_entities,
        sources=citations,
        answer_classes=answer_classes,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        extraction_confidence=confidence,
        signal_level=SignalLevel.RAW_SIGNAL,
        requires_manual_review=manual_review,
        analyzer_version=ANALYZER_VERSION,
    )
