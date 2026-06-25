"""_label_cohort_labels の挙動テスト (EPGPRD-318)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as cfg  # noqa: E402
from fetch_dashboard_data import _label_cohort_labels  # noqa: E402


def _make_conf(**overrides) -> cfg.Config:
    defaults = dict(
        base_url="https://x",
        email="x",
        api_token="x",
        slack_webhook_url=None,
        weekly_labels=["運用保守"],
        weekly_label_pattern=r"^運用保守\d{6}$",
    )
    defaults.update(overrides)
    return cfg.Config(**defaults)


class LabelCohortLabelsTests(unittest.TestCase):
    def test_uses_expanded_labels_when_available(self) -> None:
        """expand_weekly_labels で展開されたラベルを優先して返すこと"""
        conf = _make_conf(weekly_labels=[
            "運用保守",
            "運用保守202311",
            "運用保守202401",
            "運用保守202501",
            "運用保守保留案件",  # パターン不一致なので除外される
        ])
        result = _label_cohort_labels(conf)
        # パターンにマッチする 3 件のみ、ソート順
        self.assertEqual(result, ["運用保守202311", "運用保守202401", "運用保守202501"])

    def test_falls_back_to_generated_when_no_match(self) -> None:
        """マッチするラベルがなければ過去Nヶ月の機械生成にフォールバック"""
        conf = _make_conf(weekly_labels=["運用保守"])  # 6桁付きはない
        result = _label_cohort_labels(conf, months=3)
        # フォールバックで運用保守YYYYMM 形式 3 件を生成
        self.assertEqual(len(result), 3)
        for label in result:
            self.assertRegex(label, r"^運用保守\d{6}$")

    def test_none_conf_uses_fallback(self) -> None:
        """conf=None なら従来通り機械生成"""
        result = _label_cohort_labels(None, months=2)
        self.assertEqual(len(result), 2)

    def test_no_pattern_uses_fallback(self) -> None:
        """weekly_label_pattern=None なら conf からは取らずフォールバック"""
        conf = _make_conf(
            weekly_labels=["運用保守202311", "運用保守202401"],
            weekly_label_pattern=None,
        )
        result = _label_cohort_labels(conf, months=2)
        self.assertEqual(len(result), 2)
        # 機械生成なので 202311, 202401 そのものは含まない可能性が高い
        # （現在月起点で 2ヶ月分なので）


if __name__ == "__main__":
    unittest.main()
