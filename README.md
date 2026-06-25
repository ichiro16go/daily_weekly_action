# EPG 運用保守 日報・週報通知

Jira のチケットを起点に、EPG 運用保守の日報・週報 Slack 通知を自動化するツールです。

---

## 機能一覧

| 機能 | スクリプト | ワークフロー |
|------|-----------|-------------|
| Jira日報・週報 Slack通知 | `jira_monitor.py` | `jira-notify.yml` |

---

## Jira 日報・週報 Slack 通知

### 何をするか

EPG 運用保守ボード（Board 1649）のチケットを集計し、Slack に日報・週報を送信します。

- **日報**: 当日クローズ・更新されたチケットを担当者別に通知
- **週報**: 直近7日間のクローズ推移・担当者別集計を通知
- **対応中件数**: `In PROGRESS` ステータスのチケットのみを集計（完了済みを除外）

### 実装方法

```
jira_monitor.py          # Jira REST API でチケット集計・整形
config.py                # 環境変数の読み込み、JQL定義
notifiers/slack.py       # Slack Incoming Webhook で送信
.github/workflows/
  jira-notify.yml        # GitHub Actions (workflow_dispatch)
```

Jira API の `/rest/agile/1.0/board/{boardId}/issue` でチケットを取得し、
ステータス遷移履歴を `/rest/api/3/issue/{key}/changelog` で確認することで
「その日に完了系ステータスへ遷移したチケット」を正確に集計しています。

### 技術選定の理由

| 技術 | 理由 |
|------|------|
| **Python** | Jira REST API の JSON レスポンスをそのまま扱いやすく、既存スクリプトと統一 |
| **Slack Incoming Webhook** | Bot トークン不要・設定が簡単・Slack Block Kit で見やすい整形が可能 |
| **GitHub Actions (`workflow_dispatch`)** | cron-job.org から HTTP POST で定刻呼び出し。GitHub の schedule より確実に定時実行できる |
| **cron-job.org** | GitHub Actions の `schedule` トリガーは混雑時に最大数十分遅延するため外部 cron で補完 |

> **なぜ GitHub Actions の schedule を使わないのか**
>
> GitHub 公式ドキュメントにも「schedule は負荷状況によって大幅に遅延する」と記載があります。
> 定時送信（17:00 JST）を保証するために、cron-job.org から `workflow_dispatch` を叩く方式を採用しています。

### ローカルでの使い方

```bash
# セットアップ
cp .env.example .env
# .env に JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN / SLACK_WEBHOOK_URL を記入
source .env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL WEEKLY_LABELS EXCLUDED_PROJECTS

# 日報を標準出力で確認（Slack 送信なし）
python3 jira_monitor.py --daily

# 日報を Slack に送信
python3 jira_monitor.py --daily --notify slack

# 週報を Slack に送信
python3 jira_monitor.py --weekly --notify slack
```

### cron-job.org の設定（定時実行）

| ジョブ | スケジュール | `report_type` |
|--------|-------------|---------------|
| 日報   | 月〜金 17:00 JST (08:00 UTC) | `daily` |
| 週報   | 金曜 17:05 JST (08:05 UTC) | `weekly` |

**リクエスト設定:**
- URL: `https://api.github.com/repos/{owner}/{repo}/actions/workflows/jira-notify.yml/dispatches`
- Method: POST
- Headers:
  - `Authorization: Bearer {GitHub PAT}`
  - `Accept: application/vnd.github+json`
  - `X-GitHub-Api-Version: 2022-11-28`
- Body (JSON):
  ```json
  {"ref": "main", "inputs": {"report_type": "daily"}}
  ```

GitHub PAT は **Fine-grained token** で `Actions: Read and write` 権限のみ付与してください。

### 集計仕様

- 完了系ステータス: `Done` / `完了` / `Close` / `Resolved` / `解決済み` / `リリース済み`
- 週報の「今週」はカレンダー週ではなく、実行時点から遡った直近7日間
- 日報で当日更新のない担当者は末尾にまとめて表示
- ダッシュボードのリードタイム集計は、対象期間内に **created** されたチケットのみを母集団とする（期間を跨いで開いた古いチケットは件数には含めるが、平均/中央値の計算から除外）。透明性のため各エントリに `excluded_old_count` を含める
- ダッシュボードのリードタイムは P95 を超える外れ値を除外したうえで平均/中央値を算出。各エントリに `outlier_count` / `p95_threshold` / `raw_count` を含める。サンプル数 < 5 の場合は除外なし
- カレンダー画面のバーは Jira の **Start Date**（`JIRA_START_DATE_FIELD`、既定 `customfield_10015`）を開始日、**Due Date** を終了日として使用。未設定の場合は `created` / `today` にフォールバックし、両方未設定のチケットは点線枠で表示する。期限が表示月外にある期限超過チケットはバー右側に元の期限を併記。

## セットアップ（初回）

### 1. Secrets の登録

GitHub リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で登録：

| Secret 名 | 値 | 用途 |
|-----------|----|------|
| `JIRA_BASE_URL` | `https://yoursite.atlassian.net` | Jira API |
| `JIRA_EMAIL` | Atlassian アカウントのメールアドレス | Jira API |
| `JIRA_API_TOKEN` | [API トークン](https://id.atlassian.com/manage-profile/security/api-tokens) | Jira API |
| `SLACK_WEBHOOK_URL` | Slack アプリの Incoming Webhook URL | Slack通知 |

### 2. ローカル環境変数

```bash
cp .env.example .env
# .env を編集して上記の値を記入
source .env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL INCLUDE_SUBTASKS
```

### オプション環境変数

| 環境変数 | 既定値 | 用途 |
|---------|--------|------|
| `INCLUDE_SUBTASKS` | `true` | ダッシュボード集計（起案数/クローズ数/リードタイム）にサブタスクを独立カウントするか。`false` で従来挙動。 |

---

## ファイル構成

```
├── .env.example                    # 環境変数テンプレート（コミット可）
├── .env                            # 実際の値（.gitignore 済み・コミット不可）
├── config.py                       # 環境変数の読み込み・JQL定義
├── jira_monitor.py                 # 日報・週報メインスクリプト
├── notifiers/
│   ├── __init__.py
│   └── slack.py                    # Slack Webhook 通知
└── .github/
    └── workflows/
        └── jira-notify.yml         # 日報・週報 (workflow_dispatch)
```

## 注意事項

- `.env` は絶対にコミットしないこと（`.gitignore` に追加済み）
- `JIRA_API_TOKEN` は個人トークン。チームで共有しない
- GitHub PAT（cron-job.org 用）は `Actions: Read and write` のみ付与した Fine-grained token を使用すること
