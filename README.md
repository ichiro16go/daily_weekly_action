# Jira 停滞チケット監視スクリプト

## 概要

`jira_monitor.py` — JPREQ プロジェクトの停滞チケットを検出し、Slack に通知するスクリプト。

## セットアップ

```bash
# 1. 環境変数ファイルを作成
cp master/scripts/.env.example master/scripts/.env

# 2. .env を編集して実際の値を設定
#   JIRA_EMAIL      : 自分の Atlassian アカウントのメールアドレス
#   JIRA_API_TOKEN  : https://id.atlassian.com/manage-profile/security/api-tokens で発行
#   SLACK_WEBHOOK_URL: Slack アプリ管理画面で取得（任意）

# 3. 環境変数を読み込む
source master/scripts/.env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL
```

## 使い方

```bash
# 停滞チケット一覧（3日以上 IN PROGRESS）を標準出力
python3 master/scripts/jira_monitor.py --check stale

# 停滞の閾値を変更（7日以上）
python3 master/scripts/jira_monitor.py --check stale --stale-days 7

# Slack に通知
python3 master/scripts/jira_monitor.py --check stale --notify slack

# 週次サマリーを標準出力
python3 master/scripts/jira_monitor.py --weekly

# 週次サマリーを Slack に通知
python3 master/scripts/jira_monitor.py --weekly --notify slack
```

## 定期実行（cron）

```cron
# 毎朝 9:00 に停滞チェック（平日のみ）
0 9 * * 1-5 cd /home/ichiro/dev && source master/scripts/.env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL && python3 master/scripts/jira_monitor.py --check stale --notify slack

# 毎週月曜 9:30 に週次サマリー
30 9 * * 1 cd /home/ichiro/dev && source master/scripts/.env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL && python3 master/scripts/jira_monitor.py --weekly --notify slack
```

## ファイル構成

```
master/scripts/
├── .env.example       # 環境変数テンプレート（コミット可）
├── .env               # 実際の値（.gitignore に追加すること）
├── config.py          # 環境変数の読み込み
├── jira_monitor.py    # メインスクリプト
├── notifiers/
│   ├── __init__.py
│   └── slack.py       # Slack Webhook 通知
└── README.md
```

## 注意事項

- `.env` は絶対にコミットしないこと（`.gitignore` に追加済みであることを確認）
- `JIRA_API_TOKEN` は個人のトークン。チームで共有しない
# daily_weekly_action
# daily_weekly_action
