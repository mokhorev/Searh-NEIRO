from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from neirosearch.browser.combinator import pending_task_diagnostics, pending_task_indexes


class BrowserQueueTests(unittest.TestCase):
    def test_only_pending_and_retry_tasks_are_runnable(self) -> None:
        tasks = pd.DataFrame(
            [
                {"provider_id": "chatgpt_web", "answer": "", "status": "pending"},
                {"provider_id": "chatgpt_web", "answer": "", "status": "retry"},
                {"provider_id": "chatgpt_web", "answer": "", "status": "running"},
                {"provider_id": "chatgpt_web", "answer": "", "status": "error"},
                {"provider_id": "chatgpt_web", "answer": "готово", "status": "pending"},
                {"provider_id": "unsupported_web", "answer": "", "status": "pending"},
            ]
        )

        self.assertEqual(pending_task_indexes(tasks, providers=["chatgpt_web"]), [0, 1])

    def test_missing_queue_has_specific_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.csv"
            messages = pending_task_diagnostics(pd.DataFrame(), tasks_path=path)

        self.assertIn("Файл очереди не найден", messages[0])
        self.assertIn(str(path.resolve()), messages[0])

    def test_provider_mismatch_lists_available_providers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ui_tasks.csv"
            path.touch()
            tasks = pd.DataFrame(
                [{"provider_id": "qwen_web", "answer": "", "status": "pending"}]
            )
            messages = pending_task_diagnostics(
                tasks,
                providers=["chatgpt_web"],
                tasks_path=path,
            )

        diagnostic = " ".join(messages)
        self.assertIn("нет задач для: chatgpt_web", diagnostic)
        self.assertIn("qwen_web", diagnostic)

    def test_missing_provider_column_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ui_tasks.csv"
            path.touch()
            messages = pending_task_diagnostics(
                pd.DataFrame([{"answer": "", "status": "pending"}]),
                tasks_path=path,
            )

        self.assertIn("столбец provider_id", " ".join(messages))


if __name__ == "__main__":
    unittest.main()
