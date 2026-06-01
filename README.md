# Jira 日報・週報 Slack通知

## 概要

`jira_monitor.py` — ボード1649（EPG 運用保守）のチケットを集計し、Slack に日報・週報を送信するスクリプト。

- **日報** (`--daily`): 月〜金 17:00 に当日クローズ・当日更新チケットを担当者別で通知
- **週報** (`--weekly`): 金曜 17:00 に直近7日間のクローズ推移・担当者別集計を通知

### 集計仕様

- 日報・週報の完了件数は、現在も完了系ステータスで、対象期間内に完了系ステータスへ遷移したチケットを集計します。
- 完了系ステータスは `Done`, `完了`, `Close`, `Resolved`, `解決済み`, `リリース済み` です。
- 週報の「今週」はカレンダー週ではなく、レポート実行時点から遡った直近7日間です。
- 日報では更新がない担当者を個別セクションにせず、末尾にデバッグ用として集約表示します。

## セットアップ（ローカル実行）

```bash
# 1. 環境変数ファイルを作成
cp .env.example .env

# 2. .env を編集して実際の値を設定
#   JIRA_BASE_URL   : https://yoursite.atlassian.net
#   JIRA_EMAIL      : 自分の Atlassian アカウントのメールアドレス
#   JIRA_API_TOKEN  : https://id.atlassian.com/manage-profile/security/api-tokens で発行
#   SLACK_WEBHOOK_URL: Slack アプリ管理画面で取得

# 3. 環境変数を読み込む
source .env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL
```

## 使い方

```bash
# 日報を標準出力
python3 jira_monitor.py --daily

# 日報を Slack に送信
python3 jira_monitor.py --daily --notify slack

# 週報を標準出力
python3 jira_monitor.py --weekly

# 週報を Slack に送信
python3 jira_monitor.py --weekly --notify slack
```

## GitHub Actions による定期自動実行

**スケジュール:**
- 日報: 月〜金 17:00 JST に自動送信
- 週報: 金曜 17:05 JST に自動送信（日報の直後）

### Secrets の登録手順

1. GitHub リポジトリの **Settings** → **Secrets and variables** → **Actions** を開く
2. **New repository secret** から以下の4つを登録する:

| Secret名 | 値 |
|---------|---|
| `JIRA_BASE_URL` | `https://yoursite.atlassian.net` |
| `JIRA_EMAIL` | Atlassian アカウントのメールアドレス |
| `JIRA_API_TOKEN` | [API トークン](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `SLACK_WEBHOOK_URL` | Slack アプリの Incoming Webhook URL |

3. Actions タブ → **Jira 日報・週報 Slack通知** → **Run workflow** で手動テスト可能

### 手動実行

Actions タブから `workflow_dispatch` で `daily` / `weekly` / `both` を選んで手動実行できます。

## ファイル構成

```
├── .env.example          # 環境変数テンプレート（コミット可）
├── .env                  # 実際の値（.gitignore 済み・コミット不可）
├── config.py             # 環境変数の読み込み・JQL定義
├── jira_monitor.py       # メインスクリプト
├── notifiers/
│   ├── __init__.py
│   └── slack.py          # Slack Webhook 通知
└── .github/
    └── workflows/
        └── jira-notify.yml  # GitHub Actions 定期実行設定
```

## 注意事項

- `.env` は絶対にコミットしないこと（`.gitignore` に追加済み）
- `JIRA_API_TOKEN` は個人のトークン。チームで共有しない
