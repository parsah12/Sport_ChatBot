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
            conn.execute("DROP TABLE IF EXISTS chats")
            conn.commit()

        # ساخت جدول اصلی
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                smart_title TEXT,
                messages TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title)
            )
        """)

        # اضافه کردن ستون smart_title اگر وجود نداشته باشه
        try:
            conn.execute("SELECT smart_title FROM chats LIMIT 1")
        except sqlite3.OperationalError:
            print("ستون smart_title وجود نداشت — در حال اضافه کردن...")
            conn.execute("ALTER TABLE chats ADD COLUMN smart_title TEXT")
            print("ستون smart_title با موفقیت اضافه شد!")

        conn.commit()


def delete_all_chats():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM chats")
        conn.commit()


# ذخیره یا بروزرسانی چت — حالا smart_title هم قبول می‌کنه
def save_chat(messages, title, smart_title=None):
    """
    ذخیره یا بروزرسانی چت
    اگر smart_title داده بشه، ذخیره میشه
    """
    data = json.dumps(messages, ensure_ascii=False)
    now = datetime.now().isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO chats (title, smart_title, messages, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                messages = excluded.messages,
                smart_title = excluded.smart_title,
                updated_at = excluded.updated_at
        """, (title, smart_title, data, now))
        conn.commit()


# بارگذاری همه چت‌ها — حالا smart_title رو هم برمی‌گردونه
def load_all_chats():
    """بارگذاری همه چت‌ها به ترتیب آخرین بروزرسانی"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT title, smart_title, messages, updated_at FROM chats
            ORDER BY updated_at DESC
        """).fetchall()

    chats = []
    for row in rows:
        try:
            chats.append({
                "title": row["title"],
                "smart_title": row["smart_title"],  # ممکنه None باشه
                "messages": json.loads(row["messages"]),
                "updated_at": row["updated_at"]
            })
        except json.JSONDecodeError as e:
            print(f"خطا در بارگذاری چت {row['title']}: {e}")
    return chats


# ایجاد چت جدید با عنوان موقت
def create_new_chat():
    """ایجاد یک چت جدید با عنوان موقت"""
    save_chat([], "چت جدید")
    all_chats = load_all_chats()
    return all_chats[0] if all_chats else None


# مقداردهی اولیه دیتابیس
init_db()

# تست: نمایش تمام چت‌ها
if __name__ == "__main__":
    chats = load_all_chats()

    if not chats:
        print("هیچ چتی در دیتابیس ذخیره نشده.")
    else:
        print(f"{len(chats)} چت پیدا شد:\n")
        for i, chat in enumerate(chats, start=1):
            display_title = chat["smart_title"] or chat["title"]
            print(f"{i}. {display_title}")
            print(f"   پیام‌ها: {len(chat['messages'])} | بروزرسانی: {chat['updated_at']}")
            if chat["smart_title"]:
                print(f"   هوشمند: {chat['smart_title']}")
            print("-" * 50)