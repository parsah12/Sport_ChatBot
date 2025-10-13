# --- Dockerfile ---
FROM python:3.11-slim

WORKDIR /app

# کپی فایل‌ها
COPY . /app

# نصب پکیج‌ها
# RUN pip install --no-cache-dir streamlit

# (در صورت داشتن فایل requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# ایجاد پوشه‌های لازم
RUN mkdir -p /app/db /app/chats

# اجرای برنامه
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
