"""_get_created_in_range の JQL 構築テスト (EPGPRD-318 regression)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

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


class GetCreatedInRangeJqlTests(unittest.TestCase):
    """過去に `created >= "..."` と二重クォートになり常に 0 件返るバグがあった。
    `_jql_datetime` は既にクォート込み文字列を返すため、追加クォートしてはいけない。
    """

    def setUp(self) -> None:
        self.client = MagicMock()
        self.client.count.return_value = 42
        self.conf = _make_conf()
        # JST 想定の素朴な aware datetime
        self.start = datetime(2026, 6, 18, 0, 0, tzinfo=timezone.utc)
        self.end = datetime(2026, 6, 25, 0, 0, tzinfo=timezone.utc)

    def test_no_double_quotes_around_datetime(self) -> None:
        fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        called_jql = self.client.count.call_args[0][0]
        # 不正: created >= ""...""
        self.assertNotIn('""', called_jql)
        # 正常: created >= "..."（クォート1組のみ）
        self.assertIn("created >= ", called_jql)
        self.assertIn("created < ", called_jql)

    def test_includes_label_filter(self) -> None:
        fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        called_jql = self.client.count.call_args[0][0]
        self.assertIn('labels IN ("運用保守")', called_jql)

    def test_returns_client_count(self) -> None:
        result = fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        self.assertEqual(result, 42)


if __name__ == "__main__":
    unittest.main()
