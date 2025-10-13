import sqlite3
import os
import json
from datetime import datetime

DB_DIR = "chats"
DB_PATH = os.path.join(DB_DIR, "chats.db")

# اطمینان از وجود پوشه دیتابیس
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# ایجاد جدول چت‌ها اگر وجود ندارد
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                messages TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_chat(messages, title):
    """ذخیره یا بروزرسانی چت در دیتابیس"""
    data = json.dumps(messages, ensure_ascii=False)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO chats (title, messages, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                messages=excluded.messages,
                updated_at=excluded.updated_at
        """, (title, data, datetime.now().isoformat()))
        conn.commit()

def load_all_chats():
    """بارگذاری همه چت‌ها به ترتیب آخرین بروزرسانی"""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT title, messages, updated_at FROM chats
            ORDER BY updated_at DESC
        """).fetchall()

    chats = []
    for title, messages, updated_at in rows:
        try:
            chats.append({
                "title": title,
                "messages": json.loads(messages),
                "updated_at": updated_at
            })
        except json.JSONDecodeError:
            print(f"❌ خطا در بارگذاری {title}")
    return chats

# مقداردهی اولیه دیتابیس
init_db()
