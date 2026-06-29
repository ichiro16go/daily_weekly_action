# Vercel Authentication 手動設定チェックリスト

本番ダッシュボードのアクセス制限は Vercel の **Deployment Protection → Vercel Authentication** で個別アカウント単位の SSO 認証を有効化します。コード側の変更は不要で、`next build` / SSG / 静的 HTML 生成・CI からの `vercel deploy` には影響しません。

参考: <https://vercel.com/docs/security/deployment-protection/methods-to-protect-deployments/vercel-authentication>

関連チケット:
- EPGPRD-328（本対応・後継）
- EPGPRD-321（旧 Password Protection 案・クローズ済）

## 設定手順

1. Vercel Dashboard → 対象 Project → **Settings → Deployment Protection** を開く
2. **Vercel Authentication** セクションで **Standard Protection** を有効化
3. 適用範囲を選択:
   - 推奨: **Production + Preview** の両方を保護
   - Preview を社外共有する用途があれば、その PR/branch ごとに Shareable Link を発行
4. **Trusted IPs** は使わない（社内IPが固定化されていないため）
5. **Password Protection** は OFF（Vercel Authentication があれば不要）

## 閲覧者の追加（招待）

Vercel Team の **Member** 以上であれば、Vercel Authentication 経由でアクセス可能。

1. Vercel Team → **Settings → Members → Invite Member**
2. メールアドレス入力（@epg.co.jp を使うと SSO 経由のログインができる）
3. ロール: **Viewer** で十分（デプロイ・設定変更は不要）
4. 招待メールから承諾後、Vercel ログイン → 保護されたデプロイにアクセス可能

> Vercel Team が Pro プランの場合は Viewer ロールは無料（Member 課金対象外）。

## 動作確認

1. 別ブラウザ / シークレットウィンドウで本番 URL にアクセス
2. Vercel のログイン画面 (`https://vercel.com/sso-api?...`) にリダイレクトされることを確認
3. EPG 用 Vercel アカウントでログイン → ダッシュボードが表示される
4. Vercel Team に未招待のアカウントでログイン → アクセス拒否される

## CI / 自動化への影響

なし。Vercel Authentication は配信時の認証なので、GitHub Actions の `vercel deploy` / `vercel build` には影響しません。

過去に Password Protection 用に発行した `VERCEL_AUTOMATION_BYPASS_SECRET` は不要になりますが、`update-dashboard.yml` 内のコメント記述以外で実際の使用箇所はありません（残しても害なし、整理時に削除可）。

## 旧 Password Protection からの移行

| 観点 | 旧: Password Protection | 新: Vercel Authentication |
|---|---|---|
| 認証単位 | チーム共通パスワード | 個別アカウント (Vercel Team Member) |
| 退職者対応 | パスワード再発行＋全員に再共有 | Team から Member 削除のみ |
| 監査ログ | なし | Vercel 側にアクセスログあり |
| パスワード管理 | 1Password 等で共有運用 | 不要 |
| 設定箇所 | Vercel UI | Vercel UI |
| コスト | 無料 | Pro Team で無料（Viewer ロール） |
