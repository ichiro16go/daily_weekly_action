"""_get_created_in_range の JQL 構築テスト (EPGPRD-318 regression)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

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

    def test_omits_label_filter_by_default(self) -> None:
        fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        called_jql = self.client.count.call_args[0][0]
        self.assertNotIn('labels IN ("運用保守")', called_jql)

    def test_can_enable_label_filter_via_env(self) -> None:
        with patch.dict(
            fdd.os.environ,
            {"DASHBOARD_USE_WEEKLY_LABEL_FILTER": "true"},
            clear=False,
        ):
            fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        called_jql = self.client.count.call_args[0][0]
        self.assertIn('labels IN ("運用保守")', called_jql)

    def test_returns_client_count(self) -> None:
        result = fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        self.assertEqual(result, 42)

    def test_jql_matches_weekly_report_format(self) -> None:
        """週報側 (jira_monitor.build_weekly_summary L525-527) と同じ
        `created >= ... AND created < ...` 形式であることを保証する。
        日付クォートの付け方が乖離すると 0 件バグが再発するため。
        """
        import jira_monitor as jm

        fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        dash_jql = self.client.count.call_args[0][0]

        # 週報側の組み立て方を再現
        start_q = jm._jql_datetime(self.start)
        end_q = jm._jql_datetime(self.end)
        expected_fragment = f"created >= {start_q} AND created < {end_q}"
        self.assertIn(expected_fragment, dash_jql)

    def test_datetime_quoted_exactly_once(self) -> None:
        """`_jql_datetime` の戻り値クォートが二重化されていないこと。"""
        fdd._get_created_in_range(self.client, self.conf, self.start, self.end)
        jql = self.client.count.call_args[0][0]
        # 日付の前後に `""` が現れたらバグ再発
        import re
        self.assertIsNone(re.search(r'""\d{4}/', jql))
        self.assertIsNone(re.search(r'\d{2}:\d{2}""', jql))


if __name__ == "__main__":
    unittest.main()
