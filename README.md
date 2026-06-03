# EPG 運用保守 自動化ツール集

Jira のチケットを起点に、Slack 通知・情報不足チェック・定時実行を自動化するツール群です。

---

## 機能一覧

| 機能 | スクリプト | ワークフロー |
|------|-----------|-------------|
| Jira日報・週報 Slack通知 | `jira_monitor.py` | `jira-notify.yml` |
| 営業依頼チケット 情報不足自動チェック | `sales_request_checker.py` | `sales-request-checker.yml` |

---

## 機能 1: Jira 日報・週報 Slack 通知

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
source .env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL

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

---

## 機能 2: 営業依頼チケット 情報不足自動チェック

### 何をするか

JPREQ プロジェクトに営業・事業部からの依頼チケットが起票されたとき、
**記載すべき情報が揃っているかを自動チェックし、不足項目をコメントで通知**します。

チェック結果は 🔴（情報不足）/ 🟡（一部不足）/ 🟢（十分）の3段階で評価します。

### チェック項目

| カテゴリ | 必須項目 | 評価方法 |
|---------|---------|---------|
| ① 基本情報 | 対象サービス・依頼内容・希望時期 | キーワードマッチ |
| ② 前提条件 | **現状 (As-Is)・発生条件・対象範囲・背景** | キーワードマッチ（1項目でも欠けると 🔴） |
| ③ 要件 | 変更後の姿 (To-Be)・期待効果 | キーワードマッチ |
| ④ 任意確認項目 | 優先度・代替案・添付資料 | 参考表示のみ |

**最終判定ロジック:**
- ② の必須4項目が1つでも欠けている → 🔴
- ①③ の必須項目の過半数（2項目以上）が不足 → 🔴
- それ以外で不足あり → 🟡
- すべて揃っている → 🟢

### 実装方法

```
sales_request_checker.py          # Jira から description を取得 → キーワード判定 → コメント投稿
.github/workflows/
  sales-request-checker.yml       # repository_dispatch + workflow_dispatch
```

1. Jira REST API でチケットの `description` フィールドを取得
2. Jira の description は **ADF（Atlassian Document Format）** という JSON 形式で返ることがあるため、再帰的にテキストを抽出
3. 各カテゴリのキーワードリストと照合して項目の有無を判定
4. `--post` フラグが指定された場合のみ Jira にコメントを投稿

**重複投稿防止:** コメントに `[sales-request-checker v1]` というマーカーを埋め込み、
直近のコメントに同マーカーがあれば再投稿をスキップします。

### 技術選定の理由

| 技術 | 理由 |
|------|------|
| **キーワードベース判定（LLM不使用）** | LLM API コストが不要・結果が決定的で説明しやすい・営業依頼のパターンが限定的なため十分 |
| **Python** | `jira_monitor.py` の `JiraClient` クラスをそのまま再利用できるため追加依存なし |
| **`repository_dispatch` + `workflow_dispatch` 併用** | Jira Automation からは `repository_dispatch` で呼び出し、手動テストは GitHub UI の `workflow_dispatch` で実行できるようにした |
| **dry-run デフォルト** | `--post` なしで CLI 出力のみにすることで、ローカルでの動作確認を安全に行える |

### ローカルでの使い方

```bash
# dry-run（CLI に結果を出力するだけ、Jira には投稿しない）
python3 sales_request_checker.py JPREQ-1234

# Jira にコメントを投稿
python3 sales_request_checker.py JPREQ-1234 --post
```

### GitHub Actions からの自動実行（手動テスト）

1. **Actions** タブ → 「**営業依頼チケット 情報不足自動チェック**」
2. **Run workflow** → `ticket_key` に対象チケットキー（例: `JPREQ-1234`）を入力
3. 実行ログに `✅ JPREQ-XXXX にコメントを投稿しました。` が出れば成功

### Jira Automation との連携（本番運用）

JPREQ プロジェクトの Automation で「チケット作成時に GitHub Actions を自動実行」する設定が必要です。

1. JPREQ プロジェクト設定 → **Automation** → **Create rule**
2. **Trigger**: Issue created（`issuetype != Sub-task`）
3. **Action**: Send web request
   - URL: `https://api.github.com/repos/{owner}/{repo}/actions/workflows/sales-request-checker.yml/dispatches`
   - Method: POST
   - Headers:
     - `Authorization: Bearer {GitHub PAT}`
     - `Accept: application/vnd.github+json`
     - `X-GitHub-Api-Version: 2022-11-28`
   - Body (JSON):
     ```json
     {"ref": "main", "inputs": {"ticket_key": "{{issue.key}}"}}
     ```

---

## セットアップ（初回）

### 1. Secrets の登録

GitHub リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で登録：

| Secret 名 | 値 | 用途 |
|-----------|----|------|
| `JIRA_BASE_URL` | `https://yoursite.atlassian.net` | 両機能 |
| `JIRA_EMAIL` | Atlassian アカウントのメールアドレス | 両機能 |
| `JIRA_API_TOKEN` | [API トークン](https://id.atlassian.com/manage-profile/security/api-tokens) | 両機能 |
| `SLACK_WEBHOOK_URL` | Slack アプリの Incoming Webhook URL | 機能1のみ |

### 2. ローカル環境変数

```bash
cp .env.example .env
# .env を編集して上記の値を記入
source .env && export JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN SLACK_WEBHOOK_URL
```

---

## ファイル構成

```
├── .env.example                    # 環境変数テンプレート（コミット可）
├── .env                            # 実際の値（.gitignore 済み・コミット不可）
├── config.py                       # 環境変数の読み込み・JQL定義
├── jira_monitor.py                 # 日報・週報メインスクリプト
├── sales_request_checker.py        # 営業依頼チケット情報不足チェック
├── notifiers/
│   ├── __init__.py
│   └── slack.py                    # Slack Webhook 通知
└── .github/
    └── workflows/
        ├── jira-notify.yml         # 日報・週報 (workflow_dispatch)
        └── sales-request-checker.yml  # 情報不足チェック (repository_dispatch + workflow_dispatch)
```

## 注意事項

- `.env` は絶対にコミットしないこと（`.gitignore` に追加済み）
- `JIRA_API_TOKEN` は個人トークン。チームで共有しない
- GitHub PAT（cron-job.org / Jira Automation 用）は `Actions: Read and write` のみ付与した Fine-grained token を使用すること
