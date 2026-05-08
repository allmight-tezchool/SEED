"""
auth.py - SEED 認証モジュール
- ローカル開発: パスワード不要の簡易ログイン(セッション内でユーザー名選択)
- 本番(Streamlit Cloud): Google OAuth(st.login)を使う
"""

import os
import streamlit as st


def is_production():
    """Streamlit Cloud上で動いているかを判定"""
    return os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud" or os.path.exists("/mount/src")


def _get_secret_or_env(key, default=""):
    """Streamlit Secrets → 環境変数の順で値を取得"""
    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key, default)


def get_allowed_domains():
    """許可された会社ドメイン(複数対応、カンマ区切り)"""
    raw = _get_secret_or_env("ALLOWED_EMAIL_DOMAIN", "").strip().lower()
    if not raw:
        return []
    # カンマ区切りで複数対応、空白も除去
    return [d.strip().lstrip("@") for d in raw.split(",") if d.strip()]


def get_allowed_emails():
    """個別に許可された特定のメールアドレス(複数対応、カンマ区切り)"""
    raw = _get_secret_or_env("ALLOWED_EMAILS", "").strip().lower()
    if not raw:
        return []
    return [e.strip() for e in raw.split(",") if e.strip()]


def is_email_allowed(email):
    """メールアドレスが許可リストに該当するかチェック"""
    email = email.lower().strip()
    allowed_domains = get_allowed_domains()
    allowed_emails = get_allowed_emails()

    # 制限なしなら全部OK
    if not allowed_domains and not allowed_emails:
        return True

    # 特定アドレスの個別許可
    if email in allowed_emails:
        return True

    # ドメイン許可
    for domain in allowed_domains:
        if email.endswith("@" + domain):
            return True

    return False


def get_current_user():
    """
    現在ログイン中のユーザー情報を返す。
    返り値: {"id": str, "email": str, "name": str, "is_local": bool} or None
    """
    # ローカル開発モード: session_stateで管理
    if not is_production():
        local_user = st.session_state.get("local_user")
        if local_user:
            return {
                "id": local_user["email"],
                "email": local_user["email"],
                "name": local_user["name"],
                "is_local": True,
            }
        return None

    # 本番: Streamlit標準のst.login使用
    try:
        if st.user.is_logged_in:
            email = getattr(st.user, "email", "") or ""
            name = getattr(st.user, "name", "") or email.split("@")[0]
            if not is_email_allowed(email):
                return {"id": "blocked", "email": email, "name": name, "blocked": True}
            return {
                "id": email,
                "email": email,
                "name": name,
                "is_local": False,
            }
    except Exception:
        pass
    return None


def render_login_screen():
    """ログイン画面の描画。ログイン済みなら何もしない"""
    user = get_current_user()
    if user and not user.get("blocked"):
        return user

    if user and user.get("blocked"):
        st.error(
            "このメールアドレスではログインできません。\n"
            "アクセス権限がない場合は、管理者にお問い合わせください。"
        )
        if st.button("ログアウト"):
            try:
                st.logout()
            except Exception:
                pass
            st.session_state.pop("local_user", None)
            st.rerun()
        st.stop()

    # 未ログイン状態
    st.markdown("# 🌳 未来の森")
    st.markdown("つぶやきが一本の木になる、思考の森。")
    st.markdown("---")

    if is_production():
        st.markdown("### ログイン")
        st.markdown("社内のGoogleアカウントでログインしてください。")
        if st.button("🔐 Googleでログイン", type="primary"):
            try:
                st.login("google")
            except Exception as e:
                st.error(f"ログイン失敗: {e}")
        st.stop()
    else:
        st.markdown("### ローカル開発モード")
        st.caption("社内デプロイ前のテスト用ログインです。本番ではGoogle認証になります。")
        with st.form("local_login"):
            email = st.text_input("メールアドレス(ダミーでOK)", value="ryo@example.com")
            name = st.text_input("名前", value="RYO")
            submit = st.form_submit_button("ログイン", type="primary")
        if submit:
            if not email.strip():
                st.warning("メールアドレスを入力してください。")
            else:
                st.session_state.local_user = {
                    "email": email.strip().lower(),
                    "name": name.strip() or email.split("@")[0],
                }
                st.rerun()
        st.stop()


def render_logout_button():
    """サイドバー等で使うログアウトボタン"""
    user = get_current_user()
    if not user:
        return
    st.sidebar.markdown(f"**👤 {user['name']}**")
    st.sidebar.caption(user["email"])
    if st.sidebar.button("🚪 ログアウト"):
        try:
            if not user.get("is_local"):
                st.logout()
        except Exception:
            pass
        st.session_state.pop("local_user", None)
        st.session_state.clear()
        st.rerun()
