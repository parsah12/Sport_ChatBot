# import re

# def get_next_question(user_data):
#     if "age" not in user_data:
#         return "چند سالته؟ 👶"
#     elif "height" not in user_data:
#         return "قدت چقدره؟ (به سانتی‌متر) 📏"
#     elif "weight" not in user_data:
#         return "وزنت چقدره؟ (به کیلوگرم) ⚖️"
#     elif "goal" not in user_data:
#         return "هدفت چیه؟ (افزایش حجم / کاهش وزن / تناسب اندام) 🏋️‍♂️"
#     elif "gender" not in user_data:
#         return "جنسیتت چیه؟ (مرد / زن) 🚻"
#     else:
#         return None


# def validate_answer(question, answer):
#     """بررسی می‌کنه که پاسخ کاربر به سؤال مربوطه معتبر هست یا نه."""
#     answer = answer.strip().lower()

#     if "چند سالته" in question:
#         return bool(re.search(r"\d{1,2}", answer)), re.findall(r"\d{1,2}", answer)[0] if re.search(r"\d{1,2}", answer) else None

#     elif "قدت" in question:
#         return bool(re.search(r"\d{2,3}", answer)), re.findall(r"\d{2,3}", answer)[0] if re.search(r"\d{2,3}", answer) else None

#     elif "وزنت" in question:
#         return bool(re.search(r"\d{2,3}", answer)), re.findall(r"\d{2,3}", answer)[0] if re.search(r"\d{2,3}", answer) else None

#     elif "هدفت" in question:
#         valid_goals = ["حجم", "کاهش", "تناسب"]
#         for g in valid_goals:
#             if g in answer:
#                 return True, g
#         return False, None

#     elif "جنسیت" in question:
#         if "مرد" in answer or "زن" in answer:
#             return True, "مرد" if "مرد" in answer else "زن"
#         return False, None

#     return True, answer  # در صورت عدم تطابق خاص


# def generate_plan(user_data):
#     goal = user_data.get("goal", "").lower()
#     gender = user_data.get("gender", "").lower()

#     if "حجم" in goal:
#         workout = "🏋️ تمرینات سنگین ۴ روز در هفته با وزنه و افزایش تدریجی بار."
#         diet = "🍗 رژیم پر پروتئین شامل مرغ، تخم‌مرغ، برنج و سیب‌زمینی."
#     elif "کاهش" in goal:
#         workout = "🏃 تمرینات هوازی روزانه و تمرینات چربی‌سوز."
#         diet = "🥗 رژیم کم کالری با پروتئین بالا و حذف قند و چربی‌های بد."
#     else:
#         workout = "🤸 تمرینات ترکیبی برای حفظ تناسب اندام."
#         diet = "🍎 رژیم متعادل با نسبت مناسب پروتئین و کربوهیدرات."

#     return f"""
# 🎯 مشخصاتت:
# - سن: {user_data['age']}
# - قد: {user_data['height']} سانتی‌متر
# - وزن: {user_data['weight']} کیلوگرم
# - هدف: {user_data['goal']}
# - جنسیت: {user_data['gender']}

# 🔥 برنامه پیشنهادی:
# {workout}

# 🥗 رژیم پیشنهادی:
# {diet}
# """
