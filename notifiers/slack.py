"""
notifiers/slack.py — Slack Incoming Webhook 通知

SLACK_WEBHOOK_URL 環境変数が設定されていれば投稿します。
"""

import json
import urllib.request
import sys

import config as cfg


def post(conf: cfg.Config, text: str) -> None:
    if not conf.slack_webhook_url:
        print("⚠️  SLACK_WEBHOOK_URL が未設定のため Slack 通知をスキップします", file=sys.stderr)
        return

    payload = json.dumps({"text": f"```\n{text}\n```"}).encode()
    req = urllib.request.Request(
        conf.slack_webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            print(f"❌ Slack 通知失敗: HTTP {resp.status}", file=sys.stderr)
        else:
            print("✅ Slack 通知完了")
