import uvicorn
import json
import os
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from utils.ai_logic import generate_plan, generate_smart_title_from_history
from chat_storage import load_all_chats, save_chat, update_chat, delete_chat, delete_all_chats, init_db

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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] New WebSocket connection")

    all_chats = load_all_chats()
    current_chat = all_chats[0] if all_chats else None

    def log(msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    async def broadcast_chats_list():
        chats_list = load_all_chats()
        await websocket.send_json({
            "type": "chats",
            "data": [
                {
                    "title": c.get("smart_title") or c["title"] or "New Chat",
                    "smart_title": c.get("smart_title")
                }
                for c in chats_list
            ]
        })

    await broadcast_chats_list()

    try:
        while True:
            data = json.loads(await websocket.receive_text())
            action = data.get("action")

            if action == "get_chats":
                log("Request: Get chat list")

            elif action == "new_chat":
                save_chat([], "New Chat")
                all_chats = load_all_chats()
                current_chat = all_chats[0]
                log("Created new chat")

            elif action == "switch_chat":
                idx = data.get("index", 0)
                chats = load_all_chats()
                if 0 <= idx < len(chats):
                    current_chat = chats[idx]
                    title = current_chat.get("smart_title") or current_chat["title"] or "New Chat"
                    log(f"Switched to chat: {title}")

            elif action == "delete_chat":
                idx = data.get("index", 0)
                chats = load_all_chats()
                if 0 <= idx < len(chats):
                    chat_to_delete = chats[idx]
                    title = chat_to_delete.get("smart_title") or chat_to_delete["title"]
                    delete_chat(chat_to_delete["id"])
                    log(f"Deleted chat: {title}")
                    if current_chat and current_chat["id"] == chat_to_delete["id"]:
                        save_chat([], "New Chat")
                        all_chats = load_all_chats()
                        current_chat = all_chats[0]
                        log("Replaced with new chat (previous was deleted)")

            elif action == "clear_all":
                delete_all_chats()
                save_chat([], "New Chat")
                all_chats = load_all_chats()
                current_chat = all_chats[0]
                log("Cleared all chats")

            elif action == "send_message":
                text = data.get("text", "").strip()
                if not text or not current_chat:
                    continue

                log(f"User message: {text}")

                current_chat["messages"].append({"role": "user", "content": text})

                log("Generating AI response...")
                response = generate_plan(current_chat["messages"])
                current_chat["messages"].append({"role": "bot", "content": response})

                if not current_chat.get("smart_title") and len(current_chat["messages"]) >= 4:
                    smart_title = generate_smart_title_from_history(current_chat["messages"])
                    if smart_title and len(smart_title.strip()) > 3:
                        current_chat["smart_title"] = smart_title.strip()
                        log(f"Smart title generated: {smart_title.strip()}")

                update_chat(current_chat["id"], current_chat["messages"], current_chat.get("smart_title"))

                await websocket.send_json({
                    "type": "message_sent",
                    "role": "user",
                    "content": text,
                    "file": None
                })

                await websocket.send_json({
                    "type": "new_message",
                    "role": "bot",
                    "content": response
                })

            elif action == "send_file":
                filename = data["filename"]
                mime_type = data["mimeType"]
                base64_data = data["data"]
                text = data.get("text", "").strip() or "Photo uploaded"

                try:
                    file_bytes = base64.b64decode(base64_data)
                    file_size_kb = len(file_bytes) / 1024
                    file_path = os.path.join(UPLOAD_DIR, filename)

                    with open(file_path, "wb") as f:
                        f.write(file_bytes)

                    log(f"File uploaded: {filename} ({file_size_kb:.1f} KB)")
                    if text != "Photo uploaded":
                        log(f"With text: {text}")

                    file_info = {
                        "filename": filename,
                        "mimeType": mime_type,
                        "tempUrl": f"/uploads/{filename}"
                    }

                    current_chat["messages"].append({
                        "role": "user",
                        "content": text,
                        "file": file_info
                    })

                    log("Analyzing image with AI...")
                    response = generate_plan(current_chat["messages"])
                    current_chat["messages"].append({"role": "bot", "content": response})

                    if not current_chat.get("smart_title"):
                        smart_title = generate_smart_title_from_history(current_chat["messages"])
                        if smart_title:
                            current_chat["smart_title"] = smart_title
                            log(f"Smart title: {smart_title}")

                    update_chat(current_chat["id"], current_chat["messages"], current_chat.get("smart_title"))

                    await websocket.send_json({
                        "type": "message_sent",
                        "role": "user",
                        "content": text,
                        "file": file_info
                    })

                    await websocket.send_json({
                        "type": "new_message",
                        "role": "bot",
                        "content": response
                    })

                except Exception as e:
                    log(f"Upload failed: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Upload failed. Please try again."
                    })

            await broadcast_chats_list()

    except WebSocketDisconnect:
        log("WebSocket disconnected")
    except Exception as e:
        log(f"Unexpected error: {e}")


@app.get("/view/{filename:path}")
async def view_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}


if __name__ == "__main__":
    print("=" * 70)
    print("     Fitness AI Coach - Final Version")
    print("     Address: http://127.0.0.1:8000")
    print("=" * 70)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)