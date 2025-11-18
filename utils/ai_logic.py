import requests
import os
import base64
from PIL import Image
import hashlib

OPENROUTER_API_KEY = "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"

# کش برای ذخیره تحلیل‌های عکس
image_analysis_cache = {}

def get_image_hash(filepath):
    """محاسبه هش عکس برای استفاده به عنوان کلید کش"""
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def compress_image(filepath, max_size=512, quality=30):
    """فشرده‌سازی پیشرفته عکس برای حداقل کردن حجم"""
    try:
        img = Image.open(filepath)
        
        # تبدیل به RGB اگر لازم باشد
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        
        # کاهش سایز
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # ایجاد فایل موقت
        import tempfile
        fd, output_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        
        # ذخیره با کیفیت بسیار پایین اما قابل قبول
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        
        # بررسی حجم فایل
        file_size = os.path.getsize(output_path) / 1024  # حجم به کیلوبایت
        print(f"حجم عکس فشرده: {file_size:.1f} KB")
        
        # اگر هنوز حجم زیاد است، بیشتر فشرده کن
        if file_size > 20:
            img.save(output_path, "JPEG", quality=20, optimize=True)
            file_size = os.path.getsize(output_path) / 1024
            print(f"حجم عکس پس از فشرده‌سازی اضافی: {file_size:.1f} KB")
        
        return output_path
    except Exception as e:
        print(f"[خطا در فشرده‌سازی عکس] {e}")
        return filepath

def generate_plan(chat_history):
    url = "https://openrouter.ai/api/v1/chat/completions"

    # بررسی آیا در چت عکس وجود دارد
    has_image = any(
        "file" in msg and msg["file"]["mimeType"].startswith("image/")
        for msg in chat_history
    )

    # پیدا کردن آخرین پیام کاربر
    last_user_text = ""
    last_user_has_image = False
    for msg in reversed(chat_history):
        if msg["role"] == "user":
            if msg.get("content", "").strip():
                last_user_text = msg["content"]
            if "file" in msg and msg["file"]["mimeType"].startswith("image/"):
                last_user_has_image = True
            break

    # بررسی آیا کاربر گفته عکس ندارد
    no_photo_keywords = [
        "عکس ندارم", "عکسی ندارم", "بدون عکس", "بدون تصویر", "no photo", "without photo",
        "don't have photo", "عکس نمیتونم", "فقط برنامه", "just program", "برنامه بدون عکس"
    ]
    user_said_no_photo = any(kw in last_user_text.lower() for kw in no_photo_keywords)

    # بررسی آیا قبلاً عکس تحلیل شده
    cached_analysis = None
    image_filepath = None
    
    if has_image and not user_said_no_photo:
        # پیدا کردن مسیر فایل عکس
        for msg in reversed(chat_history):
            if (msg["role"] == "user" and "file" in msg and 
                msg["file"]["mimeType"].startswith("image/")):
                image_filepath = os.path.join("static", "uploads", msg["file"]["filename"])
                if os.path.exists(image_filepath):
                    image_hash = get_image_hash(image_filepath)
                    if image_hash in image_analysis_cache:
                        cached_analysis = image_analysis_cache[image_hash]
                        print("✅ استفاده از تحلیل کش شده عکس")
                    break

    # انتخاب استراتژی بر اساس وجود عکس و کش
    if has_image and not user_said_no_photo and not cached_analysis and last_user_has_image:
        # حالت اول: عکس جدید - نیاز به تحلیل دارد
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه با ۱۵+ سال تجربه در سطح جهانی هستی. "
            "تخصص ویژه‌ات تحلیل دقیق بدن از روی عکس و ساخت برنامه ۱۰۰٪ شخصی‌سازی‌شده است."
            "وقتی کاربر عکس آپلود کرده:"
            "- تحلیل دقیق بدن"
            "  • درصد چربی تخمینی"
            "  • آنالیز پوسچر"
            "  • نقاط قوت و ضعف عضلانی"
            "- برنامه تمرینی + تغذیه + ریکاوری بده."
            "همیشه فارسی جواب بده."
        )
        model = "meta-llama/llama-3.2-90b-vision-instruct"
        temperature = 0.1
        use_vision = True
    elif has_image and not user_said_no_photo and cached_analysis:
        # حالت دوم: عکس قبلاً تحلیل شده - استفاده از کش
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه هستی. "
            "کاربر قبلاً عکس آپلود کرده و تو تحلیل زیر را انجام داده‌ای:\n\n"
            f"تحلیل قبلی از عکس کاربر:\n{cached_analysis}\n\n"
            "حالا بر اساس همین تحلیل و درخواست جدید کاربر، برنامه کامل بده."
            "نیازی به تحلیل مجدد عکس نیست. فقط بر اساس تحلیل موجود کار کن."
            "همیشه فارسی جواب بده."
        )
        model = "openai/gpt-4o-mini"
        temperature = 0.4
        use_vision = False
    else:
        # حالت سوم: بدون عکس
        system_prompt = (
            "تو یک مربی حرفه‌ای بدنسازی و تغذیه هستی. "
            "فقط بر اساس متن برنامه کامل تمرینی + تغذیه + ریکاوری بساز. "
            "فقط فارسی جواب بده."
        )
        model = "openai/gpt-4o-mini"
        temperature = 0.4
        use_vision = False

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        content_list = []

        # اضافه کردن متن
        if msg.get("content", "").strip():
            content_list.append({"type": "text", "text": msg["content"]})

        # اضافه کردن عکس فقط در شرایط خاص
        if (use_vision and role == "user" and last_user_has_image and
            "file" in msg and msg["file"]["mimeType"].startswith("image/")):

            filepath = os.path.join("static", "uploads", msg["file"]["filename"])
            if os.path.exists(filepath):
                print("🔍 شروع فشرده‌سازی و پردازش عکس...")
                compressed_path = compress_image(filepath)
                try:
                    with open(compressed_path, "rb") as f:
                        image_data = f.read()

                    img_b64 = base64.b64encode(image_data).decode("ascii")

                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    })
                    print("✅ عکس با موفقیت اضافه شد")

                    # حذف فایل موقت
                    if compressed_path != filepath:
                        try:
                            os.remove(compressed_path)
                        except Exception:
                            print("[WARN] Temp file could not be removed")

                except Exception as e:
                    content_list.append({
                        "type": "text",
                        "text": "⚠️ عکس قابل پردازش نبود. فقط براساس متن جواب می‌دم."
                    })
                    print(f"[WARN] Image processing failed: {str(e)}")
            else:
                content_list.append({"type": "text", "text": "⚠️ عکس پیدا نشد."})

        # اضافه کردن پیام به لیست
        if content_list:
            messages.append({"role": role, "content": content_list})
        elif msg.get("content", "").strip():
            messages.append({"role": role, "content": msg["content"]})

    # ارسال درخواست
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 3000,
        "top_p": 0.95,
        "presence_penalty": 0.1,
        "frequency_penalty": 0.1
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://127.0.0.1:8000",
        "X-Title": "Smart Fitness Coach",
        "Content-Type": "application/json"
    }

    try:
        print(f"🚀 ارسال درخواست به {model}...")
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        response.raise_for_status()
        
        result = response.json()["choices"][0]["message"]["content"]
        
        # اگر عکس جدید تحلیل شد، در کش ذخیره کن
        if (use_vision and image_filepath and os.path.exists(image_filepath)):
            image_hash = get_image_hash(image_filepath)
            if image_hash:
                image_analysis_cache[image_hash] = result
                print("💾 تحلیل عکس در کش ذخیره شد")
        
        return result

    except requests.exceptions.RequestException as e:
        error = str(e).lower()
        if "rate limit" in error:
            return "⚠️ سرور شلوغه، چند لحظه دیگه دوباره امتحان کن."
        return "⚠️ خطای اتصال به سرور."

    except Exception as e:
        try:
            print(f"[Unexpected error in generate_plan]: {str(e)}")
        except:
            print("[Unexpected error - log encoding failed]")
        return "⚠️ خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره امتحان کن."