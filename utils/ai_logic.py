import requests
import os
import base64
from PIL import Image

OPENROUTER_API_KEY = "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"

def compress_image(filepath, max_size=1024, quality=85):
    try:
        img = Image.open(filepath)
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        output_path = filepath.replace('.', '_compressed.')
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        return output_path
    except:
        return filepath

def generate_plan(chat_history):
    url = "https://openrouter.ai/api/v1/chat/completions"

    system_prompt = {
        "role": "system",
        "content": (
            "You are a professional fitness coach specializing in body analysis. "
            "ALWAYS analyze the uploaded image(s) in detail: estimate body fat %, muscle distribution, "
            "posture issues, strengths/weaknesses (e.g., strong shoulders, weak core). "
            "Then create a PERSONALIZED workout plan in Persian based on the image and user query. "
            "If user speaks Persian, respond ONLY in Persian. "
            "NEVER say 'I can't see the image' or give general advice. Always provide SPECIFIC analysis."
        )
    }

    messages = [system_prompt]
    has_media = False

    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        content_list = []

        if msg.get("content", "").strip():
            content_list.append({"type": "text", "text": msg["content"]})

        if "file" in msg:
            file_info = msg["file"]
            filepath = os.path.join("static", "uploads", file_info["filename"])

            if os.path.exists(filepath) and file_info["mimeType"].startswith("image/"):
                compressed_path = compress_image(filepath)
                try:
                    with open(compressed_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    content_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    })
                    has_media = True
                    
                    if compressed_path != filepath:
                        os.remove(compressed_path)
                        
                except Exception as e:
                    content_list.append({"type": "text", "text": f"[Image error: {str(e)}]"})
            else:
                content_list.append({"type": "text", "text": f"[File: {file_info.get('original_name', 'unknown')}]"})

        if content_list:
            messages.append({"role": role, "content": content_list})
        elif msg.get("content", "").strip():
            messages.append({"role": role, "content": msg["content"]})

    # Llama 3.2 90B Vision — رایگان، قدرتمند، و دقیق برای تحلیل بدن
    model = "meta-llama/llama-3.2-90b-vision-instruct"

    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "top_p": 0.3,
        "max_tokens": 1500
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://127.0.0.1:8000",
        "X-Title": "Fitness Coach AI",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text if e.response else str(e)
        return f"خطای API: {e.response.status_code if e.response else 'Unknown'} - {error_detail[:200]}..."
    except Exception as e:
        return f"خطای غیرمنتظره: {str(e)}"