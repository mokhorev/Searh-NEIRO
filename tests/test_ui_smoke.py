from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


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


if __name__ == "__main__":
    unittest.main()
