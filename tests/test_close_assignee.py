"""_assignee_name_at_close のテスト."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_dashboard_data import _assignee_name_at_close, _assignee_name_at_close_with_source  # noqa: E402


def _issue(current: str, resolved: str, histories: list[dict]) -> dict:
    return {
        "fields": {
            "assignee": {"displayName": current},
            "resolutiondate": resolved,
        },
        "changelog": {"histories": histories},
    }


class CloseAssigneeTests(unittest.TestCase):
    def test_returns_current_assignee_when_history_missing(self) -> None:
        issue = _issue("現在担当", "2026-06-10T10:00:00.000+0900", [])
        self.assertEqual(_assignee_name_at_close(issue), "現在担当")
        self.assertEqual(_assignee_name_at_close_with_source(issue), ("現在担当", "current"))

    def test_rewinds_post_close_assignee_change(self) -> None:
        issue = _issue(
            "報告者",
            "2026-06-10T10:00:00.000+0900",
            [
                {
                    "created": "2026-06-10T10:00:00.000+0900",
                    "items": [
                        {
                            "field": "assignee",
                            "fromString": "担当A",
                            "toString": "報告者",
                        },
                    ],
                }
            ],
        )
        self.assertEqual(_assignee_name_at_close(issue), "担当A")
        self.assertEqual(_assignee_name_at_close_with_source(issue), ("担当A", "changelog"))

    def test_ignores_assignee_changes_before_resolution(self) -> None:
        issue = _issue(
            "担当B",
            "2026-06-10T10:00:00.000+0900",
            [
                {
                    "created": "2026-06-01T10:00:00.000+0900",
                    "items": [
                        {
                            "field": "assignee",
                            "fromString": "担当A",
                            "toString": "担当B",
                        },
                    ],
                }
            ],
        )
        self.assertEqual(_assignee_name_at_close(issue), "担当B")
        self.assertEqual(_assignee_name_at_close_with_source(issue), ("担当B", "current"))


if __name__ == "__main__":
    unittest.main()
