import streamlit as st
import os
from utils.ai_logic import generate_plan
from chat_storage import load_all_chats, save_chat, init_db, delete_all_chats

# ================= تنظیمات صفحه =================
st.set_page_config(page_title="💪 مربی هوشمند بدنسازی", page_icon="🏋️", layout="wide")

# ================= استایل =================
css_file = "static/style.css"
if os.path.exists(css_file):
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("<div class='header'>🏋️ مربی هوشمند بدنسازی</div>", unsafe_allow_html=True)

# ================= مقداردهی اولیه دیتابیس =================
init_db()

# ================= بارگذاری چت‌ها =================
if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats()

if "current_chat" not in st.session_state:
    if st.session_state.all_chats:
        st.session_state.current_chat = st.session_state.all_chats[0]
    else:
        st.session_state.current_chat = {"title": "چت جدید", "messages": []}

# ================= سایدبار =================
st.sidebar.markdown("<h2 style='text-align:center'>💬 چت‌ها</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# دکمه ایجاد چت جدید
if st.sidebar.button("🆕 چت جدید"):
    new_chat = {"title": "چت جدید", "messages": []}
    st.session_state.current_chat = new_chat
    st.session_state.all_chats.insert(0, new_chat)
    st.rerun()

# دکمه پاک کردن همه چت‌ها
if st.sidebar.button("🗑️ پاک کردن همه چت‌ها", key="clear_chats"):
    delete_all_chats()
    st.session_state.all_chats = []
    st.session_state.current_chat = {"title": "چت جدید", "messages": []}
    st.sidebar.success("✅ همه چت‌ها پاک شدند.")
    st.rerun()

# نمایش چت‌های ذخیره‌شده با عنوان واقعی
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
for idx, chat in enumerate(st.session_state.all_chats):
    title = chat.get("title", f"چت {idx + 1}")
    if st.sidebar.button(title, key=f"chat_{idx}"):
        st.session_state.current_chat = chat
        st.rerun()

# ================= نمایش پیام‌ها =================
st.markdown("<div class='chat-box'>", unsafe_allow_html=True)
for msg in st.session_state.current_chat["messages"]:
    role_class = "user" if msg["role"] == "user" else "bot"
    emoji = "👤" if msg["role"] == "user" else "🤖"
    st.markdown(f"<div class='msg {role_class}'>{emoji} {msg['content']}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ================= ورودی کاربر =================
user_input = st.chat_input("هدفت از ورزش چیه؟ (مثلاً چربی کم کنم یا عضله‌سازی کنم...)")

if user_input:
    # ذخیره پیام کاربر
    st.session_state.current_chat["messages"].append({"role": "user", "content": user_input})

    # اگر عنوان فعلی پیش‌فرض است، با پیام اول عنوان بساز
    if st.session_state.current_chat["title"].startswith("چت جدید"):
        new_title = " ".join(user_input.split()[:3])
        st.session_state.current_chat["title"] = new_title

    # پاسخ مدل با حافظه کامل
    with st.spinner("🤔 در حال فکر کردن..."):
        response = generate_plan(st.session_state.current_chat["messages"])

    st.session_state.current_chat["messages"].append({"role": "bot", "content": response})

    # ذخیره در دیتابیس
    save_chat(st.session_state.current_chat["messages"], st.session_state.current_chat["title"])
    st.rerun()
