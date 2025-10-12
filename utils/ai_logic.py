# utils/ai_logic.py
import requests

OPENROUTER_API_KEY = "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"

def generate_plan(user_input):
    """
    تولید پاسخ ورزشی و دوستانه برای کاربر با استفاده از OpenRouter و مدل gpt-4o-mini.
    پاسخ‌ها تکرارپذیر و محدود به موضوع ورزشی هستند و لحن صمیمی دارند.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    system_prompt = {
        "role": "system",
        "content": (
            "تو یک مربی ورزشی حرفه‌ای و دوست‌داشتنی هستی. "
            "فقط به سوالات مرتبط با ورزش، بدنسازی، تغذیه ورزشی، تمرینات، حرکات و برنامه‌های ورزشی پاسخ بده. "
            "با کاربران به صورت صمیمی و دوستانه صحبت کن، مثل یک دوست واقعی. "
            "کاربر می‌تواند تو را با صمیمیت صدا کند و از تو تشکر کند و تو با محبت جواب بدهی. "
            "اگر سوالی غیرورزشی پرسیده شد، با احترام بگو: "
            "'متأسفم، من فقط به سوالات ورزشی پاسخ می‌دهم.' "
            "جواب‌ها کوتاه، مفید، علمی و دوستانه باشند."
        )
    }

    user_message = {"role": "user", "content": user_input}

    data = {
        "model": "gpt-4o-mini",
        "messages": [system_prompt, user_message],
        "temperature": 0.0,
        "top_p": 1.0
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    res_json = response.json()
    return res_json["choices"][0]["message"]["content"]
