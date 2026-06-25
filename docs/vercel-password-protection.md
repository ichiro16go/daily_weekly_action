# Vercel Password Protection 手動設定チェックリスト

本番ダッシュボードのアクセス制限は Vercel 側の Deployment Protection で有効化します。コード側の機能変更は不要で、`next build` / SSG / 静的HTML生成には影響しません。

参考: <https://vercel.com/docs/security/deployment-protection>

## 手動チェックリスト

1. Vercel Dashboard → Project Settings → Deployment Protection を開く
2. Password Protection を ON にする
3. パスワードを設定する（チーム共通）
4. Production + Preview の両方に適用するか選択する（推奨: Production のみ、開発中の Preview は別途）
5. `VERCEL_AUTOMATION_BYPASS_SECRET` を Generate する
6. GitHub Repository Secrets に保存する（名前は `VERCEL_AUTOMATION_BYPASS_SECRET`）
7. 動作確認: 別ブラウザ / シークレットウィンドウで本番URLにアクセスし、PW入力画面が出ることを確認する

## パスワード共有

TODO: 共有方法をチームで決定。

候補:

- 運用保守チームの ⚙ 共有ストレージ
- 1Password
- 部内Slack DM 担当者

## 認証フローのスクリーンショット

配置予定: `docs/images/vercel-password-protection-flow.png`

現時点では画像未添付。Vercel 側で Password Protection を有効化後、PW入力画面と認証後画面を取得して追加してください。

## CI / 自動化からのアクセス

GitHub Actions のデータ更新・Vercel デプロイは、Password Protection 有効後も通常どおり動作します。保護は Vercel の配信時にかかるため、Vercel CLI の build / deploy には影響しません。

将来、GitHub Actions から保護された preview / production URL を HTTP fetch する必要が出た場合は、GitHub Repository Secrets の `VERCEL_AUTOMATION_BYPASS_SECRET` を使い、次のヘッダーを付与します。

```text
x-vercel-protection-bypass: $VERCEL_AUTOMATION_BYPASS_SECRET
```
