from neirosearch.measurement import IntentClass, build_observation, infer_intent, stable_id


def test_stable_id_is_deterministic() -> None:
    assert stable_id("query", "a", 1) == stable_id("query", "a", 1)
    assert stable_id("query", "a", 1) != stable_id("query", "a", 2)


def test_intent_inference() -> None:
    assert infer_intent("Кого выбрать для ремонта квартиры?") == IntentClass.COMMERCIAL
    assert infer_intent("Сравни компании по ремонту") == IntentClass.COMPARISON
    assert infer_intent("Расскажи про Альфа", brand="Альфа") == IntentClass.BRAND
    assert infer_intent("Какое юрлицо стоит за Альфа?", brand="Альфа") == IntentClass.ENTITY_CHECK


def test_observation_keeps_evidence_span() -> None:
    answer = "Стоит рассмотреть Альфа как один из вариантов. Также рекомендуют Бета."
    observation = build_observation(
        task_id="task_1",
        answer=answer,
        brand="Альфа",
        competitors=["Бета"],
        citations=["https://example.test"],
    )
    assert observation.client_mentioned is True
    assert observation.client_recommended is True
    assert observation.evidence_spans
    assert observation.requires_manual_review is True
