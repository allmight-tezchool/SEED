# 🌐 SEED Web公開手順書

社内5〜10人で使えるWebアプリとして公開するためのガイドです。
**所要時間: 1〜2時間**(Google設定で初回少し迷うかも)

---

## 全体の流れ

```
[1] GitHubにコードを上げる(.envは除外)
       ↓
[2] Google Cloud Consoleで OAuth クライアントID を作成
       ↓
[3] Streamlit Community Cloud にデプロイ
       ↓
[4] Streamlit Cloud の Secrets に設定値を貼り付け
       ↓
[5] LINE WORKS でURLを社内に共有
```

---

## ステップ1: GitHubにコードを上げる

### 既存リポジトリにpushする場合

`.gitignore`に既に`.env`が入っているので、APIキーは漏れません。
普通にcommit & pushでOK。

```
git add .
git commit -m "Multi-user版"
git push
```

### 新規リポジトリの場合

GitHubで新規リポジトリ作成 → 既存フォルダで:
```
git init
git remote add origin https://github.com/あなたのユーザー名/seed.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

---

## ステップ2: Google Cloud Console で OAuth設定

### 2-1. プロジェクト作成

1. https://console.cloud.google.com/ にアクセス
2. 上部のプロジェクト選択 → 「新しいプロジェクト」
3. プロジェクト名: 「SEED」など好きな名前
4. 「作成」

### 2-2. OAuth 同意画面の設定

1. 左メニュー → 「APIとサービス」 → 「OAuth同意画面」
2. ユーザータイプ: **「内部」を選択**(Workspace組織内のみ)
   - ※「内部」が選べない場合は組織管理者でないので、その場合は「外部」+ ALLOWED_EMAIL_DOMAINで制限
3. 必要事項を入力:
   - アプリ名: `SEED 未来の森`
   - ユーザーサポートメール: あなたのメールアドレス
   - デベロッパー連絡先情報: 同上
4. スコープ: そのまま「保存して次へ」(後で自動で `openid email profile` が使われる)
5. テストユーザー: 「内部」なら不要

### 2-3. OAuth クライアントIDを作成

1. 左メニュー → 「APIとサービス」 → 「認証情報」
2. 上部「+ 認証情報を作成」 → 「OAuth クライアントID」
3. アプリケーションの種類: **「ウェブアプリケーション」**
4. 名前: `SEED Web App`
5. **承認済みのリダイレクトURI** に以下を追加:
   ```
   https://あなたのアプリ名.streamlit.app/oauth2callback
   ```
   (※後でStreamlit CloudのURLが決まったら、ここに戻って正しいURLに更新する)
6. 「作成」
7. **Client ID** と **Client Secret** が表示される → コピーしてメモ

---

## ステップ3: Streamlit Community Cloud にデプロイ

### 3-1. Streamlit Cloudにサインアップ

1. https://share.streamlit.io にアクセス
2. 「Continue with GitHub」でログイン

### 3-2. 新規アプリ作成

1. 「Create app」
2. 設定:
   - Repository: `あなたのユーザー名/seed`(さっき作ったリポジトリ)
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: `seed-yourname` のように好きな名前(これがURLになる)
3. 「Deploy!」
4. 数分待つとアプリが立ち上がる

### 3-3. リダイレクトURIの確定

ここでアプリのURLが確定する(例: `https://seed-yourname.streamlit.app/`)。

**ステップ2-3で設定した リダイレクトURI を、このURLに合わせて更新する。**

例:
```
https://seed-yourname.streamlit.app/oauth2callback
```

---

## ステップ4: Streamlit Cloud の Secrets に設定値を貼り付け

1. Streamlit Cloud のアプリ画面 → 右下「⋮」 → 「Settings」
2. 左メニュー「Secrets」
3. 以下を貼り付けて「Save」

```toml
[auth]
redirect_uri = "https://seed-yourname.streamlit.app/oauth2callback"
cookie_secret = "長いランダム文字列を64文字以上で生成して入れる"
client_id = "ステップ2-3で取得したClient ID"
client_secret = "ステップ2-3で取得したClient Secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

ANTHROPIC_API_KEY = "sk-ant-xxxx..."

ALLOWED_EMAIL_DOMAIN = "yourcompany.co.jp"
STREAMLIT_RUNTIME_ENV = "cloud"
```

### `cookie_secret` の作り方

Pythonコマンドでランダム文字列を生成:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

### `ALLOWED_EMAIL_DOMAIN` の効果

ここに会社ドメイン(例: `yourcompany.co.jp`)を入れると、**そのドメインのGoogleアカウントだけがログインできます**。

---

## ステップ5: LINE WORKSで共有

LINE WORKSのチームグループに、以下のようなメッセージを投稿:

```
🌳 SEED「未来の森」を社内βリリースしました

つぶやきを書くと、AIが豆知識や視点を返してくれて、
あなたの森に1本の木が植わります。

URL: https://seed-yourname.streamlit.app/

業務的な気づきは「業務の森」、
個人的なつぶやきは「個人の森」に蒔けます。
業務の森はみんなで見れますが、個人の森は自分専用です。

1日10本までです。気軽に遊んでみてください 🌱
```

---

## 💰 想定コスト(Haikuモデル使用時)

5〜10人が毎日3〜5本蒔く想定:

- API料金: **月 1〜3ドル程度**(Haiku使用時)
- ホスティング: **無料**(Streamlit Community Cloud)
- DB: **無料**(SQLite、ただし注意点あり↓)

---

## ⚠️ 重要な注意点(SQLite制限)

Streamlit Community Cloud の制限で、**SQLiteのデータは時々リセットされます**。

理由: コンテナが再起動すると、ファイルが揮発するため。

### 対策(運用してみて課題になったら)

**選択肢A: そのまま運用** (テスト段階ならOK)
- データが消えても気にしない、お試し運用なら十分

**選択肢B: Supabase(無料Postgres)に移行**
- データが永続化される
- 月500MB無料、5〜10人なら何年も持つ
- 移行作業: 半日くらい

最初は **A** で運用してみて、「みんなが本気で使い始めて困る」となったら **B** に移行が現実的です。

---

## 🆘 トラブル時の戻し方

何かあれば、`backup-before-multiuser` フォルダにシングルユーザー版が残してあります。

**ローカルで戻したい場合:**
1. SEED停止.bat
2. `app.py`, `db.py`, `ai.py` などを `backup-before-multiuser` から戻す
3. SEED起動.bat

---

## 困ったとき

| 症状 | 対処 |
| --- | --- |
| ログイン後も画面が出ない | Secretsの`redirect_uri`がアプリURLと一致してるか確認 |
| 「アクセスできません」エラー | OAuth同意画面の「内部/外部」設定、または ALLOWED_EMAIL_DOMAIN を確認 |
| ローカルで動かなくなった | `backup-before-multiuser` から戻す |
| データが消えた | Streamlit Cloudの仕様。本格運用ならSupabase移行 |
