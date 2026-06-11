#!/usr/bin/env python3
"""
fetch_dashboard_data.py — Jira APIからダッシュボード用データを取得しJSONに出力する

使い方:
  python3 fetch_dashboard_data.py              # → dashboard/data/ にJSON群を生成
  python3 fetch_dashboard_data.py --out /path  # → 指定ディレクトリに出力

既存の jira_monitor.py / config.py を再利用する。
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

# 親ディレクトリのモジュールをインポート
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as cfg
from jira_monitor import (
    JiraClient, JST, check_stale, _parse_jira_dt, _jql_datetime,
)

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _week_ranges(weeks: int = 26):
    """直近N週の(start, end)リストを返す（古い順）"""
    now = datetime.now(tz=JST)
    # 今週月曜を基準
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = today - timedelta(days=today.weekday())
    ranges = []
    for i in range(weeks - 1, -1, -1):
        start = monday - timedelta(weeks=i)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        ranges.append((start, end))
    return ranges


def _month_ranges(months: int = 6):
    """直近Nヶ月の(start, end, label)リストを返す"""
    now = datetime.now(tz=JST)
    ranges = []
    for i in range(months, 0, -1):
        year = now.year
        month = now.month - i + 1
        if month <= 0:
            month += 12
            year -= 1
        start = datetime(year, month, 1, tzinfo=JST)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=JST) - timedelta(seconds=1)
        else:
            end = datetime(year, month + 1, 1, tzinfo=JST) - timedelta(seconds=1)
        label = f"{year}-{month:02d}"
        ranges.append((start, end, label))
    return ranges


def _get_closed_in_range(client: JiraClient, conf: cfg.Config, start, end):
    """指定期間にクローズされたチケットを返す"""
    start_jql = _jql_datetime(start)
    end_jql = _jql_datetime(end)
    jql = conf.board_member_jql(
        f'status IN (Done, 完了, Close, Resolved, 解決済み, リリース済み) '
        f'AND status changed TO (Done, 完了, Close, Resolved, 解決済み, リリース済み) '
        f'AFTER {start_jql} BEFORE {end_jql}'
    )
    return client.search(jql, ["summary", "assignee", "created", "resolutiondate", "issuetype"], max_results=500)


def _get_in_progress(client: JiraClient, conf: cfg.Config):
    """現在IN PROGRESSのチケットを返す"""
    jql = conf.board_member_jql(
        'status = "In Progress"',
        order_by="assignee ASC"
    )
    return client.search(jql, ["summary", "assignee", "created", "updated", "duedate"], max_results=200)


def _assignee_name(issue) -> str:
    assignee = issue["fields"].get("assignee")
    if assignee:
        return assignee.get("displayName", "不明")
    return "未アサイン"


# ---------------------------------------------------------------------------
# データ生成関数
# ---------------------------------------------------------------------------

def build_team_summary(client: JiraClient, conf: cfg.Config) -> dict:
    """チーム全体のKPIと推移"""
    month_ranges = _month_ranges(6)
    week_ranges = _week_ranges(26)

    # 月次リードタイム
    monthly_leadtime = []
    for start, end, label in month_ranges:
        issues = _get_closed_in_range(client, conf, start, end)
        lead_times = []
        for issue in issues:
            created_str = issue["fields"].get("created")
            resolution_str = issue["fields"].get("resolutiondate")
            if not created_str:
                continue
            created = _parse_jira_dt(created_str)
            if resolution_str:
                resolved = _parse_jira_dt(resolution_str)
            else:
                resolved = end
            days = (resolved - created).days
            if days >= 0:
                lead_times.append(days)
        avg = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0
        med = round(median(lead_times), 1) if lead_times else 0
        monthly_leadtime.append({
            "month": label,
            "avg_days": avg,
            "median_days": med,
            "count": len(lead_times),
        })

    # 週次クローズ・対応中数
    weekly_closed = []
    for start, end in week_ranges[-8:]:  # 直近8週
        issues = _get_closed_in_range(client, conf, start, end)
        label = start.strftime("%m/%d")
        weekly_closed.append({"week": label, "count": len(issues)})

    # 現在の対応中数
    in_progress = _get_in_progress(client, conf)
    current_wip = len(in_progress)

    return {
        "monthly_leadtime": monthly_leadtime,
        "weekly_closed": weekly_closed,
        "current_wip": current_wip,
        "wip_limit": conf.wip_limit,
    }


def build_member_stats(client: JiraClient, conf: cfg.Config) -> dict:
    """メンバー別の完了数・対応中数 週次推移"""
    week_ranges_list = _week_ranges(26)
    members: dict[str, dict] = {}

    # 直近8週の完了を集計
    for start, end in week_ranges_list[-8:]:
        issues = _get_closed_in_range(client, conf, start, end)
        week_label = start.strftime("%m/%d")
        for issue in issues:
            name = _assignee_name(issue)
            if name not in members:
                members[name] = {"weeks": [], "in_progress": 0}
        # 今週分の完了数をカウント
        week_count: dict[str, int] = {}
        for issue in issues:
            name = _assignee_name(issue)
            week_count[name] = week_count.get(name, 0) + 1
        for name in members:
            members[name]["weeks"].append({
                "week": week_label,
                "closed": week_count.get(name, 0),
            })

    # 対応中数
    in_progress = _get_in_progress(client, conf)
    for issue in in_progress:
        name = _assignee_name(issue)
        if name not in members:
            members[name] = {"weeks": [], "in_progress": 0}
        members[name]["in_progress"] += 1

    return {"members": members, "wip_limit": conf.wip_limit}


def build_member_leadtime(client: JiraClient, conf: cfg.Config) -> dict:
    """メンバー別リードタイム月次推移"""
    month_ranges = _month_ranges(6)
    members: dict[str, list] = {}

    for start, end, label in month_ranges:
        issues = _get_closed_in_range(client, conf, start, end)
        # メンバーごとにリードタイムを集計
        member_lt: dict[str, list[int]] = {}
        for issue in issues:
            name = _assignee_name(issue)
            created_str = issue["fields"].get("created")
            resolution_str = issue["fields"].get("resolutiondate")
            if not created_str:
                continue
            created = _parse_jira_dt(created_str)
            resolved = _parse_jira_dt(resolution_str) if resolution_str else end
            days = (resolved - created).days
            if days >= 0:
                if name not in member_lt:
                    member_lt[name] = []
                member_lt[name].append(days)

        for name, times in member_lt.items():
            if name not in members:
                members[name] = []
            members[name].append({
                "month": label,
                "avg_days": round(sum(times) / len(times), 1),
                "median_days": round(median(times), 1),
                "count": len(times),
            })

    return {"members": members}


def build_stale_ranking(client: JiraClient, conf: cfg.Config) -> list:
    """滞留チケットランキング"""
    stale = check_stale(client, conf, stale_days=3)
    return [
        {
            "key": t.key,
            "summary": t.summary,
            "assignee": t.assignee,
            "days_stale": t.days_stale,
        }
        for t in sorted(stale, key=lambda x: -x.days_stale)
    ]


def build_overdue_ranking(client: JiraClient, conf: cfg.Config) -> list:
    """期限超過チケットランキング"""
    now = datetime.now(tz=JST)
    jql = conf.board_jql(
        f'duedate < "{now.strftime("%Y-%m-%d")}" AND duedate IS NOT EMPTY',
        order_by="duedate ASC"
    )
    issues = client.search(jql, ["summary", "assignee", "duedate"], max_results=50)
    results = []
    for issue in issues:
        due_str = issue["fields"].get("duedate", "")
        if not due_str:
            continue
        due_date = datetime.strptime(due_str, "%Y-%m-%d").replace(tzinfo=JST)
        days_over = (now - due_date).days
        results.append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "assignee": _assignee_name(issue),
            "duedate": due_str,
            "days_overdue": days_over,
        })
    return sorted(results, key=lambda x: -x["days_overdue"])


def build_wip_status(client: JiraClient, conf: cfg.Config) -> dict:
    """WIP超過状況"""
    in_progress = _get_in_progress(client, conf)
    by_member: dict[str, list] = {}
    for issue in in_progress:
        name = _assignee_name(issue)
        if name not in by_member:
            by_member[name] = []
        by_member[name].append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "days": (datetime.now(tz=JST) - _parse_jira_dt(issue["fields"]["updated"])).days,
        })

    members = []
    for name, tickets in sorted(by_member.items(), key=lambda x: -len(x[1])):
        members.append({
            "name": name,
            "count": len(tickets),
            "over_limit": len(tickets) > conf.wip_limit,
            "tickets": tickets,
        })

    return {
        "wip_limit": conf.wip_limit,
        "total_wip": len(in_progress),
        "members": members,
    }


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ダッシュボード用データ取得")
    parser.add_argument("--out", default=str(Path(__file__).parent / "dashboard" / "data"),
                        help="出力ディレクトリ")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        conf = cfg.load()
    except EnvironmentError as e:
        print(f"❌ 設定エラー: {e}", file=sys.stderr)
        sys.exit(1)

    client = JiraClient(conf)
    now_str = datetime.now(tz=JST).isoformat()

    print("📊 チームサマリーを取得中...")
    team = build_team_summary(client, conf)
    _write(out_dir / "team_summary.json", team)

    print("👥 メンバー別統計を取得中...")
    members = build_member_stats(client, conf)
    _write(out_dir / "member_stats.json", members)

    print("⏱  メンバー別リードタイムを取得中...")
    lt = build_member_leadtime(client, conf)
    _write(out_dir / "member_leadtime.json", lt)

    print("🚨 滞留ランキングを取得中...")
    stale = build_stale_ranking(client, conf)
    _write(out_dir / "stale_ranking.json", stale)

    print("⚠️  期限超過ランキングを取得中...")
    overdue = build_overdue_ranking(client, conf)
    _write(out_dir / "overdue_ranking.json", overdue)

    print("📋 WIP状況を取得中...")
    wip = build_wip_status(client, conf)
    _write(out_dir / "wip_status.json", wip)

    meta = {"updated_at": now_str, "data_files": 6}
    _write(out_dir / "meta.json", meta)

    print(f"✅ 完了: {out_dir} に7ファイル出力")


def _write(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
