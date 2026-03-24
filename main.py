# ssc_reminder_bot.py
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import random
import requests

# ================= CONFIGURATION =================
BOT_TOKEN = "8721015114:AAH3Rh8mv2J2kfJrO4wFfoOkXfril0ACgWc"
CHAT_ID = "6730772884"
GEMINI_API_KEY = "AIzaSyCJlJ3X2ynVaFuq8l45lxI72EDA7NtX4j8"
SSC_EXAM_DATE = "2026-04-21"

SUBJECT_TIPS = {
    "math": ["গাণিতিক সূত্রগুলো মনে রাখো", "প্রতিদিন ১টি MCQ করে দেখো"],
    "english": ["দৈনন্দিন ৫টি নতুন শব্দ শিখো", "একটি ছোট গল্প পড়ো"],
    "science": ["বিজ্ঞান সূত্রগুলো রিভিশন করো", "প্র্যাকটিকাল নোটস চেক করো"]
}

# ================= FUNCTIONS =================

def get_days_left():
    today = datetime.date.today()
    exam_date = datetime.datetime.strptime(SSC_EXAM_DATE, "%Y-%m-%d").date()
    return (exam_date - today).days

def get_daily_tip():
    subject = random.choice(list(SUBJECT_TIPS.keys()))
    tips = SUBJECT_TIPS[subject]
    return random.choice(tips)

def build_daily_message():
    days_left = get_days_left()
    tip = get_daily_tip()
    message = f"💪 এসএসসি পরীক্ষা মাত্র {days_left} দিন বাকি!\nআজকের টিপস: {tip}\n📌 পড়ার সময়, রিল বন্ধ করো!"
    return message

def send_reminder():
    message = build_daily_message()
    bot.send_message(chat_id=CHAT_ID, text=message)

def gemini_chat(user_text):
    url = "https://api.gemini.com/v1/chat"  # Gemini API endpoint
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": f"তুমি একজন SSC পড়ুয়া ছাত্রকে সাহায্য করবে। প্রশ্ন: {user_text}",
        "max_output_tokens": 150
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "দুঃখিত, উত্তর পাওয়া যায়নি।")
        else:
            return "দুঃখিত, API তে সমস্যা হয়েছে।"
    except Exception as e:
        return f"API error: {e}"

# ================= TELEGRAM BOT =================

bot = Bot(token=BOT_TOKEN)
scheduler = BackgroundScheduler()

# ডেইলি রিমাইন্ডার: সকাল 7 টা এবং সন্ধ্যা 6 টা
scheduler.add_job(send_reminder, 'cron', hour=7, minute=0)
scheduler.add_job(send_reminder, 'cron', hour=18, minute=0)
scheduler.start()

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "হ্যালো! আমি তোমার SSC স্টাডি বট। প্রতিদিন সকাল ৭টা এবং সন্ধ্যা ৬টায় পড়ার রিমাইন্ডার দিব। 💪"
    )

def chat(update: Update, context: CallbackContext):
    user_msg = update.message.text
    answer = gemini_chat(user_msg)
    update.message.reply_text(answer)

updater = Updater(BOT_TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

updater.start_polling()
updater.idle()
