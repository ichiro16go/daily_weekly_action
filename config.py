import os
from dataclasses import dataclass, field

# デフォルトの対象プロジェクト一覧（環境変数 JIRA_PROJECTS でカンマ区切りで上書き可能）
DEFAULT_PROJECTS = ["JPREQ", "EPGQC", "JUSTPASS", "FASPACLOUD", "GRMREQ"]

# ボード1649 (EPG 運用保守タスク) のフィルターJQL
# https://epark-tech.atlassian.net/jira/software/c/projects/JUSTPASS/boards/1649
BOARD_BASE_JQL = (
    "(assignee IN ("
    "712020:09d4c52e-fe6d-4e25-a8a9-fd012d72fb6c,"
    "712020:4399f2c0-987a-4c6e-a952-1fe152cbf007,"
    "712020:0b3cada4-1b11-4612-9fb9-9d957e5afcff,"
    "712020:dbf1cbb5-d2ed-47b4-b5c7-4cafcc18f681,"
    "712020:db23ae68-6b56-4a85-895a-a10acb887b61,"
    "712020:65385b16-fcf6-4936-83a9-b5ce93e6a14e,"
    "712020:d75d4ac0-7f94-46dd-b6e4-14a152e4c590"
    ") OR (assignee IS EMPTY AND project IN (\"グルメ作業依頼\", JPREQ)))"
    " AND status NOT IN (Done, 完了, レビュー完了, Close, Rejected, Resolved,"
    " 取り下げ, レビュー済み, 切り戻し, 却下, 解決済み, リリース済み, ペンディング)"
    " AND issuetype NOT IN (Phase, \"Sub-task\", サブタスク)"
    " AND (issueLinkType NOT IN (親チケット) OR issueLinkType IS EMPTY)"
)

# statusフィルタなし版（クローズ済みチケットの集計に使用）
BOARD_MEMBER_BASE_JQL = (
    "(assignee IN ("
    "712020:09d4c52e-fe6d-4e25-a8a9-fd012d72fb6c,"
    "712020:4399f2c0-987a-4c6e-a952-1fe152cbf007,"
    "712020:0b3cada4-1b11-4612-9fb9-9d957e5afcff,"
    "712020:dbf1cbb5-d2ed-47b4-b5c7-4cafcc18f681,"
    "712020:db23ae68-6b56-4a85-895a-a10acb887b61,"
    "712020:65385b16-fcf6-4936-83a9-b5ce93e6a14e,"
    "712020:d75d4ac0-7f94-46dd-b6e4-14a152e4c590"
    ") OR (assignee IS EMPTY AND project IN (\"グルメ作業依頼\", JPREQ)))"
    " AND issuetype NOT IN (Phase, \"Sub-task\", サブタスク)"
    " AND (issueLinkType NOT IN (親チケット) OR issueLinkType IS EMPTY)"
)


@dataclass
class Config:
    base_url: str
    email: str
    api_token: str
    slack_webhook_url: str | None
    projects: list[str] = field(default_factory=lambda: list(DEFAULT_PROJECTS))

    def projects_jql(self) -> str:
        """project in (JPREQ, EPGQC, ...) 形式の JQL 断片を返す"""
        return f"project in ({', '.join(self.projects)})"

    def board_jql(self, extra: str = "", order_by: str = "") -> str:
        """ボードのアクティブチケット（status除外済み）に追加条件を付けて返す"""
        jql = f"({BOARD_BASE_JQL}) AND {extra}" if extra else BOARD_BASE_JQL
        if order_by:
            jql = f"{jql} ORDER BY {order_by}"
        return jql

    def board_member_jql(self, extra: str = "", order_by: str = "") -> str:
        """ボードメンバー限定・statusフィルタなし（クローズ済み集計用）"""
        jql = f"({BOARD_MEMBER_BASE_JQL}) AND {extra}" if extra else BOARD_MEMBER_BASE_JQL
        if order_by:
            jql = f"{jql} ORDER BY {order_by}"
        return jql


def load() -> Config:
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or None

    raw_projects = os.environ.get("JIRA_PROJECTS", "")
    projects = [p.strip() for p in raw_projects.split(",") if p.strip()] or list(DEFAULT_PROJECTS)

    missing = [k for k, v in [
        ("JIRA_BASE_URL", base_url),
        ("JIRA_EMAIL", email),
        ("JIRA_API_TOKEN", api_token),
    ] if not v]

    if missing:
        raise EnvironmentError(f"必須の環境変数が未設定です: {', '.join(missing)}")

    return Config(
        base_url=base_url,
        email=email,
        api_token=api_token,
        slack_webhook_url=slack_webhook_url,
        projects=projects,
    )

