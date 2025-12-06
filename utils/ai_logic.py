import os
import base64
import hashlib
import tempfile
import logging
from PIL import Image

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure API key from env (set GEMINI_API_KEY) or hardcode (not recommended)
GEMINI_API_KEY = "AIzaSyAkUBAqCbc9r1rUib-Ch0r3BeaOJQrguHs"
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set in environment. Set GEMINI_API_KEY env var.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# simple in-memory cache (your original)
image_analysis_cache = {}

def get_image_hash(filepath):
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.exception("get_image_hash error: %s", e)
        return None

def compress_image(filepath, max_size=1024, quality=85):
    try:
        img = Image.open(filepath)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        fd, output_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        file_size = os.path.getsize(output_path)
        # ensure < 4MB
        while file_size > 4 * 1024 * 1024:
            quality = max(10, quality - 10)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
            file_size = os.path.getsize(output_path)
        # check 33MP
        width, height = img.size
        if width * height > 33 * 1024 * 1024:
            ratio = (33 * 1024 * 1024 / (width * height)) ** 0.5
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
        return output_path
    except Exception as e:
        logger.exception("compress_image error: %s", e)
        return filepath

# ------------------------------
# generate_smart_title_from_history (unchanged prompts)
# ------------------------------
def generate_smart_title_from_history(chat_history) -> str:
    user_messages = []
    has_image = False

    for msg in chat_history:
        if msg.get("role") == "user":
            text = msg.get("content", "").strip()
            file_info = msg.get("file")
            if file_info and isinstance(file_info, dict) and file_info.get("mimeType", "").startswith("image/"):
                has_image = True
                user_messages.append("عکس آپلود کرد" + (f" + {text}" if text else ""))
            elif text:
                user_messages.append(text)

    if not user_messages:
        return "چت جدید"

    context = " | ".join(user_messages[-8:])

    prompt = f"""
این پیام‌های کاربر در یک چت بدنسازی و تغذیه هست:
{context}
یک عنوان کوتاه، جذاب و حرفه‌ای (حداکثر ۴۰ کاراکتر فارسی) برای این مکالمه بساز.
اگر عکس آپلود شده حتماً به تحلیل بدن یا فرم اشاره کن.
فقط خود عنوان را بنویس، بدون نقل قول و توضیح.
عنوان:"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("[AI-TITLE] Sending prompt to Gemini for title generation")
        result = model.generate_content(prompt)
        title = getattr(result, "text", "").strip()
        if ":" in title:
            title = title.split(":", 1)[-1]
        title = title.strip().strip('\'"“”`')
        logger.info("[AI-TITLE] Generated title: %s", title)
        return title[:40]
    except Exception as e:
        logger.exception("خطا در generate_smart_title_from_history: %s", e)
        return "تحلیل عکس بدن" if has_image else "برنامه تمرینی و تغذیه"

# ------------------------------
# analyze_image: new function
# ------------------------------
def analyze_image(image_path):
    """
    دریافت مسیر فایل تصویر → فشرده سازی → ارسال به Gemini (base64) → بازگشت متن پاسخ
    """
    try:
        if not os.path.exists(image_path):
            logger.error("[IMAGE] file not found: %s", image_path)
            return "خطا: فایل تصویر پیدا نشد."

        logger.info("[IMAGE] compressing image: %s", image_path)
        compressed = compress_image(image_path)
        logger.info("[IMAGE] compressed path: %s", compressed)

        with open(compressed, "rb") as f:
            img_bytes = f.read()

        base64_image = base64.b64encode(img_bytes).decode("utf-8")
        logger.info("[IMAGE] base64 size: %d bytes", len(base64_image))

        # prompt (exactly as in your generate_plan use_vision prompt)
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه با ۱۵+ سال تجربه در سطح جهانی هستی. "
            "تخصص ویژه‌ات تحلیل دقیق بدن از روی عکس و ساخت برنامه ۱۰۰٪ شخصی‌سازی‌شده است."
            "وقتی کاربر عکس آپلود کرده:"
            "- تحلیل دقیق بدن انجام بده (درصد چربی تقریبی، پوسچر، تقارن، نقاط قوت و ضعف عضلانی)"
            "- بر اساس عکس و درخواست کاربر، برنامه کامل تمرینی و غذایی شخصی‌سازی‌شده بنویس"
            "- اگر اطلاعات کافی نیست، فقط ۵–۶ سوال کوتاه و ضروری بپرس"
            "همیشه فارسی، حرفه‌ای، صمیمی و بدون تکرار صحبت کن."
        )

        logger.info("[AI] Sending image to Gemini for analysis...")
        model = genai.GenerativeModel("gemini-2.0-flash")

        # ساخت payload برای ارسال تصویر (parts با inline_data)
        # ساختار: یک ورودی حاوی system prompt و یک inline_data برای تصویر
        payload = [
            {
                "parts": [
                    {"text": system_prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]

        result = model.generate_content(payload)
        text = getattr(result, "text", "")
        logger.info("[AI] Gemini returned %d chars", len(text))
        return text

    except Exception as e:
        logger.exception("analyze_image error: %s", e)
        return f"خطا در تحلیل تصویر: {str(e)}"

# ------------------------------
# generate_plan (keeps your prompts unchanged)
# ------------------------------
def generate_plan(chat_history):
    """
    این تابع از همان پرامپت‌ها و منطق قبلی استفاده می‌کند.
    اگر تصویری وجود داشته باشد و در کش نباشد، analyze_image فراخوانی می‌شود.
    """
    # تشخیص عکس واقعی
    has_real_image = False
    last_image_path = None

    for msg in chat_history:
        if msg.get("role") == "user":
            file_info = msg.get("file")
            if isinstance(file_info, dict):
                mime = file_info.get("mimeType", "")
                filename = file_info.get("filename", "")
                if mime.startswith("image/") and filename:
                    fp = os.path.join("static", "uploads", filename)
                    if os.path.exists(fp) and os.path.getsize(fp) > 1000:
                        has_real_image = True
                        last_image_path = fp
                        break

    last_user_text = next((m.get("content", "") for m in reversed(chat_history) if m.get("role") == "user"), "")
    user_said_no_photo = any(kw in last_user_text.lower() for kw in ["عکس ندارم", "بدون عکس", "no photo", "فقط برنامه"])

    # کش تحلیل قبلی
    cached_analysis = None
    if has_real_image and not user_said_no_photo and last_image_path:
        h = get_image_hash(last_image_path)
        if h and h in image_analysis_cache:
            cached_analysis = image_analysis_cache[h]

    use_vision = has_real_image and not user_said_no_photo and not cached_analysis

    # اگر باید تحلیل عکس انجام شود، از analyze_image استفاده کن
    if use_vision and last_image_path:
        logger.info("[PLAN] Using vision path, analyzing image: %s", last_image_path)
        analysis_text = analyze_image(last_image_path)
        # ذخیره در کش
        h = get_image_hash(last_image_path)
        if h:
            image_analysis_cache[h] = analysis_text
        return analysis_text

    # در غیر این صورت، از متن چت استفاده کن (keep prompts unchanged)
    # ساخت system_prompt همانطور که در کد اولیه داشتید
    if cached_analysis:
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه با ۱۵+ سال تجربه هستی."
            "کاربر قبلاً عکس آپلود کرده و تحلیل بدنش این بود:"
            f"{cached_analysis}"
            "حالا بر اساس همین تحلیل و درخواست جدید کاربر، برنامه کامل تمرینی و غذایی شخصی‌سازی‌شده بنویس."
            "نیازی به تحلیل مجدد عکس نیست."
            "همیشه فارسی، حرفه‌ای، کوتاه و بدون تکرار جواب بده."
        )
    else:
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه با ۱۵+ سال تجربه هستی."
            "اگر اطلاعات کافی برای ساخت برنامه نداری، فقط این ۶–۷ سوال کلیدی را بپرس (نه بیشتر):"
            "- قد و وزن فعلی؟"
            "- سن و جنسیت؟"
            "- هدف اصلی (کاهش وزن، عضله‌سازی، فرم‌دهی)؟"
            "- سطح فعلی فعالیت بدنی؟"
            "- محدودیت‌های غذایی یا ترجیحات خاص؟"
            "- تا کی می‌خوای به هدفت برسی؟"
            "کوتاه، حرفه‌ای و صمیمی صحبت کن. از لیست‌های طولانی و تکرار جداً خودداری کن."
        )

    # جمع‌آوری پیام‌ها
    messages_text = ""
    for msg in chat_history:
        role = msg.get("role", "").strip()
        content = msg.get("content", "").strip()
        if content:
            messages_text += f"{role}: {content}\n"

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = system_prompt + "\n" + messages_text
        logger.info("[PLAN] Sending text prompt to Gemini (len=%d)", len(prompt))
        result = model.generate_content(prompt)
        text = getattr(result, "text", "")
        logger.info("[PLAN] Received %d chars from Gemini", len(text))
        return text
    except Exception as e:
        logger.exception("generate_plan error: %s", e)
        return f"خطا در ارتباط با Gemini: {str(e)}"
