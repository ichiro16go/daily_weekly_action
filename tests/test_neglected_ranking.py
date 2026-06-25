"""放置チケットランキングのテスト (EPGPRD-321)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
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
        weekly_labels=["運用保守"],
    )
    defaults.update(overrides)
    return cfg.Config(**defaults)


def _issue(key: str, days_ago: int) -> dict:
    created = datetime.now(tz=fdd.JST) - timedelta(days=days_ago)
    return {
        "key": key,
        "fields": {
            "summary": f"summary {key}",
            "assignee": {"displayName": f"assignee {key}"},
            "status": {"name": "Open"},
            "created": created.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
            "issuetype": {"name": "Task"},
        },
    }


class FakeJiraClient:
    def __init__(self, issues: list[dict]) -> None:
        self.issues = issues
        self.calls: list[tuple[str, list[str], int]] = []

    def search(self, jql: str, fields: list[str], max_results: int = 100) -> list[dict]:
        self.calls.append((jql, fields, max_results))
        return self.issues


class BuildNeglectedRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conf = _make_conf()

    def test_sorts_by_days_desc(self) -> None:
        client = FakeJiraClient([_issue("EPGPRD-2", 10), _issue("EPGPRD-1", 30), _issue("EPGPRD-3", 20)])
        result = fdd.build_neglected_ranking(client, self.conf)
        self.assertEqual([item["key"] for item in result], ["EPGPRD-1", "EPGPRD-3", "EPGPRD-2"])
        self.assertEqual(result[0]["created"], (datetime.now(tz=fdd.JST) - timedelta(days=30)).strftime("%Y-%m-%d"))
        self.assertIn("statusCategory != Done", client.calls[0][0])
        self.assertIn('labels IN ("運用保守")', client.calls[0][0])
        self.assertIn("ORDER BY created ASC", client.calls[0][0])
        self.assertEqual(client.calls[0][1], ["summary", "assignee", "status", "created", "issuetype"])

    def test_caps_top_20(self) -> None:
        client = FakeJiraClient([_issue(f"EPGPRD-{i}", i) for i in range(25)])
        result = fdd.build_neglected_ranking(client, self.conf)
        self.assertEqual(len(result), 20)
        self.assertEqual(result[0]["key"], "EPGPRD-24")
        self.assertEqual(result[-1]["key"], "EPGPRD-5")

    def test_empty_input_returns_empty_output(self) -> None:
        client = FakeJiraClient([])
        self.assertEqual(fdd.build_neglected_ranking(client, self.conf), [])


if __name__ == "__main__":
    unittest.main()
