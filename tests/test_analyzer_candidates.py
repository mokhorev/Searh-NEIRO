from __future__ import annotations

import unittest

from neirosearch.analyzer import (
    clean_answer_for_report,
    extract_possible_company_names,
    prompt_mentions_brand,
    summarize_results,
)
from neirosearch.models import ProviderResult


class CandidateExtractionTests(unittest.TestCase):
    def test_map_widget_chrome_is_removed_from_report_answer(self) -> None:
        answer = (
            "4.8\nSOCO салон красоты\nРазвернуть\n"
            "Use two fingers to move the map\n© Mapbox Условия\n"
            "Оставить отзыв\n\nСалон рекомендуют за окрашивание."
        )

        cleaned = clean_answer_for_report(answer)

        self.assertEqual(cleaned, "Салон рекомендуют за окрашивание.")

    def test_prompted_and_organic_brand_visibility_are_separated(self) -> None:
        brand = "В отражении"
        results = [
            ProviderResult(
                provider_id="chatgpt_web",
                provider_label="ChatGPT",
                model="web/manual",
                prompt=f"Стоит ли выбирать {brand}?",
                ok=True,
                answer=f"{brand} подходит для этой услуги.",
            ),
            ProviderResult(
                provider_id="chatgpt_web",
                provider_label="ChatGPT",
                model="web/manual",
                prompt="Кого выбрать для сложного окрашивания?",
                ok=True,
                answer=f"Можно рассмотреть {brand}.",
            ),
            ProviderResult(
                provider_id="chatgpt_web",
                provider_label="ChatGPT",
                model="web/manual",
                prompt="Какие салоны рекомендуют?",
                ok=True,
                answer="SOCO и Mod's Hair.",
            ),
        ]

        summary = summarize_results(results, brand)

        self.assertTrue(prompt_mentions_brand(results[0].prompt, brand))
        self.assertFalse(prompt_mentions_brand(results[1].prompt, brand))
        self.assertEqual(summary["brand_found"], 2)
        self.assertEqual(summary["prompted_results"], 1)
        self.assertEqual(summary["organic_results"], 2)
        self.assertEqual(summary["organic_brand_found"], 1)

    def test_generic_beauty_phrases_are_not_company_candidates(self) -> None:
        answer = (
            "1. Салон красоты — общий вариант.\n"
            "2. салон SOCO — конкретная студия.\n"
            "3. Студия красоты — ещё одна общая формулировка."
        )

        candidates = extract_possible_company_names(answer, brand="В отражении")

        self.assertNotIn("Салон красоты", candidates)
        self.assertNotIn("Студия красоты", candidates)
        self.assertIn("салон SOCO", candidates)

    def test_platform_and_ui_noise_is_filtered(self) -> None:
        answer = (
            "Zoon, Profi и Flamp — справочники.\n"
            "Mapbox Условия, OpenStreetMap Mod и Avito — элементы страницы.\n"
            "Студия «В отражении» — это клиент."
        )

        candidates = extract_possible_company_names(answer, brand="В отражении")

        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
