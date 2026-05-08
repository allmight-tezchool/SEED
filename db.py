"""
db.py - SEED 未来の森のDB
複数ユーザー対応 + 業務/個人カテゴリ
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "seed.db"

# 既存データ(user_idなし)を、シングルユーザー時代の所有者として扱う
LEGACY_USER_ID = "legacy"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """テーブル作成 + 後方互換マイグレーション"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seeds (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet       TEXT    NOT NULL,
                ai_response TEXT    NOT NULL,
                tags        TEXT,
                created_at  TEXT    NOT NULL
            )
        """)
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(seeds)").fetchall()}
        new_cols = {
            "tree_type":      "TEXT DEFAULT 'pine'",
            "size":           "INTEGER DEFAULT 1",
            "x_position":     "REAL DEFAULT 0.5",
            "keeper_message": "TEXT DEFAULT ''",
            "linked_seed_id": "INTEGER",
            "user_id":        "TEXT DEFAULT 'legacy'",       # 誰のたねか
            "user_name":      "TEXT DEFAULT ''",             # 表示名
            "category":       "TEXT DEFAULT 'personal'",     # business / personal
        }
        for col, ddl in new_cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE seeds ADD COLUMN {col} {ddl}")


def add_seed(tweet, ai_response, tags="", tree_type="pine", size=1,
             x_position=0.5, keeper_message="", linked_seed_id=None,
             user_id=LEGACY_USER_ID, user_name="", category="personal"):
    created_at = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO seeds
                (tweet, ai_response, tags, created_at,
                 tree_type, size, x_position, keeper_message, linked_seed_id,
                 user_id, user_name, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tweet, ai_response, tags, created_at,
              tree_type, size, x_position, keeper_message, linked_seed_id,
              user_id, user_name, category))
        return cur.lastrowid


def list_seeds(limit=200, keyword=None, user_id=None, category=None,
               include_business_shared=False):
    """
    ユーザー絞り込みつきリスト取得。
    user_id=None: 全件(管理用)
    user_id指定 + category="personal": その人の個人たねのみ
    user_id指定 + category="business": その人の業務たねのみ
    user_id指定 + include_business_shared=True: 自分のたね全部 + みんなの業務たね
    """
    with get_conn() as conn:
        clauses = []
        params = []

        if include_business_shared and user_id:
            # 自分のたね全部、または誰でも見れる業務カテゴリ
            clauses.append("(user_id = ? OR category = 'business')")
            params.append(user_id)
        elif user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
            if category:
                clauses.append("category = ?")
                params.append(category)
        elif category:
            clauses.append("category = ?")
            params.append(category)

        if keyword:
            like = f"%{keyword}%"
            clauses.append("(tweet LIKE ? OR ai_response LIKE ? OR tags LIKE ?)")
            params.extend([like, like, like])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM seeds {where} ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return conn.execute(sql, params).fetchall()


def get_seed(seed_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM seeds WHERE id = ?", (seed_id,)).fetchone()


def list_recent_summaries(limit=30, user_id=None):
    """関連性チェック用に、自分の過去のたねを返す"""
    with get_conn() as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT id, tweet, tags FROM seeds WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, tweet, tags FROM seeds ORDER BY id DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def delete_seed(seed_id, user_id=None):
    """自分のたねしか削除できないようにする(user_id 指定時)"""
    with get_conn() as conn:
        if user_id is not None:
            conn.execute("DELETE FROM seeds WHERE id = ? AND user_id = ?", (seed_id, user_id))
        else:
            conn.execute("DELETE FROM seeds WHERE id = ?", (seed_id,))


def count_seeds(user_id=None, category=None):
    with get_conn() as conn:
        clauses = []
        params = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if category:
            clauses.append("category = ?")
            params.append(category)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = conn.execute(f"SELECT COUNT(*) AS c FROM seeds {where}", params).fetchone()
        return row["c"] if row else 0


def count_seeds_today(user_id, category=None):
    """今日の蒔き回数(レートリミット用)"""
    today = datetime.now().date().isoformat()
    with get_conn() as conn:
        clauses = ["user_id = ?", "DATE(created_at) = ?"]
        params = [user_id, today]
        if category:
            clauses.append("category = ?")
            params.append(category)
        where = " AND ".join(clauses)
        row = conn.execute(f"SELECT COUNT(*) AS c FROM seeds WHERE {where}", params).fetchone()
        return row["c"] if row else 0
