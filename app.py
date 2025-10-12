import streamlit as st
import os
import shutil
from utils.ai_logic import generate_plan
from chat_storage import load_all_chats, save_chat, sanitize_filename

# ================= تنظیمات صفحه =================
st.set_page_config(page_title="💪 مربی هوشمند بدنسازی", page_icon="🏋️", layout="wide")

# ================= استایل =================
css_file = "static/style.css"
with open(css_file, "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("<div class='header'>🏋️ مربی هوشمند بدنسازی</div>", unsafe_allow_html=True)

# ================= بارگذاری چت‌ها =================
if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats()
if "current_chat" not in st.session_state:
    st.session_state.current_chat = {"title": "چت جدید", "messages": []}

# ================= سایدبار =================
st.sidebar.markdown("<h2 style='text-align:center'>💬 چت‌ها</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# دکمه ایجاد چت جدید
if st.sidebar.button("🆕 چت جدید"):
    new_chat = {"title": "چت جدید", "messages": []}
    st.session_state.current_chat = new_chat
    st.session_state.all_chats.insert(0, new_chat)

# دکمه پاک کردن چت فعلی (Clear Chat)
# if st.sidebar.button("🧹 پاک کردن چت فعلی"):
#     st.session_state.current_chat["messages"] = []

# دکمه پاک کردن همه چت‌های ذخیره شده
if st.sidebar.button("🗑️ پاک کردن همه چت‌های ذخیره شده"):
    shutil.rmtree("chats", ignore_errors=True)
    os.makedirs("chats")
    st.session_state.all_chats = []
    st.sidebar.success("تمام چت‌های ذخیره شده پاک شدند!")

# نمایش لیست چت‌ها
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
for idx, chat in enumerate(st.session_state.all_chats):
    if st.sidebar.button(chat["title"], key=f"chat_{idx}"):
        st.session_state.current_chat = chat

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

    # پاسخ AI
    with st.spinner("🤔 در حال فکر کردن..."):
        response = generate_plan(user_input)

    st.session_state.current_chat["messages"].append({"role": "bot", "content": response})

    # نمایش پیام‌ها جدید
    st.markdown(f"<div class='msg user'>👤 {user_input}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='msg bot'>🤖 {response}</div>", unsafe_allow_html=True)

# ================= ذخیره چت در فایل =================
if st.session_state.current_chat["messages"]:
    save_chat(st.session_state.current_chat["messages"], st.session_state.current_chat["title"])
