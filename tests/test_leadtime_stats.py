"""fetch_dashboard_data._calc_leadtime_stats のテスト (EPGPRD-313)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_dashboard_data import _calc_leadtime_stats  # noqa: E402


class CalcLeadtimeStatsTests(unittest.TestCase):
    def test_empty(self) -> None:
        s = _calc_leadtime_stats([])
        self.assertEqual(s["count"], 0)
        self.assertEqual(s["outlier_count"], 0)
        self.assertEqual(s["avg_days"], 0)
        self.assertEqual(s["median_days"], 0)

    def test_small_sample_no_outlier_removed(self) -> None:
        # サンプル < 5 では外れ値除外しない
        s = _calc_leadtime_stats([1, 2, 100])
        self.assertEqual(s["count"], 3)
        self.assertEqual(s["outlier_count"], 0)

    def test_p95_excludes_extreme(self) -> None:
        # 1..19 + 9999 → P95 で 9999 が除外される
        data = list(range(1, 20)) + [9999]
        s = _calc_leadtime_stats(data)
        self.assertEqual(s["outlier_count"], 1)
        self.assertEqual(s["count"], 19)
        self.assertLess(s["avg_days"], 100)
        self.assertEqual(s["p95_threshold"], 19.0)

    def test_p95_threshold_is_value_not_index(self) -> None:
        data = [10] * 20
        s = _calc_leadtime_stats(data)
        self.assertEqual(s["p95_threshold"], 10.0)
        self.assertEqual(s["outlier_count"], 0)
        self.assertEqual(s["avg_days"], 10.0)

    def test_count_matches_kept_only(self) -> None:
        data = [1] * 19 + [500]
        s = _calc_leadtime_stats(data)
        # count は保持された母集団のサイズ（外れ値除外後）
        self.assertEqual(s["count"] + s["outlier_count"], len(data))


if __name__ == "__main__":
    unittest.main()
