import os
import base64
import hashlib
import tempfile
import logging
import requests
from PIL import Image
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------
logger = logging.getLogger(__name__)
load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY را در فایل .env تنظیم کن!")

GROQ_API_BASE = "https://api.groq.com/openai/v1"

# مدل‌ها – فقط نام‌های معتبر
TEXT_MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

image_analysis_cache = {}

# ---------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------

def get_image_hash(filepath):
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def compress_image(filepath, max_size=1024, quality=85):
    try:
        img = Image.open(filepath)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        fd, output_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

        img.save(output_path, "JPEG", quality=quality, optimize=True)

        while os.path.getsize(output_path) > 4 * 1024 * 1024:
            quality = max(10, quality - 10)
            img.save(output_path, "JPEG", quality=quality, optimize=True)

        return output_path
    except:
        return filepath


# ---------------------------------------------------------------------
# Groq Chat Function
# ---------------------------------------------------------------------

def groq_chat(messages, model=TEXT_MODEL, max_tokens=1024):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # تبدیل پیام‌ها به فرمت درست برای مدل‌های ویژن یا متنی
    formatted_messages = []
    for msg in messages:
        if isinstance(msg.get("content"), list):
            # این پیام شامل تصویر است → فقط برای مدل ویژن مجاز است
            if "vision" not in model.lower():
                return "خطا: نمی‌توان تصویر را به مدل متنی فرستاد!"
            formatted_messages.append(msg)
        else:
            # پیام معمولی متنی
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    payload = {
        "model": model,
        "messages": formatted_messages,
        "temperature": 0.7,
        "max_tokens": max_tokens
    }

    try:
        resp = requests.post(
            f"{GROQ_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        # جزئیات خطا را هم نشان بده (خیلی کمک می‌کنه!)
        error_detail = resp.text if 'resp' in locals() else str(e)
        logger.error(f"Groq API HTTP Error: {e} | Response: {error_detail}")
        return f"خطا در ارتباط با Groq [{resp.status_code}]: {error_detail}"
    except Exception as e:
        logger.exception("Groq API error: %s", e)
        return f"خطا در ارتباط با Groq: {str(e)}"
# ---------------------------------------------------------------------
# Vision Analyzer
# ---------------------------------------------------------------------

def analyze_image(image_path):
    if not os.path.exists(image_path):
        return "❌ خطا: فایل تصویر پیدا نشد."

    compressed = compress_image(image_path)

    with open(compressed, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        "تو مربی حرفه‌ای بدنسازی و تغذیه هستی با ۱۵ سال سابقه.\n"
        "از روی عکس:\n"
        "- درصد چربی تقریبی\n"
        "- تحلیل پوسچر و فرم\n"
        "- نقاط ضعف و قوت عضلانی\n"
        "- عدم تقارن احتمالی\n\n"
        "بعد یک برنامه کامل تمرینی + غذایی متناسب با همین بدن بنویس.\n"
        "اگر اطلاعات کافی نیست، فقط چند سوال کلیدی بپرس.\n"
        "همیشه فارسی، دقیق و حرفه‌ای باش.\n"
        "این عکس بدن کاربر است:"
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
            ]
        }
    ]

    return groq_chat(messages, model=VISION_MODEL)


# ---------------------------------------------------------------------
# Smart Title Generator
# ---------------------------------------------------------------------

def generate_smart_title_from_history(chat_history):
    user_msgs = []
    has_image = False

    for msg in chat_history:
        if msg.get("role") == "user":
            text = msg.get("content", "").strip()

            f = msg.get("file")
            if f and isinstance(f, dict) and f.get("mimeType", "").startswith("image/"):
                has_image = True
                user_msgs.append("عکس آپلود شده" + (f" + {text}" if text else ""))

            elif text:
                user_msgs.append(text)

    if not user_msgs:
        return "چت جدید"

    context = " | ".join(user_msgs[-8:])

    prompt = (
        f"این پیام‌های اخیر کاربر در یک چت بدنسازی هستند:\n{context}\n\n"
        "یک عنوان کوتاه، حرفه‌ای و جذاب (حداکثر ۴۰ کاراکتر) بساز.\n"
        "اگر عکس وجود دارد به تحلیل بدن اشاره کن.\n"
        "فقط عنوان را بده."
    )

    title = groq_chat([{"role": "user", "content": prompt}], model=TEXT_MODEL)
    if ":" in title:
        title = title.split(":", 1)[-1]

    return title.strip().strip('"').strip("'")[:40]


# ---------------------------------------------------------------------
# Generate Plan With or Without Vision
# ---------------------------------------------------------------------

def generate_plan(chat_history):
    has_image = False
    img_path = None

    for msg in chat_history:
        if msg.get("role") == "user":
            f = msg.get("file")
            if f and isinstance(f, dict):
                mime = f.get("mimeType", "")
                filename = f.get("filename", "")
                if mime.startswith("image/") and filename:
                    full = os.path.join("static", "uploads", filename)
                    if os.path.exists(full) and os.path.getsize(full) > 1000:
                        has_image = True
                        img_path = full
                        break

    last_user_text = next(
        (m.get("content", "") if isinstance(m.get("content"), str) else "" 
         for m in reversed(chat_history) if m.get("role") == "user"),
        ""
    )
    user_said_no_photo = any(k in last_user_text.lower() for k in ["بدون عکس", "no photo", "عکس ندارم"])

    # کش تحلیل تصویر
    cached = None
    if has_image and not user_said_no_photo and img_path:
        h = get_image_hash(img_path)
        if h in image_analysis_cache:
            cached = image_analysis_cache[h]

    # اگر عکس هست و کش نشده → تحلیل جدید با ویژن
    if has_image and not user_said_no_photo and not cached and img_path:
        analysis = analyze_image(img_path)
        h = get_image_hash(img_path)
        if h:
            image_analysis_cache[h] = analysis
        return analysis

    # حالا ادامه چت (با یا بدون کش)
    if cached:
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه هستی با ۱۵ سال سابقه.\n"
            "کاربر قبلاً عکس بدنش را فرستاده و تحلیل دقیق آن این بود:\n\n"
            f"{cached}\n\n"
            "حالا با توجه به این تحلیل و درخواست‌های جدید کاربر، پاسخ حرفه‌ای و شخصی‌سازی‌شده بده."
        )
    else:
        system_prompt = (
            "تو مربی حرفه‌ای بدنسازی و تغذیه هستی.\n"
            "اگر اطلاعات کافی از کاربر نداری (قد، وزن، سن، هدف و ...)، چند سوال کلیدی بپرس."
        )

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history:
        role = msg.get("role")
        if role not in ["user", "assistant"]:
            continue

        # اگر content یک لیست بود (یعنی شامل عکس) → فقط متن ساده بذار
        content = msg.get("content")
        if isinstance(content, list):
            # فقط متن پرامپت رو نگه دار، یا یه توضیح ساده
            text_part = next((item["text"] for item in content if item["type"] == "text"), "")
            messages.append({"role": role, "content": text_part or "کاربر عکس بدن خود را ارسال کرد."})
        elif isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()})

    return groq_chat(messages, model=TEXT_MODEL)