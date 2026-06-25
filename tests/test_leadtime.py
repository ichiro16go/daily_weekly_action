"""fetch_dashboard_data._calc_leadtime のテスト (EPGPRD-320 で改修).

EPGPRD-320 で「期間外作成チケットは除外」「整数 days」「サブタスク混入」の3つを解消:
  - created < start による除外を廃止
  - 日数は秒単位を float で計算（1桁丸め）
  - サブタスクはデフォルトで除外
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_dashboard_data import _calc_leadtime  # noqa: E402

JST = timezone(timedelta(hours=9))


def _issue(
    created: str | None,
    resolved: str | None,
    *,
    subtask: bool = False,
) -> dict:
    return {
        "fields": {
            "created": created,
            "resolutiondate": resolved,
            "issuetype": {"name": "サブタスク" if subtask else "タスク", "subtask": subtask},
        }
    }


class CalcLeadtimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.end = datetime(2026, 6, 30, 23, 59, 59, tzinfo=JST)

    def test_in_range_counts(self) -> None:
        issues = [
            _issue("2026-06-01T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
            _issue("2026-06-10T09:00:00.000+0900", "2026-06-20T09:00:00.000+0900"),
        ]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(lt, [4.0, 10.0])

    def test_old_created_included(self) -> None:
        """EPGPRD-320: 期間外に作成された古いチケットも LT 集計に含める。"""
        # start を渡さなくなったので、過去作成チケットでも resolved-created で計算される
        issues = [
            _issue("2026-05-15T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
            _issue("2026-06-10T09:00:00.000+0900", "2026-06-20T09:00:00.000+0900"),
        ]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(lt, [21.0, 10.0])

    def test_missing_created_skipped(self) -> None:
        issues = [
            _issue(None, "2026-06-10T09:00:00.000+0900"),
            _issue("2026-06-02T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
        ]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(lt, [3.0])

    def test_unresolved_uses_end(self) -> None:
        issues = [_issue("2026-06-25T09:00:00.000+0900", None)]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(len(lt), 1)
        self.assertGreaterEqual(lt[0], 5.0)

    def test_negative_days_skipped(self) -> None:
        # resolved < created（データ異常）はスキップ
        issues = [_issue("2026-06-15T09:00:00.000+0900", "2026-06-10T09:00:00.000+0900")]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(lt, [])

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_calc_leadtime([], self.end), [])

    def test_subday_returns_fraction(self) -> None:
        """EPGPRD-320: 同日クローズが 0 日 floor にならず小数で残る。"""
        issues = [
            # 12h = 0.5日（banker's rounding を避けるため0.5境界外を選択）
            _issue("2026-06-10T00:00:00.000+0900", "2026-06-10T14:24:00.000+0900"),
        ]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(lt, [0.6])  # 14.4h / 24h = 0.6

    def test_subtask_excluded_by_default(self) -> None:
        """EPGPRD-320: サブタスクは LT 集計から除外する。"""
        issues = [
            _issue("2026-06-01T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
            _issue(
                "2026-06-10T09:00:00.000+0900",
                "2026-06-10T09:30:00.000+0900",
                subtask=True,
            ),
        ]
        lt = _calc_leadtime(issues, self.end)
        self.assertEqual(lt, [4.0])

    def test_subtask_can_be_included(self) -> None:
        issues = [
            _issue("2026-06-01T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
            _issue(
                "2026-06-10T00:00:00.000+0900",
                "2026-06-12T00:00:00.000+0900",
                subtask=True,
            ),
        ]
        lt = _calc_leadtime(issues, self.end, exclude_subtasks=False)
        self.assertEqual(lt, [4.0, 2.0])


if __name__ == "__main__":
    unittest.main()
