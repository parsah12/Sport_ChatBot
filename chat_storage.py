import json
import os

CHAT_DIR = "chats"
if not os.path.exists(CHAT_DIR):
    os.makedirs(CHAT_DIR)

def sanitize_filename(title):
    """تبدیل عنوان به نام فایل امن"""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in title)

def save_chat(messages, title):
    """ذخیره یا بروزرسانی چت"""
    file_name = sanitize_filename(title) + ".json"
    file_path = os.path.join(CHAT_DIR, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"title": title, "messages": messages}, f, ensure_ascii=False, indent=2)

def load_all_chats():
    """بارگذاری همه چت‌ها"""
    chats = []
    for file in os.listdir(CHAT_DIR):
        if file.endswith(".json"):
            try:
                with open(os.path.join(CHAT_DIR, file), "r", encoding="utf-8") as f:
                    chats.append(json.load(f))
            except Exception as e:
                print(f"خطا در بارگذاری {file}: {e}")
    # مرتب‌سازی بر اساس زمان modification واقعی فایل‌ها
    chats.sort(key=lambda x: os.path.getmtime(os.path.join(CHAT_DIR, sanitize_filename(x["title"]) + ".json")), reverse=True)
    return chats
