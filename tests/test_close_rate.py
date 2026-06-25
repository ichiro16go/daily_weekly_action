"""_safe_rate のテスト (EPGPRD-311)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_dashboard_data import _safe_rate  # noqa: E402


class SafeRateTests(unittest.TestCase):
    def test_zero_denominator(self) -> None:
        self.assertEqual(_safe_rate(0, 0), 0.0)
        self.assertEqual(_safe_rate(5, 0), 0.0)

    def test_negative_denominator(self) -> None:
        self.assertEqual(_safe_rate(3, -1), 0.0)

    def test_normal(self) -> None:
        self.assertEqual(_safe_rate(3, 10), 0.3)
        self.assertEqual(_safe_rate(7, 8), 0.875)

    def test_rounding(self) -> None:
        # 1/3 → 0.333 (3桁丸め)
        self.assertEqual(_safe_rate(1, 3), 0.333)

    def test_over_one_allowed(self) -> None:
        # 同じ週内でクローズが起案を上回るケースもあり得る
        self.assertEqual(_safe_rate(15, 10), 1.5)


if __name__ == "__main__":
    unittest.main()
