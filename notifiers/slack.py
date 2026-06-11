"""
notifiers/slack.py — Slack Incoming Webhook 通知（Block Kit 対応）

SLACK_WEBHOOK_URL 環境変数が設定されていれば投稿します。
"""

import json
import urllib.request
import sys

import config as cfg


def _post_payload(webhook_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            print(f"❌ Slack 通知失敗: HTTP {resp.status}", file=sys.stderr)
        else:
            print("✅ Slack 通知完了")


def post(conf: cfg.Config, text: str) -> None:
    """テキスト形式で投稿（後方互換）"""
    if not conf.slack_webhook_url:
        print("⚠️  SLACK_WEBHOOK_URL が未設定のため Slack 通知をスキップします", file=sys.stderr)
        return
    _post_payload(conf.slack_webhook_url, {"text": f"```\n{text}\n```"})


def post_blocks(conf: cfg.Config, blocks: list[dict], text_fallback: str = "") -> None:
    """Block Kit 形式で投稿"""
    if not conf.slack_webhook_url:
        print("⚠️  SLACK_WEBHOOK_URL が未設定のため Slack 通知をスキップします", file=sys.stderr)
        return
    payload = {"blocks": blocks}
    if text_fallback:
        payload["text"] = text_fallback
    _post_payload(conf.slack_webhook_url, payload)


# ---------------------------------------------------------------------------
# Block Kit ヘルパー
# ---------------------------------------------------------------------------

def header_block(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


def section_block(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def section_fields(fields: list[str]) -> dict:
    return {
        "type": "section",
        "fields": [{"type": "mrkdwn", "text": f} for f in fields],
    }


def divider_block() -> dict:
    return {"type": "divider"}


def context_block(texts: list[str]) -> dict:
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": t} for t in texts],
    }
