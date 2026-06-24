"""fetch_dashboard_data._calc_leadtime のテスト (EPGPRD-314)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_dashboard_data import _calc_leadtime  # noqa: E402

JST = timezone(timedelta(hours=9))


def _issue(created: str, resolved: str | None) -> dict:
    return {"fields": {"created": created, "resolutiondate": resolved}}


class CalcLeadtimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 6, 1, tzinfo=JST)
        self.end = datetime(2026, 6, 30, 23, 59, 59, tzinfo=JST)

    def test_in_range_counts(self) -> None:
        issues = [
            _issue("2026-06-01T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
            _issue("2026-06-10T09:00:00.000+0900", "2026-06-20T09:00:00.000+0900"),
        ]
        lt, excluded = _calc_leadtime(issues, self.start, self.end)
        self.assertEqual(lt, [4, 10])
        self.assertEqual(excluded, 0)

    def test_old_created_excluded(self) -> None:
        issues = [
            _issue("2026-05-15T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
            _issue("2026-06-10T09:00:00.000+0900", "2026-06-20T09:00:00.000+0900"),
        ]
        lt, excluded = _calc_leadtime(issues, self.start, self.end)
        self.assertEqual(lt, [10])
        self.assertEqual(excluded, 1)

    def test_missing_created_skipped(self) -> None:
        issues = [
            {"fields": {"created": None, "resolutiondate": "2026-06-10T09:00:00.000+0900"}},
            _issue("2026-06-02T09:00:00.000+0900", "2026-06-05T09:00:00.000+0900"),
        ]
        lt, excluded = _calc_leadtime(issues, self.start, self.end)
        self.assertEqual(lt, [3])
        self.assertEqual(excluded, 0)

    def test_unresolved_uses_end(self) -> None:
        issues = [
            _issue("2026-06-25T09:00:00.000+0900", None),
        ]
        lt, excluded = _calc_leadtime(issues, self.start, self.end)
        self.assertEqual(len(lt), 1)
        self.assertGreaterEqual(lt[0], 5)

    def test_negative_days_skipped(self) -> None:
        # resolved < created（データ異常）はスキップ
        issues = [
            _issue("2026-06-15T09:00:00.000+0900", "2026-06-10T09:00:00.000+0900"),
        ]
        lt, excluded = _calc_leadtime(issues, self.start, self.end)
        self.assertEqual(lt, [])
        self.assertEqual(excluded, 0)

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_calc_leadtime([], self.start, self.end), ([], 0))


if __name__ == "__main__":
    unittest.main()
