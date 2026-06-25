"""サブタスク件数集計ヘルパのテスト (EPGPRD-323)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_dashboard_data import _count_subtasks_in_issues  # noqa: E402


class SubtaskCountTests(unittest.TestCase):
    def test_counts_only_issuetype_subtask_true(self) -> None:
        issues = [
            {"fields": {"issuetype": {"name": "サブタスク", "subtask": True}}},
            {"fields": {"issuetype": {"name": "Task", "subtask": False}}},
            {"fields": {"issuetype": {"name": "Sub-task", "subtask": True}}},
            {"fields": {"summary": "issuetypeなし"}},
        ]

        self.assertEqual(_count_subtasks_in_issues(issues), 2)

    def test_empty_list_returns_zero(self) -> None:
        self.assertEqual(_count_subtasks_in_issues([]), 0)


if __name__ == "__main__":
    unittest.main()
