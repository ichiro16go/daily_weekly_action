"""Calendar data generation tests for WBSGantt date fields."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as cfg  # noqa: E402
import fetch_dashboard_data as fdd  # noqa: E402


def _make_conf(**overrides) -> cfg.Config:
    defaults = dict(
        base_url="https://example.atlassian.net",
        email="test@example.com",
        api_token="token",
        slack_webhook_url=None,
        weekly_labels=[],
    )
    defaults.update(overrides)
    return cfg.Config(**defaults)


class FakeJiraClient:
    def __init__(self, issues: list[dict]) -> None:
        self.issues = issues
        self.requested_fields: list[str] | None = None

    def search(self, _jql: str, fields: list[str], max_results: int = 50) -> list[dict]:
        self.requested_fields = fields
        return self.issues[:max_results]


class BuildCalendarDataEndDateTests(unittest.TestCase):
    def test_uses_wbsgantt_end_before_duedate_and_falls_back(self) -> None:
        issues = [
            {
                "key": "EPGPRD-1",
                "fields": {
                    "summary": "WBS end wins",
                    "assignee": {"displayName": "石橋 テスト"},
                    "status": {"name": "In Progress"},
                    "duedate": "2026-07-01",
                    "customfield_10200": "2026-06-20",
                    "customfield_10201": "2026-07-05T00:00:00.000+0900",
                    "created": "2026-06-01T09:00:00.000+0900",
                    "priority": {"name": "Medium"},
                },
            },
            {
                "key": "EPGPRD-2",
                "fields": {
                    "summary": "Fallback to due",
                    "assignee": {"displayName": "石橋 テスト"},
                    "status": {"name": "In Progress"},
                    "duedate": "2026-07-02",
                    "customfield_10200": "2026-06-21",
                    "customfield_10201": None,
                    "created": "2026-06-02T09:00:00.000+0900",
                    "priority": None,
                },
            },
        ]
        client = FakeJiraClient(issues)
        data = fdd.build_calendar_data(client, _make_conf())

        self.assertIn("customfield_10201", client.requested_fields or [])
        tasks = data["members"]["石橋 テスト"]["tasks"]
        self.assertEqual(tasks[0]["key"], "EPGPRD-2")
        self.assertEqual(tasks[0]["dueDate"], "2026-07-02")
        self.assertEqual(tasks[0]["endDateSource"], "duedate")
        self.assertEqual(tasks[1]["key"], "EPGPRD-1")
        self.assertEqual(tasks[1]["dueDate"], "2026-07-05")
        self.assertEqual(tasks[1]["endDateSource"], "wbsgantt")


if __name__ == "__main__":
    unittest.main()
