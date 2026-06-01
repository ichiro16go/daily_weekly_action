"""
jira_monitor.py — Jira 停滞チケット監視スクリプト

使い方:
  python3 master/scripts/jira_monitor.py --check stale
  python3 master/scripts/jira_monitor.py --check stale --notify slack
  python3 master/scripts/jira_monitor.py --weekly
  python3 master/scripts/jira_monitor.py --weekly --notify confluence
"""

import argparse
import base64
import json
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

import config as cfg
from notifiers import slack as slack_notifier


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class StaleTicket:
    key: str
    summary: str
    assignee: str
    updated: datetime
    days_stale: int


@dataclass
class TicketBrief:
    key: str
    summary: str
    assignee: str
    detail: str = ""


@dataclass
class AssigneeStat:
    name: str
    closed_this_week: int
    in_progress: int


@dataclass
class WeeklySummary:
    period_label: str
    stale: list[StaleTicket]
    overdue: list[TicketBrief]
    unassigned: list[TicketBrief]
    new_tickets_count: int
    closed_count: int
    delta_count: int
    overdue_count: int
    unassigned_count: int
    in_progress_count: int
    trend_4w: list[int]           # [3週前, 2週前, 先週, 今週] のクローズ件数
    assignee_stats: list[AssigneeStat]


@dataclass
class DailyTicket:
    key: str
    summary: str
    assignee: str
    status: str


@dataclass
class AssigneeDailyStat:
    name: str
    completed: list[DailyTicket]    # 今日クローズ
    in_progress: list[DailyTicket]  # 今日更新された IN PROGRESS 系
    pending: list[DailyTicket]      # 今日更新されたペンディング・確認中系


@dataclass
class DailyReport:
    date: str
    closed_count: int
    new_tickets_count: int
    in_progress_count: int
    assignee_stats: list[AssigneeDailyStat]


# ---------------------------------------------------------------------------
# Jira API クライアント
# ---------------------------------------------------------------------------

class JiraClient:
    def __init__(self, conf: cfg.Config):
        self.base_url = conf.base_url
        token = base64.b64encode(f"{conf.email}:{conf.api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request_json(self, method: str, path: str, payload: dict | None = None, query: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            detail = f"HTTP {e.code} {e.reason}"
            if body:
                detail = f"{detail}: {body}"
            raise RuntimeError(detail) from e

    def _search_once(
        self,
        jql: str,
        fields: list[str],
        max_results: int,
        next_page_token: str | None = None,
    ) -> dict:
        # JQLが長い場合にGETのURL長制限で接続リセットされるためPOSTを使う
        payload: dict = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        return self._request_json("POST", "/rest/api/3/search/jql", payload=payload)

    def search(self, jql: str, fields: list[str], max_results: int = 100) -> list[dict]:
        """JQL で Jira を検索し、全件をページネーションして返す"""
        results = []
        next_page_token = None
        while True:
            page_size = min(max_results - len(results), 100)
            if page_size <= 0:
                break

            data = self._search_once(jql, fields, page_size, next_page_token=next_page_token)
            page_issues = data.get("issues", [])
            results.extend(page_issues)

            if len(results) >= max_results:
                break
            if data.get("isLast", True):
                break

            next_page_token = data.get("nextPageToken")
            if not next_page_token or not page_issues:
                break
        return results

    def count(self, jql: str) -> int:
        payload = {"jql": jql}
        data = self._request_json("POST", "/rest/api/3/search/approximate-count", payload=payload)
        return data["count"]


# ---------------------------------------------------------------------------
# チェック関数
# ---------------------------------------------------------------------------

JST = timezone(timedelta(hours=9))
CLOSE_STATUSES = ("Done", "完了", "Close", "Resolved", "解決済み", "リリース済み")


def _jql_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _jql_list(values: tuple[str, ...]) -> str:
    return ", ".join(_jql_quote(v) for v in values)


def _jql_datetime(dt: datetime) -> str:
    return _jql_quote(dt.astimezone(JST).strftime("%Y/%m/%d %H:%M"))


def _closed_transition_jql(after: str, before: str | None = None) -> str:
    clauses = []
    for status in CLOSE_STATUSES:
        clause = f"status CHANGED TO {_jql_quote(status)} AFTER {after}"
        if before:
            clause = f"{clause} BEFORE {before}"
        clauses.append(clause)
    return f"status IN ({_jql_list(CLOSE_STATUSES)}) AND ({' OR '.join(clauses)})"


def _assignee_name(issue: dict) -> str:
    return (issue["fields"].get("assignee") or {}).get("displayName", "未アサイン")


def _summary(issue: dict, limit: int = 60) -> str:
    return issue["fields"]["summary"][:limit]


def _brief(issue: dict, detail: str = "") -> TicketBrief:
    return TicketBrief(
        key=issue["key"],
        summary=_summary(issue),
        assignee=_assignee_name(issue),
        detail=detail,
    )


def _period_label(start: datetime, end: datetime) -> str:
    return (
        f"{start.astimezone(JST).strftime('%Y-%m-%d %H:%M')}"
        f" 〜 {end.astimezone(JST).strftime('%Y-%m-%d %H:%M')}（直近7日）"
    )


def _parse_jira_dt(s: str) -> datetime:
    """Jira の updated 文字列を datetime に変換"""
    # "2025-06-18T14:00:46.129+0900" 形式
    return datetime.fromisoformat(s)


def check_stale(client: JiraClient, conf: cfg.Config, stale_days: int = 3) -> list[StaleTicket]:
    """stale_days 以上更新されていない IN PROGRESS チケットを返す（ボードJQLベース）"""
    jql = conf.board_jql(f'status = "In PROGRESS" AND updated <= -{stale_days}d', order_by="updated ASC")
    issues = client.search(jql, ["summary", "assignee", "updated"], max_results=200)

    now = datetime.now(tz=JST)
    tickets = []
    for issue in issues:
        updated = _parse_jira_dt(issue["fields"]["updated"])
        days = (now - updated).days
        assignee = (issue["fields"].get("assignee") or {}).get("displayName", "未アサイン")
        tickets.append(StaleTicket(
            key=issue["key"],
            summary=issue["fields"]["summary"][:60],
            assignee=assignee,
            updated=updated,
            days_stale=days,
        ))
    return tickets


def build_weekly_summary(client: JiraClient, conf: cfg.Config) -> WeeklySummary:
    stale = check_stale(client, conf, stale_days=7)

    period_end = datetime.now(tz=JST).replace(second=0, microsecond=0)
    period_start = period_end - timedelta(days=7)
    period_start_jql = _jql_datetime(period_start)
    period_end_jql = _jql_datetime(period_end)
    closed_period_jql = _closed_transition_jql(period_start_jql, before=period_end_jql)
    created_period_jql = f"created >= {period_start_jql} AND created <= {period_end_jql}"

    new_tickets_count = client.count(conf.board_member_jql(created_period_jql))
    closed_count = client.count(conf.board_member_jql(closed_period_jql))
    delta_count = new_tickets_count - closed_count
    overdue_count = client.count(conf.board_jql('duedate < now()'))
    unassigned_count = client.count(conf.board_jql('assignee IS EMPTY'))
    in_progress_count = client.count(conf.board_jql('status = "In PROGRESS"'))

    # 4週分クローズ件数トレンド（board_member_jql = ボードメンバー限定・statusフィルタなし）
    trend_4w = []
    week_ranges = [
        (period_end - timedelta(days=28), period_end - timedelta(days=21)),
        (period_end - timedelta(days=21), period_end - timedelta(days=14)),
        (period_end - timedelta(days=14), period_end - timedelta(days=7)),
        (period_start, period_end),
    ]
    for start, end in week_ranges:
        count = client.count(
            conf.board_member_jql(_closed_transition_jql(_jql_datetime(start), before=_jql_datetime(end)))
        )
        trend_4w.append(count)

    # 全ボードメンバーを先に列挙して空エントリ初期化（daily と同じアプローチ）
    all_board_issues = client.search(
        conf.board_jql(order_by="assignee ASC"),
        ["assignee"],
        max_results=500,
    )
    # 担当者別集計: IN PROGRESS ＋ 今週クローズ（ともにボードメンバー限定）
    in_progress_issues = client.search(
        conf.board_jql('status = "In PROGRESS"'),
        ["assignee"],
        max_results=500,
    )
    closed_week_issues = client.search(
        conf.board_member_jql(closed_period_jql),
        ["assignee"],
        max_results=500,
    )
    overdue_issues = client.search(
        conf.board_jql('duedate < now()', order_by="duedate ASC"),
        ["summary", "assignee", "duedate"],
        max_results=5,
    )
    unassigned_issues = client.search(
        conf.board_jql('assignee IS EMPTY', order_by="created ASC"),
        ["summary", "assignee", "created"],
        max_results=5,
    )

    assignee_map: dict[str, AssigneeStat] = {}
    for issue in all_board_issues:
        name = _assignee_name(issue)
        if name not in assignee_map:
            assignee_map[name] = AssigneeStat(name=name, closed_this_week=0, in_progress=0)
    for issue in in_progress_issues:
        name = _assignee_name(issue)
        if name not in assignee_map:
            assignee_map[name] = AssigneeStat(name=name, closed_this_week=0, in_progress=0)
        assignee_map[name].in_progress += 1
    for issue in closed_week_issues:
        name = _assignee_name(issue)
        if name not in assignee_map:
            assignee_map[name] = AssigneeStat(name=name, closed_this_week=0, in_progress=0)
        assignee_map[name].closed_this_week += 1

    assignee_stats = sorted(assignee_map.values(), key=lambda x: x.closed_this_week, reverse=True)
    overdue = [
        _brief(issue, detail=f"期限: {issue['fields'].get('duedate') or '-'}")
        for issue in overdue_issues
    ]
    unassigned = [_brief(issue) for issue in unassigned_issues]

    return WeeklySummary(
        period_label=_period_label(period_start, period_end),
        stale=stale,
        overdue=overdue,
        unassigned=unassigned,
        new_tickets_count=new_tickets_count,
        closed_count=closed_count,
        delta_count=delta_count,
        overdue_count=overdue_count,
        unassigned_count=unassigned_count,
        in_progress_count=in_progress_count,
        trend_4w=trend_4w,
        assignee_stats=assignee_stats,
    )


# ペンディング・確認中と判断するステータス名
_PENDING_LIKE = {"ペンディング", "Pending", "確認中", "保留", "待ち"}


def build_daily_report(client: JiraClient, conf: cfg.Config) -> DailyReport:
    today_str = datetime.now(tz=JST).strftime("%Y-%m-%d")

    # 今日クローズしたチケット（ボードJQLは完了除外なので board_member_jql ベース）
    closed_extra_jql = _closed_transition_jql("startOfDay()")
    closed_count = client.count(conf.board_member_jql(closed_extra_jql))
    closed_jql = conf.board_member_jql(closed_extra_jql, order_by="assignee ASC")
    closed_issues = client.search(
        closed_jql,
        ["summary", "assignee", "status"],
        max_results=200,
    )
    # 今日新規起票（完了済みも含めるため board_member_jql ベース）
    new_count = client.count(conf.board_member_jql('created >= startOfDay()'))
    # 現在アクティブな件数（ボードJQLがそのままアクティブ件数）
    in_progress_count = client.count(conf.board_jql())

    # 全ボードメンバーを先に列挙（assigneeのみ取得でAPI負荷を抑える）
    all_board_issues = client.search(
        conf.board_jql(order_by="assignee ASC"),
        ["assignee"],
        max_results=500,
    )
    # 今日更新があったアクティブチケットのみ詳細取得
    today_active_issues = client.search(
        conf.board_jql('updated >= startOfDay()', order_by="assignee ASC"),
        ["summary", "assignee", "status"],
        max_results=200,
    )

    assignee_map: dict[str, AssigneeDailyStat] = {}

    def get_or_create(name: str) -> AssigneeDailyStat:
        if name not in assignee_map:
            assignee_map[name] = AssigneeDailyStat(
                name=name, completed=[], in_progress=[], pending=[]
            )
        return assignee_map[name]

    # 全ボードメンバーを空エントリで初期化（更新0件でも名前を表示するため）
    for issue in all_board_issues:
        name = _assignee_name(issue)
        get_or_create(name)

    for issue in closed_issues:
        name = _assignee_name(issue)
        get_or_create(name).completed.append(DailyTicket(
            key=issue["key"],
            summary=_summary(issue, limit=50),
            assignee=name,
            status="Close",
        ))

    for issue in today_active_issues:
        name = _assignee_name(issue)
        status_name = (issue["fields"].get("status") or {}).get("name", "")
        ticket = DailyTicket(
            key=issue["key"],
            summary=_summary(issue, limit=50),
            assignee=name,
            status=status_name,
        )
        stat = get_or_create(name)
        if status_name in _PENDING_LIKE or "確認" in status_name or "保留" in status_name:
            stat.pending.append(ticket)
        else:
            stat.in_progress.append(ticket)

    assignee_stats = sorted(
        assignee_map.values(),
        key=lambda x: len(x.completed) + len(x.in_progress) + len(x.pending),
        reverse=True,
    )
    return DailyReport(
        date=today_str,
        closed_count=closed_count,
        new_tickets_count=new_count,
        in_progress_count=in_progress_count,
        assignee_stats=assignee_stats,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------

def format_daily(r: DailyReport) -> str:
    active_stats = [
        stat for stat in r.assignee_stats
        if len(stat.completed) + len(stat.in_progress) + len(stat.pending) > 0
    ]
    inactive_names = [
        stat.name for stat in r.assignee_stats
        if len(stat.completed) + len(stat.in_progress) + len(stat.pending) == 0
    ]
    lines = [
        f"📋 運用保守チーム 日報 ({r.date})",
        "━" * 60,
        f"✅ 本日完了: {r.closed_count}件　📥 新規起票: {r.new_tickets_count}件　🔄 対応中: {r.in_progress_count}件",
        "",
    ]

    if not active_stats:
        lines.append("本日の更新なし")
        lines.append("")
    else:
        lines.append("─ 担当者別 ─")
        for stat in active_stats:
            lines.append(f"👤 {stat.name}")
            for t in stat.completed:
                lines.append(f"  ✅ {t.key}  {t.summary}")
            for t in stat.in_progress:
                lines.append(f"  🔄 {t.key}  {t.summary}")
            for t in stat.pending:
                lines.append(f"  ⏸ {t.key}  {t.summary}  （{t.status}）")
            lines.append("")

    if inactive_names:
        lines.append("─ 更新なし（デバッグ用） ─")
        lines.append(f"  {' / '.join(inactive_names)}")

    return "\n".join(lines).rstrip()


def format_stale(
        tickets: list[StaleTicket], stale_days: int = 3) -> str:
    today = datetime.now(tz=JST).strftime("%Y-%m-%d")
    if not tickets:
        return f"✅ 停滞チケットなし（{stale_days}日以上 IN PROGRESS のチケットは 0件）"

    lines = [
        f"🚨 停滞チケット検出 ({today})",
        f"IN PROGRESS のまま {stale_days}日以上 更新なし — {len(tickets)}件",
        "━" * 60,
    ]
    for t in tickets:
        lines.append(
            f"{t.key:<14} {t.assignee:<16} 最終更新: {t.updated.strftime('%Y-%m-%d')} ({t.days_stale}日前)"
        )
        lines.append(f"  {t.summary}")
    return "\n".join(lines)


def _bar(count: int, max_count: int, width: int = 10) -> str:
    filled = round(count / max_count * width) if max_count > 0 else 0
    return "█" * filled + "░" * (width - filled)


def format_weekly(s: WeeklySummary) -> str:
    today = datetime.now(tz=JST).strftime("%Y-%m-%d")
    lines = [
        f"📊 運用保守チーム 週次レポート ({today})",
        f"対象期間: {s.period_label}",
        "━" * 60,
    ]

    # トレンドグラフ（ASCII棒グラフ）
    labels = ["3週前", "2週前", "先週 ", "今週 "]
    max_count = max(s.trend_4w) if any(s.trend_4w) else 1
    lines.append("📈 週次クローズ件数の推移")
    for label, count in zip(labels, s.trend_4w):
        lines.append(f"  {label}: {_bar(count, max_count)} {count}件")
    lines.append("")

    # 担当者別
    lines.append("─ 担当者別（今週） ─")
    lines.append(f"  {'担当者':<16} {'完了':>5} {'対応中':>6}")
    lines.append(f"  {'─'*16} {'─'*5} {'─'*6}")
    for stat in s.assignee_stats:
        lines.append(f"  {stat.name:<16} {stat.closed_this_week:>4}件 {stat.in_progress:>5}件")
    lines.append("")

    # サマリー
    delta_prefix = "+" if s.delta_count > 0 else ""
    lines += [
        "─ サマリー ─",
        f"  📥 新規起票:                  {s.new_tickets_count}件",
        f"  ✅ 完了:                      {s.closed_count}件",
        f"  📊 増減（新規-完了）:          {delta_prefix}{s.delta_count}件",
        f"  🔄 IN PROGRESS 合計:          {s.in_progress_count}件",
        f"  ⚠️  期限超過:                  {s.overdue_count}件",
        f"  👤 担当者未アサイン:            {s.unassigned_count}件",
        "",
        f"⚠️  期限超過チケット — {s.overdue_count}件",
    ]
    for t in s.overdue:
        detail = f"  {t.detail}" if t.detail else ""
        lines.append(f"  {t.key}  {t.assignee}{detail}  {t.summary}")
    if s.overdue_count > len(s.overdue):
        lines.append(f"  …他 {s.overdue_count - len(s.overdue)}件")
    lines += [
        "",
        f"👤 担当者未アサインチケット — {s.unassigned_count}件",
    ]
    for t in s.unassigned:
        lines.append(f"  {t.key}  {t.summary}")
    if s.unassigned_count > len(s.unassigned):
        lines.append(f"  …他 {s.unassigned_count - len(s.unassigned)}件")
    lines += [
        "",
        f"🚨 滞留チケット（7日以上 IN PROGRESS）— {len(s.stale)}件",
    ]
    for t in s.stale[:5]:
        lines.append(
            f"  {t.key}  {t.assignee}  最終更新: {t.updated.strftime('%Y-%m-%d')} "
            f"({t.days_stale}日前)  {t.summary}"
        )
    if len(s.stale) > 5:
        lines.append(f"  …他 {len(s.stale) - 5}件")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Jira 停滞チケット監視スクリプト")
    parser.add_argument("--check", choices=["stale", "overdue", "unassigned"],
                        help="チェック対象を指定")
    parser.add_argument("--stale-days", type=int, default=3,
                        help="停滞と判定する日数（デフォルト: 3）")
    parser.add_argument("--daily", action="store_true",
                        help="日報を生成（本日更新チケットを担当者別に表示）")
    parser.add_argument("--weekly", action="store_true",
                        help="週次サマリーを生成")
    parser.add_argument("--notify", choices=["slack", "confluence"],
                        help="通知先を指定（省略時は標準出力のみ）")
    args = parser.parse_args()

    if not args.weekly and not args.daily and not args.check:
        parser.print_help()
        sys.exit(0)

    try:
        conf = cfg.load()
    except EnvironmentError as e:
        print(f"❌ 設定エラー: {e}", file=sys.stderr)
        print("→ .env.example をコピーして .env を作成し、環境変数を設定してください", file=sys.stderr)
        sys.exit(1)

    client = JiraClient(conf)

    try:
        if args.daily:
            report = build_daily_report(client, conf)
            text = format_daily(report)
            print(text)
            if args.notify == "slack":
                slack_notifier.post(conf, text)

        elif args.weekly:
            summary = build_weekly_summary(client, conf)
            text = format_weekly(summary)
            print(text)
            if args.notify == "slack":
                slack_notifier.post(conf, text)
            elif args.notify == "confluence":
                print("⚠️  Confluence 通知は未実装です", file=sys.stderr)

        elif args.check == "stale":
            tickets = check_stale(client, conf, stale_days=args.stale_days)
            text = format_stale(tickets, stale_days=args.stale_days)
            print(text)
            if args.notify == "slack":
                slack_notifier.post(conf, text)

        else:
            parser.print_help()
    except RuntimeError as e:
        print(f"❌ Jira API エラー: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
