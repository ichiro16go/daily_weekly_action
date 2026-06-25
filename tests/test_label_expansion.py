"""expand_weekly_labels と Config.weekly_label_pattern のテスト (EPGPRD-318)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as cfg  # noqa: E402
from jira_monitor import expand_weekly_labels  # noqa: E402


def _make_conf(**overrides) -> cfg.Config:
    defaults = dict(
        base_url="https://example.atlassian.net",
        email="test@example.com",
        api_token="token",
        slack_webhook_url=None,
        weekly_labels=["運用保守"],
        weekly_label_pattern=r"^運用保守\d{6}$",
    )
    defaults.update(overrides)
    return cfg.Config(**defaults)


class ExpandWeeklyLabelsTests(unittest.TestCase):
    def test_adds_matching_labels(self) -> None:
        conf = _make_conf()
        client = MagicMock()

        # `運用保守` で 15件 →キャップ→ 深掘りトリガー、`運用保守0..9` を呼ぶ
        # `運用保守2` も 15件で深掘り、`運用保守20..29` を呼ぶ
        # 最終的に新ラベルが取れる構造を再現
        full_2024 = [f"運用保守2024{m:02d}" for m in range(1, 13)]
        full_2025 = ["運用保守202501", "運用保守202502", "運用保守202503"]

        def fake_suggest(prefix):
            if prefix == "運用保守":
                # 15件キャップ (2024 系で埋まる)
                return ["運用保守"] + full_2024 + ["運用保守保留案件", "運用保守保留A"]
            if prefix == "運用保守2":
                return full_2024 + ["運用保守202501", "運用保守202502", "運用保守202503"][:3]
            if prefix == "運用保守20":
                return full_2024 + full_2025
            return []

        client.fetch_label_suggestions.side_effect = fake_suggest
        added = expand_weekly_labels(client, conf)
        for m in range(1, 13):
            self.assertIn(f"運用保守2024{m:02d}", added)
        self.assertIn("運用保守202501", added)
        self.assertIn("運用保守202503", added)
        self.assertNotIn("運用保守保留案件", added)
        # 再帰が走ったことを確認
        self.assertGreater(client.fetch_label_suggestions.call_count, 11)

    def test_no_pattern_skips(self) -> None:
        conf = _make_conf(weekly_label_pattern=None)
        client = MagicMock()
        added = expand_weekly_labels(client, conf)
        self.assertEqual(added, [])
        client.fetch_label_suggestions.assert_not_called()

    def test_dedupe(self) -> None:
        conf = _make_conf(weekly_labels=["運用保守", "運用保守202401"])
        client = MagicMock()
        client.fetch_label_suggestions.return_value = ["運用保守202401", "運用保守202402"]
        added = expand_weekly_labels(client, conf)
        self.assertEqual(added, ["運用保守202402"])
        self.assertEqual(conf.weekly_labels.count("運用保守202401"), 1)

    def test_api_error_keeps_existing(self) -> None:
        conf = _make_conf()
        client = MagicMock()
        client.fetch_label_suggestions.side_effect = RuntimeError("HTTP 500")
        added = expand_weekly_labels(client, conf)
        self.assertEqual(added, [])
        self.assertEqual(conf.weekly_labels, ["運用保守"])

    def test_invalid_regex_skips(self) -> None:
        conf = _make_conf(weekly_label_pattern="[invalid(")
        client = MagicMock()
        added = expand_weekly_labels(client, conf)
        self.assertEqual(added, [])
        client.fetch_label_suggestions.assert_not_called()


class WeeklyLabelPatternEnvTests(unittest.TestCase):
    def test_default_pattern(self) -> None:
        env = {
            "JIRA_BASE_URL": "https://x",
            "JIRA_EMAIL": "a@b.c",
            "JIRA_API_TOKEN": "t",
        }
        with patch.dict(os.environ, env, clear=True):
            conf = cfg.load()
        self.assertEqual(conf.weekly_label_pattern, r"^運用保守\d{6}$")

    def test_env_override(self) -> None:
        env = {
            "JIRA_BASE_URL": "https://x",
            "JIRA_EMAIL": "a@b.c",
            "JIRA_API_TOKEN": "t",
            "WEEKLY_LABEL_PATTERN": r"^special\d+$",
        }
        with patch.dict(os.environ, env, clear=True):
            conf = cfg.load()
        self.assertEqual(conf.weekly_label_pattern, r"^special\d+$")

    def test_empty_env_disables(self) -> None:
        env = {
            "JIRA_BASE_URL": "https://x",
            "JIRA_EMAIL": "a@b.c",
            "JIRA_API_TOKEN": "t",
            "WEEKLY_LABEL_PATTERN": "",
        }
        with patch.dict(os.environ, env, clear=True):
            conf = cfg.load()
        self.assertIsNone(conf.weekly_label_pattern)


if __name__ == "__main__":
    unittest.main()
