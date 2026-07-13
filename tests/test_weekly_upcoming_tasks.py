"""EPGPRD-292: 週報に今後の予定タスクセクションを表示するテスト。"""

import unittest

import config as cfg
from jira_monitor import AssigneeStat, TicketBrief, WeeklySummary, format_weekly, format_weekly_blocks


class WeeklyUpcomingTasksTest(unittest.TestCase):
    def _summary(self) -> WeeklySummary:
        return WeeklySummary(
            period_label="2026-07-06〜2026-07-13",
            stale=[],
            overdue=[],
            unassigned=[],
            new_tickets_count=0,
            closed_count=0,
            delta_count=0,
            overdue_count=0,
            unassigned_count=0,
            in_progress_count=0,
            trend_4w=[0, 0, 0, 0],
            assignee_stats=[AssigneeStat(name="宮本一路", closed_this_week=0, in_progress=0)],
            new_tickets=[],
            upcoming_tasks=[
                TicketBrief(
                    key="EPGPRD-999",
                    summary="9月末までの予定タスク",
                    assignee="宮本一路",
                    detail="期限: 2026-09-30",
                )
            ],
            filter_urls={"upcoming_tasks": "https://example.invalid/issues/?jql=..."},
        )

    def _conf(self) -> cfg.Config:
        return cfg.Config(
            base_url="https://epark-tech.atlassian.net",
            email="test@example.com",
            api_token="dummy",
            slack_webhook_url=None,
            weekly_labels=["運用保守"],
        )

    def test_format_weekly_contains_upcoming_section(self) -> None:
        text = format_weekly(self._summary())
        self.assertIn("📅 今後の予定タスク（当月〜9月末）", text)
        self.assertIn("EPGPRD-999", text)

    def test_format_weekly_blocks_contains_upcoming_section(self) -> None:
        blocks = format_weekly_blocks(self._summary(), self._conf())
        joined = "\n".join(
            e.get("text", "")
            for b in blocks
            for e in (
                [b.get("text", {})]
                if b.get("text")
                else b.get("fields", []) + b.get("elements", [])
            )
            if isinstance(e, dict)
        )
        self.assertIn("今後の予定タスク（当月〜9月末）", joined)
        self.assertIn("EPGPRD-999", joined)


if __name__ == "__main__":
    unittest.main()
