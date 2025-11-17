import uvicorn
import json
import os
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from utils.ai_logic import generate_plan
from chat_storage import load_all_chats, save_chat, init_db, delete_all_chats

# --- تنظیمات اولیه ---
init_db()
app = FastAPI()

# پوشه‌های استاتیک
app.mount("/static", StaticFiles(directory="static"), name="static")

# پوشه آپلودها
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/template.html", encoding="utf-8") as f:
        return f.read()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    all_chats = load_all_chats()
    current_chat = all_chats[0] if all_chats else None

    def create_chat():
        nonlocal current_chat, all_chats
        title = f"چت جدید {datetime.now().strftime('%H:%M')}"
        save_chat([], title)
        all_chats = load_all_chats()
        current_chat = all_chats[0]

    try:
        while True:
            data = json.loads(await websocket.receive_text())
            action = data.get("action")

            # --- دریافت لیست چت‌ها ---
            if action == "get_chats":
                await websocket.send_json({
                    "type": "chats",
                    "data": [
                        {"title": c["title"], "index": i}
                        for i, c in enumerate(load_all_chats())
                    ]
                })

            # --- دریافت چت فعلی ---
            elif action == "get_chat":
                if not current_chat:
                    create_chat()
                await websocket.send_json({
                    "type": "chat",
                    "title": current_chat["title"],
                    "messages": current_chat["messages"]
                })

            # --- چت جدید ---
            elif action == "new_chat":
                create_chat()
                await websocket.send_json({"type": "chat_updated"})

            # --- تغییر چت ---
            elif action == "switch_chat":
                idx = data.get("index", 0)
                chats = load_all_chats()
                if 0 <= idx < len(chats):
                    current_chat = chats[idx]
                await websocket.send_json({"type": "chat_updated"})

            # --- پاک کردن همه ---
            elif action == "clear_all":
                delete_all_chats()
                create_chat()
                await websocket.send_json({"type": "chat_updated"})

            # --- ارسال پیام متنی ---
            elif action == "send_message":
                text = data.get("text", "").strip()
                if not text or not current_chat:
                    continue

                current_chat["messages"].append({"role": "user", "content": text})

                # تغییر عنوان چت جدید
                if current_chat["title"].startswith("چت جدید"):
                    words = text.split()[:4]
                    new_title = " ".join(words)
                    if len(new_title) > 3:
                        import sqlite3
                        with sqlite3.connect("chats/chats.db") as conn:
                            conn.execute("DELETE FROM chats WHERE title = ?", (current_chat["title"],))
                        current_chat["title"] = new_title

                response = generate_plan(current_chat["messages"])
                current_chat["messages"].append({"role": "bot", "content": response})
                save_chat(current_chat["messages"], current_chat["title"])

                await websocket.send_json({
                    "type": "new_message",
                    "role": "bot",
                    "content": response
                })

            # --- آپلود فایل (عکس یا فیلم) - نسخه نهایی و تمیز ---
            elif action == "send_file":
                filename = data.get("filename", "unknown_file")
                mime_type = data.get("mimeType", "application/octet-stream")
                file_data_b64 = data.get("data")
                text = data.get("text", "").strip()

                if not file_data_b64 or not current_chat:
                    continue

                # تعیین پسوند امن
                ext = "jpg"
                if "." in filename:
                    ext = filename.split(".")[-1].lower()
                elif "image" in mime_type:
                    ext = mime_type.split("/")[-1]
                elif "video" in mime_type:
                    ext = mime_type.split("/")[-1]

                safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{hash(filename) % 100000}.{ext}"
                filepath = os.path.join(UPLOAD_DIR, safe_filename)

                # ذخیره فایل
                try:
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(file_data_b64))
                except Exception as e:
                    print("خطا در ذخیره فایل:", e)
                    continue

                # فقط متن در چت نمایش داده بشه (عکس در چت نمیاد)
                user_content = text or "عکس آپلود شد و در حال تحلیل..."

                # ذخیره پیام کاربر با فایل (برای AI)
                current_chat["messages"].append({
                    "role": "user",
                    "content": user_content,
                    "file": {
                        "filename": safe_filename,
                        "original_name": filename,
                        "mimeType": mime_type
                    }
                })

                # فقط متن رو به فرانت‌اند بفرست (بدون file)
                await websocket.send_json({
                    "type": "new_message",
                    "role": "user",
                    "content": user_content
                })

                # AI تحلیل کنه (عکس رو می‌بینه!)
                response = generate_plan(current_chat["messages"])
                current_chat["messages"].append({"role": "bot", "content": response})
                save_chat(current_chat["messages"], current_chat["title"])

                await websocket.send_json({
                    "type": "new_message",
                    "role": "bot",
                    "content": response
                })

    except Exception as e:
        print("خطا در وب‌سوکت:", e)


# فقط برای دیباگ یا ngrok (اختیاری)
@app.get("/view/{filename:path}")
async def view_image(filename: str):
    file_path = os.path.join("static/uploads", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    print("مربی هوشمند بدنسازی در حال اجرا...")
    print("آدرس: http://127.0.0.1:8000")
    print("برای بستن: Ctrl+C")
    uvicorn.run(app, host="127.0.0.1", port=8000)