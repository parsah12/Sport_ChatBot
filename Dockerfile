FROM python:3.11-slim

WORKDIR /app

# کپی فایل requirements.txt و نصب وابستگی‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی سایر فایل‌های پروژه
COPY . .

# ایجاد پوشه‌های مورد نیاز
RUN mkdir -p /app/chats /app/static/uploads

# تنظیم متغیر محیطی برای اطمینان از ایجاد پوشه chats
ENV PYTHONPATH=/app

# اجرای برنامه
CMD ["python", "app.py"]