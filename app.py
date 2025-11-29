import uvicorn
import json
import os
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from utils.ai_logic import generate_plan, generate_smart_title_from_history
from chat_storage import (load_all_chats, save_chat, update_chat, delete_chat, 
                         delete_all_chats, init_db)

init_db()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

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

    async def broadcast_chats_list():
        chats_list = load_all_chats()
        await websocket.send_json({
            "type": "chats",
            "data": [
                {
                    "title": c.get("smart_title") or c["title"],
                    "index": i
                }
                for i, c in enumerate(chats_list)
            ]
        })

    try:
        while True:
            data = json.loads(await websocket.receive_text())
            action = data.get("action")

            if action == "get_chats":
                await broadcast_chats_list()

            elif action == "get_chat":
                if not current_chat:
                    save_chat([], "چت جدید")
                    all_chats = load_all_chats()
                    current_chat = all_chats[0] if all_chats else None
                
                if current_chat:
                    await websocket.send_json({
                        "type": "chat",
                        "title": current_chat.get("smart_title") or current_chat["title"],
                        "messages": current_chat["messages"]
                    })

            elif action == "new_chat":
                save_chat([], "چت جدید")
                all_chats = load_all_chats()
                current_chat = all_chats[0] if all_chats else None
                await broadcast_chats_list()

            elif action == "switch_chat":
                idx = data.get("index", 0)
                chats = load_all_chats()
                if 0 <= idx < len(chats):
                    current_chat = chats[idx]
                    await websocket.send_json({
                        "type": "chat_switched",  # تغییر به chat_switched
                        "title": current_chat.get("smart_title") or current_chat["title"],
                        "messages": current_chat["messages"],
                        "smart_title": current_chat.get("smart_title")
                    })

            elif action == "delete_chat":
                idx = data.get("index", 0)
                chats = load_all_chats()
                if 0 <= idx < len(chats):
                    chat_to_delete = chats[idx]
                    delete_chat(chat_to_delete["id"])
                    # اگر چت در حال استفاده حذف شد، یک چت جدید ایجاد کن
                    if current_chat and current_chat["id"] == chat_to_delete["id"]:
                        save_chat([], "چت جدید")
                        all_chats = load_all_chats()
                        current_chat = all_chats[0] if all_chats else None
                    await broadcast_chats_list()

            elif action == "clear_all":
                delete_all_chats()
                save_chat([], "چت جدید")
                all_chats = load_all_chats()
                current_chat = all_chats[0] if all_chats else None
                await broadcast_chats_list()

            elif action == "send_message":
                text = data.get("text", "").strip()
                if not text or not current_chat:
                    continue

                current_chat["messages"].append({"role": "user", "content": text})
                
                response = generate_plan(current_chat["messages"])
                current_chat["messages"].append({"role": "bot", "content": response})

                should_generate_title = not current_chat.get("smart_title") and len(current_chat["messages"]) >= 2
                if should_generate_title:
                    smart_title = generate_smart_title_from_history(current_chat["messages"])
                    if smart_title:
                        current_chat["smart_title"] = smart_title

                # به‌روزرسانی چت موجود به جای ایجاد چت جدید
                update_chat(current_chat["id"], current_chat["messages"], current_chat.get("smart_title"))

                await websocket.send_json({
                    "type": "new_message",
                    "role": "bot",
                    "content": response
                })
                await broadcast_chats_list()

    except Exception as e:
        print("خطا در وب‌سوکت:", e)

@app.get("/view/{filename:path}")
async def view_image(filename: str):
    file_path = os.path.join("static/uploads", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}

if __name__ == "__main__":
    print("مربی هوشمند بدنسازی در حال اجرا...")
    print("آدرس: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)