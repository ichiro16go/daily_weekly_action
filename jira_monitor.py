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
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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
class LeadTimeStat:
    """月次リードタイム統計"""

    month_label: str  # "2026-01" 形式
    avg_days: float  # 平均リードタイム（日）
    median_days: float  # 中央値リードタイム（日）
    count: int  # サンプル数


@dataclass
class WipViolation:
    """WIP上限超過"""

    name: str
    in_progress: int
    limit: int


@dataclass
class KpiProgress:
    """チームKPI進捗"""

    # 週完了数
    target_weekly_closed: float  # 目標（件/週）
    actual_weekly_closed: float  # 実績（件/週）
    half_total_closed: int       # 上半期累計完了数
    half_weeks_elapsed: float    # 経過週数
    # リードタイム中央値
    target_lead_time_median: float  # 目標（日）
    actual_lead_time_median: float  # 実績（日）
    lead_time_sample_count: int     # サンプル数
    # 前期参考
    prev_half_total: int         # 前期完了数
    prev_half_weekly: float      # 前期週平均


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
    trend_4w: list[int]  # [3週前, 2週前, 先週, 今週] のクローズ件数
    assignee_stats: list[AssigneeStat]
    new_tickets: list[TicketBrief] = None  # 新規起票チケット一覧
    label_filter_name: str = ""               # 適用したラベル名（表示用）
    lead_time_trend: list[LeadTimeStat] = None   # 月次リードタイム推移
    wip_violations: list[WipViolation] = None    # WIP上限超過者
    kpi: KpiProgress = None                      # チームKPI進捗
    filter_urls: dict[str, str] = None           # セクション別Jiraフィルター URL


@dataclass
class DailyTicket:
    key: str
    summary: str
    assignee: str
    status: str


@dataclass
class AssigneeDailyStat:
    name: str
    completed: list[DailyTicket]  # 今日クローズ
    in_progress: list[DailyTicket]  # 今日更新された IN PROGRESS 系
    pending: list[DailyTicket]  # 今日更新されたペンディング・確認中系


@dataclass
class DailyReport:
    date: str
    closed_count: int
    new_tickets_count: int
    in_progress_count: int
    assignee_stats: list[AssigneeDailyStat]


# ---------------------------------------------------------------------------
# Jira フィルター URL ヘルパー
# ---------------------------------------------------------------------------


def _jira_filter_url(base_url: str, jql: str) -> str:
    """JQL から Jira Issues 検索ページの URL を生成する"""
    return f"{base_url}/issues/?jql={urllib.parse.quote(jql, safe='')}"


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

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        query: dict | None = None,
    ) -> dict:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=self.headers, method=method
        )
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
        expand: str | None = None,
        next_page_token: str | None = None,
    ) -> dict:
        # JQLが長い場合にGETのURL長制限で接続リセットされるためPOSTを使う
        payload: dict = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
        }
        if expand:
            payload["expand"] = expand
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        return self._request_json("POST", "/rest/api/3/search/jql", payload=payload)

    def search(
        self,
        jql: str,
        fields: list[str],
        max_results: int = 100,
        expand: str | None = None,
    ) -> list[dict]:
        """JQL で Jira を検索し、全件をページネーションして返す"""
        results = []
        next_page_token = None
        while True:
            page_size = min(max_results - len(results), 100)
            if page_size <= 0:
                break

            data = self._search_once(
                jql, fields, page_size, expand=expand, next_page_token=next_page_token
            )
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

    def get_issue(
        self,
        key: str,
        fields: list[str] | None = None,
        expand: str | None = None,
    ) -> dict:
        query: dict[str, str] = {}
        if fields:
            query["fields"] = ",".join(fields)
        if expand:
            query["expand"] = expand
        return self._request_json("GET", f"/rest/api/3/issue/{key}", query=query or None)

    def count(self, jql: str) -> int:
        payload = {"jql": jql}
        data = self._request_json(
            "POST", "/rest/api/3/search/approximate-count", payload=payload
        )
        return data["count"]

    def fetch_label_suggestions(self, prefix: str) -> list[str]:
        """Jira のラベル自動補完 API を使って prefix にマッチするラベル値を返す。

        Endpoint: GET /rest/api/3/jql/autocompletedata/suggestions
        ?fieldName=labels&fieldValue={prefix}

        Jira は最大 ~100 件を返す。ラベル数がそれを超える運用は想定外。
        """
        data = self._request_json(
            "GET",
            "/rest/api/3/jql/autocompletedata/suggestions",
            query={"fieldName": "labels", "fieldValue": prefix},
        )
        results = data.get("results", []) or []
        # value はハイライト用に <b>...</b> が混ざることがあるため除去
        labels: list[str] = []
        for item in results:
            v = item.get("value") or ""
            v = v.replace("<b>", "").replace("</b>", "")
            if v:
                labels.append(v)
        return labels


def _fetch_labels_recursive(
    client: "JiraClient",
    prefix: str,
    *,
    threshold: int = 15,
    depth: int = 0,
    max_depth: int = 8,
) -> set[str]:
    """Jira autocomplete API は ~15 件で結果をキャップするため、上限に達したら
    `prefix + 0..9` で再帰的に深掘りして取りこぼしを防ぐ。

    threshold: この件数以上返ったら深掘り対象とみなす
    max_depth: 暴走防止（YYYYMMDD まで対応する 8 桁を想定）
    """
    out = set(client.fetch_label_suggestions(prefix))
    if len(out) >= threshold and depth < max_depth:
        for d in "0123456789":
            out.update(
                _fetch_labels_recursive(
                    client, prefix + d, threshold=threshold, depth=depth + 1, max_depth=max_depth
                )
            )
    return out


def expand_weekly_labels(client: "JiraClient", conf: cfg.Config) -> list[str]:
    """conf.weekly_label_pattern が指定されていれば Jira から該当ラベルを取得して
    conf.weekly_labels に追加する。重複は除去。

    Jira の autocomplete API は前方一致で上位 ~15 件しか返さないため、
    `_fetch_labels_recursive` で件数キャップ時に深掘りして全件取得する。

    展開に失敗した場合は元のラベルを保持して警告のみ出す（実行は続ける）。
    Returns 追加された新規ラベル一覧（ログ用）。
    """
    import re as _re

    pattern = getattr(conf, "weekly_label_pattern", None)
    if not pattern:
        return []

    try:
        regex = _re.compile(pattern)
    except _re.error as e:
        print(f"⚠️  WEEKLY_LABEL_PATTERN が不正な正規表現です: {e}", file=sys.stderr)
        return []

    # prefix 推定: 正規表現の先頭にある固定文字列を抜き出す（^を除く、最初のメタ文字で終わる）
    prefix_match = _re.match(r"^\^?([^\\\[\(\.\*\+\?\{\|]+)", pattern)
    prefix = prefix_match.group(1) if prefix_match else ""
    if not prefix:
        print(
            "⚠️  WEEKLY_LABEL_PATTERN から prefix を抽出できませんでした。ラベル展開をスキップ",
            file=sys.stderr,
        )
        return []

    try:
        candidates = _fetch_labels_recursive(client, prefix)
    except (RuntimeError, urllib.error.URLError) as e:
        print(f"⚠️  ラベル候補取得失敗（既存ラベルのまま続行）: {e}", file=sys.stderr)
        return []

    matched = [label for label in candidates if regex.match(label)]
    existing = set(conf.weekly_labels)
    added = sorted(label for label in matched if label not in existing)
    if added:
        conf.weekly_labels = list(conf.weekly_labels) + added
    return added


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


def _resolved_jql(start: datetime, end: datetime) -> str:
    """resolved フィールドで期間指定（transition式より正確）"""
    return (
        f'status IN ({_jql_list(CLOSE_STATUSES)}) '
        f'AND resolved >= "{start.strftime("%Y-%m-%d")}" '
        f'AND resolved <= "{end.strftime("%Y-%m-%d")}"'
    )


def _assignee_name(issue: dict) -> str:
    return (issue["fields"].get("assignee") or {}).get("displayName", "未アサイン")


def _assignee_name_at_close(issue: dict) -> str:
    """クローズ時点の担当者を changelog から逆算する。"""
    fields = issue.get("fields") or {}
    resolved_str = fields.get("resolutiondate")
    if not resolved_str:
        return _assignee_name(issue)

    try:
        resolved_at = _parse_jira_dt(resolved_str)
    except Exception:
        return _assignee_name(issue)

    assignee = _assignee_name(issue)
    histories = sorted(
        (issue.get("changelog") or {}).get("histories", []),
        key=lambda h: h.get("created", ""),
        reverse=True,
    )
    for history in histories:
        created_str = history.get("created")
        if not created_str:
            continue
        try:
            history_dt = _parse_jira_dt(created_str)
        except Exception:
            continue
        if history_dt < resolved_at:
            continue
        for item in history.get("items") or []:
            if item.get("field") != "assignee":
                continue
            to_name = item.get("toString") or "未アサイン"
            from_name = item.get("fromString") or "未アサイン"
            if assignee == to_name:
                assignee = from_name
            elif assignee == "未アサイン" and from_name != "未アサイン":
                assignee = from_name
    return assignee or "未アサイン"


def _closed_issues_with_history(
    client: JiraClient,
    conf: cfg.Config,
    start,
    end,
    extra_filter: str = "",
) -> list[dict]:
    """クローズ済みチケットを changelog 付きで返す。"""
    issues = client.search(
        conf.board_member_jql(f"{_resolved_jql(start, end)}{extra_filter}"),
        ["summary", "assignee", "created", "resolutiondate", "issuetype"],
        max_results=500,
        expand="changelog",
    )
    if all("changelog" in issue for issue in issues):
        return issues

    detailed_issues = []
    for issue in issues:
        if "changelog" in issue:
            detailed_issues.append(issue)
            continue
        detailed_issues.append(
            client.get_issue(
                issue["key"],
                fields=["summary", "assignee", "created", "resolutiondate", "issuetype"],
                expand="changelog",
            )
        )
    return detailed_issues


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


def check_stale(
    client: JiraClient, conf: cfg.Config, stale_days: int = 3, extra_filter: str = ""
) -> list[StaleTicket]:
    """stale_days 以上更新されていない IN PROGRESS チケットを返す（ボードJQLベース）"""
    condition = f'status = "In PROGRESS" AND updated <= -{stale_days}d'
    if extra_filter:
        condition = f"{condition} AND {extra_filter}"
    jql = conf.board_jql(condition, order_by="updated ASC")
    issues = client.search(jql, ["summary", "assignee", "updated"], max_results=200)

    now = datetime.now(tz=JST)
    tickets = []
    for issue in issues:
        updated = _parse_jira_dt(issue["fields"]["updated"])
        days = (now - updated).days
        assignee = (issue["fields"].get("assignee") or {}).get(
            "displayName", "未アサイン"
        )
        tickets.append(
            StaleTicket(
                key=issue["key"],
                summary=issue["fields"]["summary"][:60],
                assignee=assignee,
                updated=updated,
                days_stale=days,
            )
        )
    return tickets


def _calc_lead_time_trend(
    client: JiraClient, conf: cfg.Config, months: int = 6
) -> list:
    """直近 N ヶ月のリードタイム（起票→解決の日数）を月次で集計する"""
    from statistics import median

    now = datetime.now(tz=JST)
    results = []

    for i in range(months, 0, -1):
        # 各月の範囲を計算
        month_end = (
            now.replace(day=1) - timedelta(days=1)
            if i == 1
            else now.replace(day=1) - timedelta(days=30 * (i - 1))
        )
        # 簡易的に月初〜月末を算出
        year = now.year
        month = now.month - i + 1
        if month <= 0:
            month += 12
            year -= 1
        month_start = datetime(year, month, 1, tzinfo=JST)
        if month == 12:
            month_end_dt = datetime(year + 1, 1, 1, tzinfo=JST) - timedelta(seconds=1)
        else:
            month_end_dt = datetime(year, month + 1, 1, tzinfo=JST) - timedelta(
                seconds=1
            )

        month_label = f"{year}-{month:02d}"
        start_jql = _jql_datetime(month_start)
        end_jql = _jql_datetime(month_end_dt)

        # その月にクローズされたチケットの created を取得
        closed_jql = conf.board_member_jql(
            _closed_transition_jql(start_jql, before=end_jql)
        )
        issues = client.search(closed_jql, ["created"], max_results=500)

        lead_times = []
        for issue in issues:
            created_str = issue["fields"].get("created")
            if not created_str:
                continue
            created = _parse_jira_dt(created_str)
            # クローズ日はその月のどこかだが、正確な日は changelog が必要
            # 簡易計算: 月末 - created で近似（上限は月末で切る）
            resolved_approx = min(month_end_dt, now)
            days = (resolved_approx - created).days
            if days >= 0:
                lead_times.append(days)

        avg_days = sum(lead_times) / len(lead_times) if lead_times else 0
        med_days = median(lead_times) if lead_times else 0

        results.append(
            LeadTimeStat(
                month_label=month_label,
                avg_days=round(avg_days, 1),
                median_days=round(med_days, 1),
                count=len(lead_times),
            )
        )

    return results


# KPI 目標設定（config化したい場合は config.py に移動）
_KPI_TARGET_WEEKLY_CLOSED = 9.0    # 週完了数目標
_KPI_TARGET_LT_MEDIAN = 21.0      # リードタイム中央値目標（日）

# 半期の境界
_HALF_YEAR_BOUNDARIES = {
    # (start, end, prev_start, prev_end)
    "upper": ("04-01", "09-30", "10-01", "03-31"),  # 上半期: 4月〜9月
    "lower": ("10-01", "03-31", "04-01", "09-30"),  # 下半期: 10月〜3月
}


def _calc_kpi_progress(client: JiraClient, conf: cfg.Config) -> KpiProgress:
    """半期KPI進捗を計算"""
    from statistics import median as _median

    now = datetime.now(tz=JST)
    year = now.year

    # 今が上半期(4-9)か下半期(10-3)かを判定
    if now.month >= 4 and now.month <= 9:
        half_start = datetime(year, 4, 1, tzinfo=JST)
        half_end = datetime(year, 9, 30, 23, 59, 59, tzinfo=JST)
        prev_start = datetime(year - 1, 10, 1, tzinfo=JST)
        prev_end = datetime(year, 3, 31, 23, 59, 59, tzinfo=JST)
    else:
        if now.month >= 10:
            half_start = datetime(year, 10, 1, tzinfo=JST)
            half_end = datetime(year + 1, 3, 31, 23, 59, 59, tzinfo=JST)
            prev_start = datetime(year, 4, 1, tzinfo=JST)
            prev_end = datetime(year, 9, 30, 23, 59, 59, tzinfo=JST)
        else:
            half_start = datetime(year - 1, 10, 1, tzinfo=JST)
            half_end = datetime(year, 3, 31, 23, 59, 59, tzinfo=JST)
            prev_start = datetime(year - 1, 4, 1, tzinfo=JST)
            prev_end = datetime(year - 1, 9, 30, 23, 59, 59, tzinfo=JST)

    # ラベルフィルタ
    label_filter = ""
    if conf.weekly_labels:
        quoted = ", ".join(f'"{l}"' for l in conf.weekly_labels)
        label_filter = f' AND labels IN ({quoted})'

    # 今半期の完了数
    current_jql = (
        f'{_resolved_jql(half_start, now)}{label_filter}'
    )
    half_total = client.count(conf.board_member_jql(current_jql))

    # 今半期のリードタイム（resolved フィールドベース）
    current_issues = client.search(
        conf.board_member_jql(current_jql),
        ["created", "resolutiondate"],
        max_results=500,
    )
    lead_times = []
    for issue in current_issues:
        created_str = issue["fields"].get("created")
        resolved_str = issue["fields"].get("resolutiondate")
        if not created_str or not resolved_str:
            continue
        created = _parse_jira_dt(created_str)
        resolved = _parse_jira_dt(resolved_str)
        days = (resolved - created).days
        if days >= 0:
            lead_times.append(days)

    lt_median = _median(lead_times) if lead_times else 0

    # 経過週数
    weeks_elapsed = (now - half_start).days / 7.0
    actual_weekly = half_total / weeks_elapsed if weeks_elapsed > 0 else 0

    # 前期の完了数
    prev_jql = (
        f'{_resolved_jql(prev_start, prev_end)}{label_filter}'
    )
    prev_total = client.count(conf.board_member_jql(prev_jql))
    prev_weeks = (prev_end - prev_start).days / 7.0
    prev_weekly = prev_total / prev_weeks if prev_weeks > 0 else 0

    return KpiProgress(
        target_weekly_closed=_KPI_TARGET_WEEKLY_CLOSED,
        actual_weekly_closed=round(actual_weekly, 1),
        half_total_closed=half_total,
        half_weeks_elapsed=round(weeks_elapsed, 1),
        target_lead_time_median=_KPI_TARGET_LT_MEDIAN,
        actual_lead_time_median=round(lt_median, 1),
        lead_time_sample_count=len(lead_times),
        prev_half_total=prev_total,
        prev_half_weekly=round(prev_weekly, 1),
    )


def build_weekly_summary(client: JiraClient, conf: cfg.Config) -> WeeklySummary:
    # ラベルフィルタ構築（OR）: labels IN ("運用保守", "運用保守保留案件")
    if conf.weekly_labels:
        quoted = ", ".join(f'"{l}"' for l in conf.weekly_labels)
        label_filter = f"labels IN ({quoted})"
    else:
        label_filter = ""

    def _and_label(base: str) -> str:
        """label_filter が空でなければ AND で結合する"""
        if not label_filter:
            return base
        return f"{base} AND {label_filter}"

    stale = check_stale(client, conf, stale_days=7, extra_filter=label_filter)

    period_end = datetime.now(tz=JST).replace(second=0, microsecond=0)
    period_start = period_end - timedelta(days=7)
    period_start_jql = _jql_datetime(period_start)
    period_end_jql = _jql_datetime(period_end)
    resolved_period_jql = _resolved_jql(period_start, period_end)
    created_period_jql = (
        f"created >= {period_start_jql} AND created <= {period_end_jql}"
    )

    # 集計（ラベルフィルタが空なら全件対象）
    new_tickets_count = client.count(
        conf.board_member_jql(_and_label(created_period_jql))
    )
    closed_count = client.count(conf.board_member_jql(_and_label(resolved_period_jql)))
    delta_count = new_tickets_count - closed_count
    overdue_count = client.count(conf.board_jql(_and_label("duedate < now()")))
    unassigned_count = client.count(conf.board_jql(_and_label("assignee IS EMPTY")))
    in_progress_count = client.count(
        conf.board_jql(_and_label('status = "In PROGRESS"'))
    )

    # 新規起票チケット一覧
    new_ticket_issues = client.search(
        conf.board_member_jql(_and_label(created_period_jql), order_by="created DESC"),
        ["summary", "assignee", "created"],
        max_results=20,
    )
    new_tickets = [_brief(issue) for issue in new_ticket_issues]

    # 4週分クローズ件数トレンド（resolved ベース）
    trend_4w = []
    week_ranges = [
        (period_end - timedelta(days=28), period_end - timedelta(days=21)),
        (period_end - timedelta(days=21), period_end - timedelta(days=14)),
        (period_end - timedelta(days=14), period_end - timedelta(days=7)),
        (period_start, period_end),
    ]
    for start, end in week_ranges:
        count = client.count(
            conf.board_member_jql(_and_label(_resolved_jql(start, end)))
        )
        trend_4w.append(count)

    # 全ボードメンバーを先に列挙して空エントリ初期化
    all_board_issues = client.search(
        conf.board_jql(label_filter or None, order_by="assignee ASC")
        if label_filter
        else conf.board_jql(order_by="assignee ASC"),
        ["assignee"],
        max_results=500,
    )
    # 担当者別集計
    in_progress_issues = client.search(
        conf.board_jql(_and_label('status = "In PROGRESS"')),
        ["assignee"],
        max_results=500,
    )
    closed_week_issues = _closed_issues_with_history(client, conf, period_start, period_end, f" AND {label_filter}" if label_filter else "")
    overdue_issues = client.search(
        conf.board_jql(_and_label("duedate < now()"), order_by="duedate ASC"),
        ["summary", "assignee", "duedate"],
        max_results=5,
    )
    unassigned_issues = client.search(
        conf.board_jql(_and_label("assignee IS EMPTY"), order_by="created ASC"),
        ["summary", "assignee", "created"],
        max_results=5,
    )

    assignee_map: dict[str, AssigneeStat] = {}
    for issue in all_board_issues:
        name = _assignee_name(issue)
        if name not in assignee_map:
            assignee_map[name] = AssigneeStat(
                name=name, closed_this_week=0, in_progress=0
            )
    for issue in in_progress_issues:
        name = _assignee_name(issue)
        if name not in assignee_map:
            assignee_map[name] = AssigneeStat(
                name=name, closed_this_week=0, in_progress=0
            )
        assignee_map[name].in_progress += 1
    for issue in closed_week_issues:
        name = _assignee_name_at_close(issue)
        if name not in assignee_map:
            assignee_map[name] = AssigneeStat(
                name=name, closed_this_week=0, in_progress=0
            )
        assignee_map[name].closed_this_week += 1

    assignee_stats = sorted(
        assignee_map.values(), key=lambda x: x.closed_this_week, reverse=True
    )
    overdue = [
        _brief(issue, detail=f"終了: {issue['fields'].get('duedate') or '-'}")
        for issue in overdue_issues
    ]
    unassigned = [_brief(issue) for issue in unassigned_issues]

    # WIP上限チェック
    wip_violations = [
        WipViolation(name=stat.name, in_progress=stat.in_progress, limit=conf.wip_limit)
        for stat in assignee_stats
        if stat.in_progress > conf.wip_limit and stat.name != "未アサイン"
    ]

    # リードタイム計算（直近6ヶ月を月次で集計）
    lead_time_trend = _calc_lead_time_trend(client, conf, months=6)

    # チームKPI進捗
    kpi = _calc_kpi_progress(client, conf)

    # セクション別 Jira フィルター URL
    filter_urls = {
        "new_tickets": _jira_filter_url(
            conf.base_url,
            conf.board_member_jql(_and_label(created_period_jql), order_by="created DESC"),
        ),
        "closed": _jira_filter_url(
            conf.base_url,
            conf.board_member_jql(_and_label(resolved_period_jql)),
        ),
        "in_progress": _jira_filter_url(
            conf.base_url,
            conf.board_jql(_and_label('status = "In PROGRESS"')),
        ),
        "overdue": _jira_filter_url(
            conf.base_url,
            conf.board_jql(_and_label("duedate < now()"), order_by="duedate ASC"),
        ),
        "unassigned": _jira_filter_url(
            conf.base_url,
            conf.board_jql(_and_label("assignee IS EMPTY"), order_by="created ASC"),
        ),
        "stale": _jira_filter_url(
            conf.base_url,
            conf.board_jql(
                _and_label('status = "In PROGRESS" AND updated <= -7d'),
                order_by="updated ASC",
            ),
        ),
    }

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
        new_tickets=new_tickets,
        label_filter_name=", ".join(conf.weekly_labels) if conf.weekly_labels else "",
        lead_time_trend=lead_time_trend,
        wip_violations=wip_violations,
        kpi=kpi,
        filter_urls=filter_urls,
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
    new_count = client.count(conf.board_member_jql("created >= startOfDay()"))
    # 現在アクティブな件数（実際に着手中 = In PROGRESS のみ）
    in_progress_count = client.count(conf.board_jql('status = "In PROGRESS"'))

    # 全ボードメンバーを先に列挙（assigneeのみ取得でAPI負荷を抑える）
    all_board_issues = client.search(
        conf.board_jql(order_by="assignee ASC"),
        ["assignee"],
        max_results=500,
    )
    # 今日更新があったアクティブチケットのみ詳細取得
    today_active_issues = client.search(
        conf.board_jql("updated >= startOfDay()", order_by="assignee ASC"),
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
        get_or_create(name).completed.append(
            DailyTicket(
                key=issue["key"],
                summary=_summary(issue, limit=50),
                assignee=name,
                status="Close",
            )
        )

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
        if (
            status_name in _PENDING_LIKE
            or "確認" in status_name
            or "保留" in status_name
        ):
            stat.pending.append(ticket)
        else:
            stat.in_progress.append(ticket)

    assignee_stats = sorted(
        assignee_map.values(),
        key=lambda x: (
            x.name == "未アサイン",
            -(len(x.completed) + len(x.in_progress) + len(x.pending)),
        ),
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


# 日報のフォーマッター。更新のあったチケットを担当者別に表示し、更新なしもデバッグ用に表示する。停滞チケットは別途週次レポートで表示する想定。
def format_daily(r: DailyReport) -> str:
    active_stats = [
        stat
        for stat in r.assignee_stats
        if len(stat.completed) + len(stat.in_progress) + len(stat.pending) > 0
    ]
    inactive_names = [
        stat.name
        for stat in r.assignee_stats
        if len(stat.completed) + len(stat.in_progress) + len(stat.pending) == 0
    ]
    lines = [
        f"📋 運用保守チーム 日報 ({r.date})",
        "本日の更新チケット一覧（更新のあったチケットのみ、担当者別に表示）",
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


def format_stale(tickets: list[StaleTicket], stale_days: int = 3) -> str:
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


# 週次レポートのフォーマッター。ASCII棒グラフでトレンドを表示し、担当者別統計と停滞・期限超過・未アサインチケットの詳細も表示する。
def format_weekly(s: WeeklySummary) -> str:
    today = datetime.now(tz=JST).strftime("%Y-%m-%d")
    lines = [
        f"📊 運用保守チーム 週次レポート ({today})",
        f"対象期間: {s.period_label}",
        f"対象ラベル: {s.label_filter_name or '全件'}",
        "━" * 60,
    ]

    # KPI進捗
    if s.kpi:
        k = s.kpi
        weekly_pct = round(k.actual_weekly_closed / k.target_weekly_closed * 100)
        lt_status = "✅" if k.actual_lead_time_median <= k.target_lead_time_median else "📉"
        weekly_status = "✅" if k.actual_weekly_closed >= k.target_weekly_closed else "📉"
        lines += [
            "🎯 チームKPI進捗（上半期）",
            f"  {weekly_status} 週完了数:       {k.actual_weekly_closed}件/週（目標 {k.target_weekly_closed}件） {weekly_pct}%",
            f"  {lt_status} リードタイム中央値: {k.actual_lead_time_median}日（目標 {k.target_lead_time_median}日）",
            f"  📦 上半期累計:     {k.half_total_closed}件（{k.half_weeks_elapsed}週経過）",
            f"  📊 前期参考:       {k.prev_half_total}件（{k.prev_half_weekly}件/週）",
            "",
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
    lines.append(f"  {'─' * 16} {'─' * 5} {'─' * 6}")
    for stat in s.assignee_stats:
        lines.append(
            f"  {stat.name:<16} {stat.closed_this_week:>4}件 {stat.in_progress:>5}件"
        )
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

    # フィルター URL 一覧
    if s.filter_urls:
        lines += [
            "",
            "─ Jira フィルターリンク ─",
        ]
        url_labels = {
            "new_tickets": "📥 新規起票",
            "closed": "✅ 完了",
            "in_progress": "🔄 対応中",
            "overdue": "⚠️  期限超過",
            "unassigned": "👤 未アサイン",
            "stale": "🚨 滞留",
        }
        for key, label in url_labels.items():
            if key in s.filter_urls:
                lines.append(f"  {label}: {s.filter_urls[key]}")

    return "\n".join(lines)


def format_weekly_blocks(s: WeeklySummary, conf: cfg.Config) -> list[dict]:
    """週報を Slack Block Kit 形式で生成する"""
    from notifiers.slack import (
        context_block,
        divider_block,
        header_block,
        section_block,
        section_fields,
    )

    today = datetime.now(tz=JST).strftime("%Y-%m-%d")
    blocks = []

    # ヘッダー
    blocks.append(header_block(f"📊 運用保守チーム 週次レポート ({today})"))
    ctx = [f"対象期間: {s.period_label}"]
    if conf.weekly_labels:
        ctx.append(f"フィルタ: labels IN ({', '.join(conf.weekly_labels)})")
    blocks.append(context_block(ctx))
    blocks.append(divider_block())

    # KPI進捗
    if s.kpi:
        k = s.kpi
        weekly_pct = round(k.actual_weekly_closed / k.target_weekly_closed * 100)
        lt_status = "✅" if k.actual_lead_time_median <= k.target_lead_time_median else "📉"
        weekly_status = "✅" if k.actual_weekly_closed >= k.target_weekly_closed else "📉"
        kpi_lines = [
            "*🎯 チームKPI進捗（上半期）*\n",
            f"{weekly_status} *週完了数*: {k.actual_weekly_closed}件/週（目標 {k.target_weekly_closed}件）— {weekly_pct}%",
            f"{lt_status} *リードタイム中央値*: {k.actual_lead_time_median}日（目標 {k.target_lead_time_median}日）",
            f"📦 上半期累計: {k.half_total_closed}件（{k.half_weeks_elapsed}週経過）",
            f"📊 前期参考: {k.prev_half_total}件（{k.prev_half_weekly}件/週）",
        ]
        blocks.append(section_block("\n".join(kpi_lines)))
        blocks.append(divider_block())

    # サマリー数値
    urls = s.filter_urls or {}
    delta_prefix = "+" if s.delta_count > 0 else ""
    new_label = f"<{urls['new_tickets']}|📥 *新規起票*>" if urls.get("new_tickets") else "📥 *新規起票*"
    closed_label = f"<{urls['closed']}|✅ *完了*>" if urls.get("closed") else "✅ *完了*"
    ip_label = f"<{urls['in_progress']}|🔄 *対応中*>" if urls.get("in_progress") else "🔄 *対応中*"
    od_label = f"<{urls['overdue']}|⚠️ *期限超過*>" if urls.get("overdue") else "⚠️ *期限超過*"
    ua_label = f"<{urls['unassigned']}|👤 *未アサイン*>" if urls.get("unassigned") else "👤 *未アサイン*"
    blocks.append(
        section_fields(
            [
                f"{new_label}\n{s.new_tickets_count}件",
                f"{closed_label}\n{s.closed_count}件",
                f"📊 *増減*\n{delta_prefix}{s.delta_count}件",
                f"{ip_label}\n{s.in_progress_count}件",
                f"{od_label}\n{s.overdue_count}件",
                f"{ua_label}\n{s.unassigned_count}件",
            ]
        )
    )
    blocks.append(divider_block())

    # 新規起票チケット一覧
    if s.new_tickets:
        new_header = f"*📥 新規起票チケット一覧 — {s.new_tickets_count}件*"
        if urls.get("new_tickets"):
            new_header += f"  <{urls['new_tickets']}|（Jiraで見る）>"
        new_lines = [new_header + "\n"]
        for t in s.new_tickets[:10]:
            new_lines.append(f"• `{t.key}` {t.assignee} — {t.summary}")
        if s.new_tickets_count > 10:
            new_lines.append(f"_…他 {s.new_tickets_count - 10}件_")
        blocks.append(section_block("\n".join(new_lines)))
        blocks.append(divider_block())

    # クローズ件数トレンド（棒グラフ風）
    labels = ["3週前", "2週前", "先週", "今週"]
    max_count = max(s.trend_4w) if any(s.trend_4w) else 1
    trend_lines = []
    for label, count in zip(labels, s.trend_4w):
        bar = "█" * round(count / max_count * 8) if max_count > 0 else ""
        trend_lines.append(f"`{label}` {bar} *{count}件*")
    blocks.append(
        section_block("*📈 週次クローズ件数の推移*\n" + "\n".join(trend_lines))
    )
    blocks.append(divider_block())

    # WIP上限超過
    if s.wip_violations:
        wip_lines = [f"🚨 *WIP上限超過（上限: {conf.wip_limit}件）*"]
        for v in s.wip_violations:
            wip_lines.append(
                f"• *{v.name}*: {v.in_progress}件（+{v.in_progress - v.limit}超過）"
            )
        blocks.append(section_block("\n".join(wip_lines)))
        blocks.append(divider_block())

    # 担当者別
    assignee_lines = ["*👥 担当者別（今週）*\n"]
    for stat in s.assignee_stats:
        if stat.name == "未アサイン":
            continue
        wip_warn = " 🚨" if stat.in_progress > conf.wip_limit else ""
        assignee_lines.append(
            f"• *{stat.name}*: 完了 {stat.closed_this_week}件 / 対応中 {stat.in_progress}件{wip_warn}"
        )
    blocks.append(section_block("\n".join(assignee_lines)))
    blocks.append(divider_block())

    # リードタイム推移
    if s.lead_time_trend:
        lt_lines = ["*⏱ リードタイム推移（起票→解決・月次）*\n"]
        for lt in s.lead_time_trend:
            lt_lines.append(
                f"`{lt.month_label}` 平均 *{lt.avg_days}日* / 中央値 {lt.median_days}日 ({lt.count}件)"
            )
        blocks.append(section_block("\n".join(lt_lines)))
        blocks.append(divider_block())

    # 停滞チケット
    if s.stale:
        stale_header = f"*🚨 滞留チケット（7日以上 IN PROGRESS）— {len(s.stale)}件*"
        if urls.get("stale"):
            stale_header += f"  <{urls['stale']}|（Jiraで見る）>"
        stale_lines = [stale_header + "\n"]
        for t in s.stale[:5]:
            stale_lines.append(
                f"• `{t.key}` {t.assignee} — {t.days_stale}日前 — {t.summary}"
            )
        if len(s.stale) > 5:
            stale_lines.append(f"_…他 {len(s.stale) - 5}件_")
        blocks.append(section_block("\n".join(stale_lines)))

    # 期限超過
    if s.overdue:
        od_header = f"*⚠️ 期限超過チケット — {s.overdue_count}件*"
        if urls.get("overdue"):
            od_header += f"  <{urls['overdue']}|（Jiraで見る）>"
        od_lines = [od_header + "\n"]
        for t in s.overdue:
            od_lines.append(f"• `{t.key}` {t.assignee} {t.detail} — {t.summary}")
        if s.overdue_count > len(s.overdue):
            od_lines.append(f"_…他 {s.overdue_count - len(s.overdue)}件_")
        blocks.append(section_block("\n".join(od_lines)))

    return blocks


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Jira 停滞チケット監視スクリプト")
    parser.add_argument(
        "--check", choices=["stale", "overdue", "unassigned"], help="チェック対象を指定"
    )
    parser.add_argument(
        "--stale-days", type=int, default=3, help="停滞と判定する日数（デフォルト: 3）"
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="日報を生成（本日更新チケットを担当者別に表示）",
    )
    parser.add_argument("--weekly", action="store_true", help="週次サマリーを生成")
    parser.add_argument(
        "--notify",
        choices=["slack", "confluence"],
        help="通知先を指定（省略時は標準出力のみ）",
    )
    args = parser.parse_args()

    if not args.weekly and not args.daily and not args.check:
        parser.print_help()
        sys.exit(0)

    try:
        conf = cfg.load()
    except EnvironmentError as e:
        print(f"❌ 設定エラー: {e}", file=sys.stderr)
        print(
            "→ .env.example をコピーして .env を作成し、環境変数を設定してください",
            file=sys.stderr,
        )
        sys.exit(1)

    client = JiraClient(conf)
    added_labels = expand_weekly_labels(client, conf)
    if added_labels:
        print(
            f"🏷️  ラベル自動展開: +{len(added_labels)} 件 ({', '.join(added_labels[:5])}{'...' if len(added_labels) > 5 else ''})",
            file=sys.stderr,
        )

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
                blocks = format_weekly_blocks(summary, conf)
                slack_notifier.post_blocks(conf, blocks, text_fallback=text)
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
