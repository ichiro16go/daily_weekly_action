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
    JiraClient, JST, CLOSE_STATUSES, check_stale, _parse_jira_dt, _jql_datetime,
    _resolved_jql, _jql_list, expand_weekly_labels,
)

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _calc_leadtime(issues, start, end):
    """
    与えられた issues 群から、period (start, end) 内に created されたものだけを
    対象にリードタイム日数のリストと除外件数を返す。EPGPRD-314 用ヘルパ。

    戻り値: (lead_times: list[int], excluded_old_count: int)
    """
    lead_times: list[int] = []
    excluded_old = 0
    for issue in issues:
        created_str = issue["fields"].get("created")
        resolution_str = issue["fields"].get("resolutiondate")
        if not created_str:
            continue
        created = _parse_jira_dt(created_str)
        if created < start:
            excluded_old += 1
            continue
        resolved = _parse_jira_dt(resolution_str) if resolution_str else end
        days = (resolved - created).days
        if days >= 0:
            lead_times.append(days)
    return lead_times, excluded_old


def _calc_leadtime_stats(days_list: list[int]) -> dict:
    """
    リードタイム日数リストから P95 を計算し、P95 超を外れ値として除外した
    avg/median/count/outlier_count/p95_threshold を返す。EPGPRD-313 用。

    - 件数が 0 → すべてゼロ
    - 件数が 1〜4 → 母数が少なすぎるので P95 除外を行わず元の値で集計
    """
    if not days_list:
        return {
            "avg_days": 0,
            "median_days": 0,
            "count": 0,
            "outlier_count": 0,
            "p95_threshold": 0,
        }

    sorted_days = sorted(days_list)
    n = len(sorted_days)
    if n < 5:
        return {
            "avg_days": round(sum(sorted_days) / n, 1),
            "median_days": round(median(sorted_days), 1),
            "count": n,
            "outlier_count": 0,
            "p95_threshold": float(sorted_days[-1]),
        }
    idx = max(int(round(0.95 * n)) - 1, 0)
    p95 = sorted_days[idx]
    kept = [d for d in days_list if d <= p95]
    outliers = len(days_list) - len(kept)
    if not kept:
        kept = days_list
        outliers = 0
    return {
        "avg_days": round(sum(kept) / len(kept), 1),
        "median_days": round(median(kept), 1),
        "count": len(kept),
        "outlier_count": outliers,
        "p95_threshold": float(p95),
    }


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


def _label_cohort_labels(conf: "cfg.Config | None" = None, months: int = 18) -> list[str]:
    """期間別コホート対象のラベル一覧（古い順）を返す。

    conf.weekly_label_pattern にマッチするラベル（`expand_weekly_labels` で
    展開された実在ラベル）を優先して使う。空または該当なしの場合は
    フォールバックで「今日から過去 months ヶ月分」を機械生成する
    （後方互換のため）。
    """
    import re as _re

    if conf is not None and getattr(conf, "weekly_label_pattern", None):
        try:
            regex = _re.compile(conf.weekly_label_pattern)
            matched = sorted({l for l in conf.weekly_labels if regex.match(l)})
            if matched:
                return matched
        except _re.error:
            pass

    # フォールバック: 現在月から遡って機械生成
    now = datetime.now(tz=JST)
    labels = []
    for offset in range(months - 1, -1, -1):
        year = now.year
        month = now.month - offset
        while month <= 0:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        labels.append(f"運用保守{year}{month:02d}")
    return labels


def _get_closed_in_range(client: JiraClient, conf: cfg.Config, start, end):
    """指定期間にクローズされたチケットを返す（resolved フィールドベース）"""
    jql = conf.board_member_jql(
        f'{_resolved_jql(start, end)}{_label_filter(conf)}'
    )
    return client.search(jql, ["summary", "assignee", "created", "resolutiondate", "issuetype"], max_results=500)


def _get_created_in_range(client: JiraClient, conf: cfg.Config, start, end):
    """指定期間に起案（created）されたチケット件数を返す。

    NOTE: `_jql_datetime` はすでにダブルクォート込みの文字列を返すため、
    f-string 内で追加で `"` を付けてはならない（過去にこれが原因で常に 0 件
    返るバグがあった。週報側 jira_monitor.build_weekly_summary の実装に揃える）。
    """
    start_jql = _jql_datetime(start)
    end_jql = _jql_datetime(end)
    extra = f'created >= {start_jql} AND created < {end_jql}{_label_filter(conf)}'
    jql = conf.board_member_jql(extra)
    return client.count(jql)


def _safe_rate(numerator: int, denominator: int) -> float:
    """0 除算ガード付きで比率を返す（小数点 3 桁、0.0 〜 ∞）。"""
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def _get_in_progress(client: JiraClient, conf: cfg.Config):
    """現在IN PROGRESSのチケットを返す（ラベルフィルタ適用）"""
    extra = f'status = "In Progress"{_label_filter(conf)}'
    jql = conf.board_member_jql(extra, order_by="assignee ASC")
    return client.search(jql, ["summary", "assignee", "created", "updated", "duedate"], max_results=200)


def _label_filter(conf: cfg.Config) -> str:
    """ラベルフィルタJQL片を返す（先頭に AND 付き、空なら空文字）"""
    if conf.weekly_labels:
        quoted = ", ".join(f'"{l}"' for l in conf.weekly_labels)
        return f' AND labels IN ({quoted})'
    return ""


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
        excluded_old = 0
        for issue in issues:
            created_str = issue["fields"].get("created")
            resolution_str = issue["fields"].get("resolutiondate")
            if not created_str:
                continue
            created = _parse_jira_dt(created_str)
            # EPGPRD-314: 期間を跨いだ古いチケットはリードタイム集計から除外
            if created < start:
                excluded_old += 1
                continue
            if resolution_str:
                resolved = _parse_jira_dt(resolution_str)
            else:
                resolved = end
            days = (resolved - created).days
            if days >= 0:
                lead_times.append(days)
        avg = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0
        med = round(median(lead_times), 1) if lead_times else 0
        stats = _calc_leadtime_stats(lead_times)
        monthly_leadtime.append({
            "month": label,
            "avg_days": stats["avg_days"],
            "median_days": stats["median_days"],
            "count": stats["count"],
            "outlier_count": stats["outlier_count"],
            "p95_threshold": stats["p95_threshold"],
            "excluded_old_count": excluded_old,
            "raw_avg_days": avg,
            "raw_median_days": med,
            "raw_count": len(lead_times),
        })

    # 週次クローズ・対応中数（同じループで起案数と閉じ率も集計）
    weekly_closed = []
    weekly_created = []
    weekly_close_rate = []
    for start, end in week_ranges[-8:]:  # 直近8週
        issues = _get_closed_in_range(client, conf, start, end)
        created_count = _get_created_in_range(client, conf, start, end)
        label = start.strftime("%m/%d")
        closed_count = len(issues)
        weekly_closed.append({"week": label, "count": closed_count})
        weekly_created.append({"week": label, "count": created_count})
        # EPGPRD-311: 同一週内の close/create 比率
        weekly_close_rate.append({
            "week": label,
            "closed": closed_count,
            "created": created_count,
            "rate": _safe_rate(closed_count, created_count),
        })

    # 週次リードタイム（直近12週）
    weekly_leadtime = []
    for start, end in week_ranges[-12:]:
        issues = _get_closed_in_range(client, conf, start, end)
        lead_times = []
        excluded_old = 0
        for issue in issues:
            created_str = issue["fields"].get("created")
            resolution_str = issue["fields"].get("resolutiondate")
            if not created_str:
                continue
            created = _parse_jira_dt(created_str)
            # EPGPRD-314: 期間外に作成された古いチケットは除外
            if created < start:
                excluded_old += 1
                continue
            if resolution_str:
                resolved = _parse_jira_dt(resolution_str)
            else:
                resolved = end
            days = (resolved - created).days
            if days >= 0:
                lead_times.append(days)
        avg = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0
        med = round(median(lead_times), 1) if lead_times else 0
        stats = _calc_leadtime_stats(lead_times)
        label = start.strftime("%m/%d")
        weekly_leadtime.append({
            "week": label,
            "avg_days": stats["avg_days"],
            "median_days": stats["median_days"],
            "count": stats["count"],
            "outlier_count": stats["outlier_count"],
            "p95_threshold": stats["p95_threshold"],
            "excluded_old_count": excluded_old,
            "raw_avg_days": avg,
            "raw_median_days": med,
            "raw_count": len(lead_times),
        })

    # 現在の対応中数
    in_progress = _get_in_progress(client, conf)
    current_wip = len(in_progress)

    return {
        "monthly_leadtime": monthly_leadtime,
        "weekly_leadtime": weekly_leadtime,
        "weekly_closed": weekly_closed,
        "weekly_created": weekly_created,
        "weekly_close_rate": weekly_close_rate,
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
        member_excluded: dict[str, int] = {}
        for issue in issues:
            name = _assignee_name(issue)
            created_str = issue["fields"].get("created")
            resolution_str = issue["fields"].get("resolutiondate")
            if not created_str:
                continue
            created = _parse_jira_dt(created_str)
            # EPGPRD-314: 期間外作成チケットはリードタイム集計から除外
            if created < start:
                member_excluded[name] = member_excluded.get(name, 0) + 1
                continue
            resolved = _parse_jira_dt(resolution_str) if resolution_str else end
            days = (resolved - created).days
            if days >= 0:
                if name not in member_lt:
                    member_lt[name] = []
                member_lt[name].append(days)

        for name, times in member_lt.items():
            if name not in members:
                members[name] = []
            stats = _calc_leadtime_stats(times)
            members[name].append({
                "month": label,
                "avg_days": stats["avg_days"],
                "median_days": stats["median_days"],
                "count": stats["count"],
                "outlier_count": stats["outlier_count"],
                "p95_threshold": stats["p95_threshold"],
                "excluded_old_count": member_excluded.get(name, 0),
                "raw_count": len(times),
            })

    return {"members": members}


def build_stale_ranking(client: JiraClient, conf: cfg.Config) -> list:
    """滞留チケットランキング"""
    label_filter = ""
    if conf.weekly_labels:
        quoted = ", ".join(f'"{l}"' for l in conf.weekly_labels)
        label_filter = f'labels IN ({quoted})'
    stale = check_stale(client, conf, stale_days=3, extra_filter=label_filter)
    base_url = conf.base_url.rstrip("/")
    return [
        {
            "key": t.key,
            "summary": t.summary,
            "assignee": t.assignee,
            "days_stale": t.days_stale,
            "url": f"{base_url}/browse/{t.key}",
        }
        for t in sorted(stale, key=lambda x: -x.days_stale)
    ]


def build_overdue_ranking(client: JiraClient, conf: cfg.Config) -> list:
    """期限超過チケットランキング"""
    now = datetime.now(tz=JST)
    jql = conf.board_jql(
        f'duedate < "{now.strftime("%Y-%m-%d")}" AND duedate IS NOT EMPTY{_label_filter(conf)}',
        order_by="duedate ASC"
    )
    issues = client.search(jql, ["summary", "assignee", "duedate"], max_results=50)
    base_url = conf.base_url.rstrip("/")
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
            "url": f"{base_url}/browse/{issue['key']}",
        })
    return sorted(results, key=lambda x: -x["days_overdue"])


def build_neglected_ranking(client: JiraClient, conf: cfg.Config) -> list[dict]:
    """未完了チケットを起票日からの経過日数順に返す"""
    now = datetime.now(tz=JST)
    jql = conf.board_member_jql(
        f"statusCategory != Done{_label_filter(conf)}",
        order_by="created ASC"
    )
    issues = client.search(jql, ["summary", "assignee", "status", "created", "issuetype"], max_results=1000)
    base_url = conf.base_url.rstrip("/")
    results = []
    for issue in issues:
        created_str = issue["fields"].get("created")
        if not created_str:
            continue
        created = _parse_jira_dt(created_str)
        days = (now - created).days
        results.append({
            "key": issue["key"],
            "summary": issue["fields"].get("summary", ""),
            "assignee": _assignee_name(issue),
            "status": issue["fields"].get("status", {}).get("name", ""),
            "created": created.strftime("%Y-%m-%d"),
            "days_since_created": days,
            "url": f"{base_url}/browse/{issue['key']}",
        })
    return sorted(results, key=lambda x: -x["days_since_created"])[:20]


def build_wip_status(client: JiraClient, conf: cfg.Config) -> dict:
    """WIP超過状況"""
    in_progress = _get_in_progress(client, conf)
    base_url = conf.base_url.rstrip("/")
    by_member: dict[str, list] = {}
    for issue in in_progress:
        name = _assignee_name(issue)
        if name not in by_member:
            by_member[name] = []
        by_member[name].append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "days": (datetime.now(tz=JST) - _parse_jira_dt(issue["fields"]["updated"])).days,
            "url": f"{base_url}/browse/{issue['key']}",
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


def build_calendar_data(client: JiraClient, conf: cfg.Config) -> dict:
    """メンバーごとの未完了チケットをカレンダー表示用に整形"""
    # overviewの「対応中」と同じフィルタ（In Progress + ラベル）を使用
    extra = f'status = "In Progress"{_label_filter(conf)}'
    fields = ["summary", "assignee", "status", "duedate", "created", "updated", "priority"]
    start_field = (conf.start_date_field or "").strip()
    if start_field:
        fields.append(start_field)
    issues = client.search(
        conf.board_member_jql(extra, order_by="assignee ASC, duedate ASC, created ASC"),
        fields,
        max_results=500,
    )

    base_url = conf.base_url.rstrip("/")
    members: dict[str, dict[str, list[dict]]] = {}

    for issue in issues:
        name = _assignee_name(issue)
        if cfg.CALENDAR_MEMBERS and not any(name.startswith(s) for s in cfg.CALENDAR_MEMBERS):
            continue
        f = issue["fields"]
        created = f.get("created")
        if not created:
            continue

        raw_start = f.get(start_field) if start_field else None
        # Jira may return start date as 'YYYY-MM-DD' or full ISO datetime
        if raw_start and "T" in str(raw_start):
            try:
                start_date = _parse_jira_dt(raw_start).date().isoformat()
            except Exception:
                start_date = str(raw_start)[:10]
        else:
            start_date = raw_start or None

        task = {
            "key": issue["key"],
            "summary": f.get("summary", ""),
            "status": (f.get("status") or {}).get("name", ""),
            "dueDate": f.get("duedate"),
            "startDate": start_date,
            "created": _parse_jira_dt(created).date().isoformat(),
            "priority": ((f.get("priority") or {}).get("name")) or "未設定",
            "url": f"{base_url}/browse/{issue['key']}",
        }

        if name not in members:
            members[name] = {"tasks": []}
        members[name]["tasks"].append(task)

    sorted_members = {
        name: {
            "tasks": sorted(
                payload["tasks"],
                key=lambda task: (
                    task["dueDate"] or "9999-12-31",
                    task["startDate"] or task["created"],
                    task["key"],
                ),
            )
        }
        for name, payload in sorted(members.items(), key=lambda item: item[0])
    }

    return {
        "members": sorted_members,
        "generated_at": datetime.now(tz=JST).isoformat(),
    }


def build_kpi_data(client: JiraClient, conf: cfg.Config) -> dict:
    """チームKPI進捗データを生成"""
    from jira_monitor import _resolved_jql, _KPI_TARGET_WEEKLY_CLOSED, _KPI_TARGET_LT_MEDIAN

    now = datetime.now(tz=JST)
    year = now.year

    # 半期判定
    if 4 <= now.month <= 9:
        half_start = datetime(year, 4, 1, tzinfo=JST)
        half_end = datetime(year, 9, 30, 23, 59, 59, tzinfo=JST)
        prev_start = datetime(year - 1, 10, 1, tzinfo=JST)
        prev_end = datetime(year, 3, 31, 23, 59, 59, tzinfo=JST)
        half_label = f"{year}上半期"
        prev_label = f"{year - 1}下半期"
    elif now.month >= 10:
        half_start = datetime(year, 10, 1, tzinfo=JST)
        half_end = datetime(year + 1, 3, 31, 23, 59, 59, tzinfo=JST)
        prev_start = datetime(year, 4, 1, tzinfo=JST)
        prev_end = datetime(year, 9, 30, 23, 59, 59, tzinfo=JST)
        half_label = f"{year}下半期"
        prev_label = f"{year}上半期"
    else:
        half_start = datetime(year - 1, 10, 1, tzinfo=JST)
        half_end = datetime(year, 3, 31, 23, 59, 59, tzinfo=JST)
        prev_start = datetime(year - 1, 4, 1, tzinfo=JST)
        prev_end = datetime(year - 1, 9, 30, 23, 59, 59, tzinfo=JST)
        half_label = f"{year - 1}下半期"
        prev_label = f"{year - 1}上半期"

    # ラベルフィルタ
    label_filter = ""
    if conf.weekly_labels:
        quoted = ", ".join(f'"{l}"' for l in conf.weekly_labels)
        label_filter = f' AND labels IN ({quoted})'

    # 今半期の完了チケット
    current_jql = f'{_resolved_jql(half_start, now)}{label_filter}'
    current_issues = client.search(
        conf.board_member_jql(current_jql),
        ["created", "resolutiondate"],
        max_results=500,
    )
    half_total = len(current_issues)

    # 半期累計の起案数・閉じ率（EPGPRD-309 / EPGPRD-311）
    half_created_total = _get_created_in_range(client, conf, half_start, now)
    half_close_rate = _safe_rate(half_total, half_created_total)

    # リードタイム計算
    lead_times = []
    excluded_old = 0
    for issue in current_issues:
        created_str = issue["fields"].get("created")
        resolved_str = issue["fields"].get("resolutiondate")
        if not created_str or not resolved_str:
            continue
        created = _parse_jira_dt(created_str)
        if created < half_start:
            excluded_old += 1
            continue
        resolved = _parse_jira_dt(resolved_str)
        days = (resolved - created).days
        if days >= 0:
            lead_times.append(days)

    lt_stats = _calc_leadtime_stats(lead_times)
    lt_median = lt_stats["median_days"]
    lt_avg = lt_stats["avg_days"]

    # 経過週数
    weeks_elapsed = round((now - half_start).days / 7.0, 1)
    actual_weekly = round(half_total / weeks_elapsed, 1) if weeks_elapsed > 0 else 0

    # 前期の完了数
    prev_jql = f'{_resolved_jql(prev_start, prev_end)}{label_filter}'
    prev_total = client.count(conf.board_member_jql(prev_jql))
    prev_weeks = (prev_end - prev_start).days / 7.0
    prev_weekly = round(prev_total / prev_weeks, 1) if prev_weeks > 0 else 0

    # 残り週数と必要ペース
    remaining_weeks = max((half_end - now).days / 7.0, 0.1)
    target_total_by_end = _KPI_TARGET_WEEKLY_CLOSED * (weeks_elapsed + remaining_weeks)
    needed_remaining = max(target_total_by_end - half_total, 0)
    needed_weekly = round(needed_remaining / remaining_weeks, 1)

    return {
        "half_label": half_label,
        "prev_label": prev_label,
        "targets": {
            "weekly_closed": _KPI_TARGET_WEEKLY_CLOSED,
            "lead_time_median": _KPI_TARGET_LT_MEDIAN,
        },
        "current": {
            "total_closed": half_total,
            "total_created": half_created_total,
            "close_rate": half_close_rate,
            "weekly_closed": actual_weekly,
            "weeks_elapsed": weeks_elapsed,
            "lead_time_median": lt_median,
            "lead_time_avg": lt_avg,
            "lead_time_sample_count": lt_stats["count"],
            "lead_time_outlier_count": lt_stats["outlier_count"],
            "lead_time_p95_threshold": lt_stats["p95_threshold"],
            "lead_time_excluded_old_count": excluded_old,
            "lead_time_raw_sample_count": len(lead_times),
        },
        "previous": {
            "total_closed": prev_total,
            "weekly_closed": prev_weekly,
        },
        "projection": {
            "remaining_weeks": round(remaining_weeks, 1),
            "needed_weekly_to_hit_target": needed_weekly,
            "projected_total_at_current_pace": round(half_total + actual_weekly * remaining_weeks),
        },
    }


def build_label_cohort_data(client: JiraClient, conf: cfg.Config) -> dict:
    """期間ラベル別の総数・閉じ率・継続率を生成"""
    cohorts = []
    closed_statuses = _jql_list(CLOSE_STATUSES)

    for label in _label_cohort_labels(conf):
        total = client.count(conf.board_member_jql(f'labels = "{label}"'))
        if total <= 0:
            continue

        closed_jql = conf.board_member_jql(
            f'labels = "{label}" AND (status IN ({closed_statuses}) OR resolution IS NOT EMPTY)'
        )
        closed = min(client.count(closed_jql), total)
        open_count = max(total - closed, 0)

        cohorts.append({
            "label": label,
            "total": total,
            "closed": closed,
            "open": open_count,
            "close_rate": round((closed / total) * 100, 1),
            "continuation_rate": round((open_count / total) * 100, 1),
        })

    return {"cohorts": cohorts, "base_url": conf.base_url.rstrip("/")}


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
    added_labels = expand_weekly_labels(client, conf)
    if added_labels:
        print(f"🏷️  ラベル自動展開: +{len(added_labels)} 件 ({', '.join(added_labels[:5])}{'...' if len(added_labels) > 5 else ''})", file=sys.stderr)
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

    print("📥 放置チケットランキングを取得中...")
    neglected = build_neglected_ranking(client, conf)
    _write(out_dir / "neglected_ranking.json", neglected)

    print("📋 WIP状況を取得中...")
    wip = build_wip_status(client, conf)
    _write(out_dir / "wip_status.json", wip)

    print("🗓️  カレンダーデータを取得中...")
    calendar = build_calendar_data(client, conf)
    _write(out_dir / "calendar.json", calendar)

    print("🎯 KPI進捗を取得中...")
    kpi = build_kpi_data(client, conf)
    _write(out_dir / "kpi.json", kpi)

    print("🏷️  期間ラベル別コホートを取得中...")
    label_cohort = build_label_cohort_data(client, conf)
    _write(out_dir / "label_cohort.json", label_cohort)

    meta = {"updated_at": now_str, "data_files": 9}
    _write(out_dir / "meta.json", meta)

    print(f"✅ 完了: {out_dir} に10ファイル出力")


def _write(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
