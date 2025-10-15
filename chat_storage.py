import sqlite3
import os
import json
from datetime import datetime

# مسیر پوشه و فایل دیتابیس
DB_DIR = "chats"
DB_PATH = os.path.join(DB_DIR, "chats.db")

# اطمینان از وجود پوشه دیتابیس
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def init_db(clear_existing=False):
    with sqlite3.connect(DB_PATH) as conn:
        if clear_existing:
            conn.execute("DELETE FROM chats")
            conn.commit()
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


def delete_all_chats():
    """پاک کردن تمام چت‌ها از دیتابیس"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM chats")
        conn.commit()
# ================= ذخیره یا بروزرسانی چت =================
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

# ================= بارگذاری همه چت‌ها =================
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

# ================= مقداردهی اولیه دیتابیس =================
init_db()

# ================= تست: نمایش تمام چت‌ها در صورت اجرای مستقیم فایل =================
if __name__ == "__main__":
    chats = load_all_chats()

    if not chats:
        print("⚠️ هیچ چتی در دیتابیس ذخیره نشده.")
    else:
        print(f"✅ {len(chats)} چت پیدا شد:\n")
        for i, chat in enumerate(chats, start=1):
            print(f"{i}. {chat['title']}  (آخرین بروزرسانی: {chat['updated_at']})")
            print(f"   تعداد پیام‌ها: {len(chat['messages'])}")
            print("-" * 40)
