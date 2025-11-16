
import uvicorn
import json
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
from utils.ai_logic import generate_plan
from chat_storage import load_all_chats, save_chat, init_db, delete_all_chats


init_db()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

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

            if action == "get_chats":
                await websocket.send_json({"type": "chats", "data": [
                    {"title": c["title"], "index": i} for i, c in enumerate(load_all_chats())
                ]})

            elif action == "get_chat":
                if not current_chat: create_chat()
                await websocket.send_json({
                    "type": "chat",
                    "title": current_chat["title"],
                    "messages": current_chat["messages"]
                })

            elif action == "new_chat":
                create_chat()
                await websocket.send_json({"type": "chat_updated"})

            elif action == "switch_chat":
                idx = data.get("index", 0)
                chats = load_all_chats()
                if 0 <= idx < len(chats):
                    current_chat = chats[idx]
                await websocket.send_json({"type": "chat_updated"})

            elif action == "clear_all":
                delete_all_chats()
                create_chat()
                await websocket.send_json({"type": "chat_updated"})

            elif action == "send_message":
                text = data.get("text", "").strip()
                if not text or not current_chat: continue
                current_chat["messages"].append({"role": "user", "content": text})
                if current_chat["title"].startswith("چت جدید"):
                    words = text.split()[:3]
                    new_title = " ".join(words) or current_chat["title"]
                    if new_title != current_chat["title"]:
                        import sqlite3
                        with sqlite3.connect("chats/chats.db") as conn:
                            conn.execute("DELETE FROM chats WHERE title = ?", (current_chat["title"],))
                        current_chat["title"] = new_title
                response = generate_plan(current_chat["messages"])
                current_chat["messages"].append({"role": "bot", "content": response})
                save_chat(current_chat["messages"], current_chat["title"])
                await websocket.send_json({"type": "new_message", "role": "bot", "content": response})

    except:
        pass

if __name__ == "__main__":
    print("مربی هوشمند بدنسازی در حال اجرا...")
    print("آدرس: http://127.0.0.1:8000")
    print("برای بستن: Ctrl+C")
    uvicorn.run(app, host="127.0.0.1", port=8000)    