from __future__ import annotations

import unittest

import pandas as pd

from neirosearch.depth_scan import (
    build_depth_prompt,
    build_depth_task_rows,
    depth_tasks,
    first_brand_depth,
)


class DepthScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.company = {
            "brand": "В отражении",
            "industry": "сложное окрашивание волос",
            "region": "Красноярск",
            "competitors": "",
        }

    def test_prompt_does_not_include_client_brand(self) -> None:
        prompt = build_depth_prompt(
            industry=self.company["industry"],
            region=self.company["region"],
            iteration=1,
            candidate_limit=7,
        )

        self.assertNotIn(self.company["brand"], prompt)
        self.assertIn(self.company["industry"], prompt)
        self.assertIn(self.company["region"], prompt)

    def test_task_rows_have_iteration_metadata(self) -> None:
        tasks = build_depth_task_rows(
            self.company,
            providers=["chatgpt_web", "gemini_web"],
            provider_labels={"chatgpt_web": "ChatGPT", "gemini_web": "Gemini"},
            iteration=2,
            candidate_limit=5,
            known_candidates=["Салон Альфа"],
        )

        self.assertEqual(len(tasks), 2)
        self.assertEqual(set(tasks["prompt_id"]), {"D2"})
        self.assertTrue(tasks["notes"].str.contains("depth_iter=2").all())
        self.assertNotIn(self.company["brand"], tasks.iloc[0]["prompt"])
        self.assertIn("Салон Альфа", tasks.iloc[0]["prompt"])

    def test_first_brand_depth_uses_completed_depth_answers(self) -> None:
        tasks = pd.DataFrame(
            [
                {
                    "brand": "В отражении",
                    "provider_label": "ChatGPT",
                    "notes": "depth_scan; depth_iter=1",
                    "answer": "Салон Альфа и Салон Бета.",
                },
                {
                    "brand": "В отражении",
                    "provider_label": "ChatGPT",
                    "notes": "depth_scan; depth_iter=2",
                    "answer": "Можно рассмотреть В отражении.",
                },
            ]
        )

        self.assertEqual(first_brand_depth(tasks, "В отражении"), 2)
        self.assertEqual(len(depth_tasks(tasks, brand="В отражении")), 2)


if __name__ == "__main__":
    unittest.main()
