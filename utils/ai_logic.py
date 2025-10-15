import requests

OPENROUTER_API_KEY = "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"

def generate_plan(chat_history):
    """
    تولید پاسخ ورزشی با حافظه کامل پیام‌ها.
    chat_history: لیست دیکشنری {"role": "user"|"bot", "content": "پیام"}
    """
    url = "https://openrouter.ai/api/v1/chat/completions"

    system_prompt = {
        "role": "system",
        "content": (
            "تو یک مربی ورزشی حرفه‌ای و دوست‌داشتنی هستی. "
            "تمامی پیام‌های قبلی کاربر و ربات را در نظر بگیر و پاسخ بده. "
            "فقط به سوالات مرتبط با ورزش پاسخ بده. "
            "جواب‌ها کوتاه، مفید و دوستانه باشند."
        )
    }

    # تبدیل role "bot" به "assistant" برای API
    messages = [system_prompt] + [
        {"role": "user" if m["role"]=="user" else "assistant", "content": m["content"]}
        for m in chat_history
    ]

    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.1,
        "top_p": 0.3
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    res_json = response.json()
    return res_json["choices"][0]["message"]["content"]
