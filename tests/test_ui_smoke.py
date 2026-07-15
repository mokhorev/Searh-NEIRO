from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import neirosearch.ui_app as ui_app


APP_PATH = Path(__file__).resolve().parents[1] / "src" / "neirosearch" / "ui_app.py"
INPUTS_DIR = Path(__file__).resolve().parents[1] / "inputs"
GENERATED_INPUTS = [INPUTS_DIR / "companies.csv", INPUTS_DIR / "providers.txt"]


class UiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preexisting_inputs = {path: path.exists() for path in GENERATED_INPUTS}

    def tearDown(self) -> None:
        for path, existed in self.preexisting_inputs.items():
            if not existed and path.exists():
                path.unlink()

    def test_main_sidebar_contains_statistics(self) -> None:
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertIn("Статистика", app.sidebar.radio[0].options)

    def test_statistics_page_renders_with_current_queue_state(self) -> None:
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        app.sidebar.radio[0].set_value("Статистика")
        app.run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(any("Статистика" in item.value for item in app.header))

    def test_depth_page_is_available(self) -> None:
        app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
        self.assertIn("Глубина рынка", app.sidebar.radio[0].options)

        app.sidebar.radio[0].set_value("Глубина рынка")
        app.run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(any("Глубина рынка" in item.value for item in app.header))

    def test_save_tasks_preserves_browser_status_columns(self) -> None:
        with self.subTest("status columns survive UI writes"):
            with patch.object(ui_app, "TASKS_PATH", Path(self.id()).with_suffix(".csv")):
                path = ui_app.TASKS_PATH
                try:
                    ui_app.save_tasks(
                        pd.DataFrame(
                            [
                                {
                                    "brand": "Альфа",
                                    "provider_id": "chatgpt_web",
                                    "answer": "готово",
                                    "status": "ok",
                                    "attempts": 1,
                                    "run_id": "run-1",
                                }
                            ]
                        )
                    )
                    loaded = ui_app.load_tasks()
                    self.assertIn("status", loaded.columns)
                    self.assertEqual(loaded.iloc[0]["status"], "ok")
                    self.assertEqual(loaded.iloc[0]["run_id"], "run-1")
                finally:
                    path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
