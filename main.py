import os
import datetime
import random
import asyncio
import threading
import pytz
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIGURATION =================
BOT_TOKEN = "8721015114:AAH3Rh8mv2J2kfJrO4wFfoOkXfril0ACgWc"
CHAT_ID = "6730772884"
GEMINI_API_KEY = "AIzaSyCJlJ3X2ynVaFuq8l45lxI72EDA7NtX4j8"
SSC_EXAM_DATE = "2026-04-21"

# Gemini AI Setup
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App (Render এর Port error বন্ধ করার জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    return "SSC Bot is Online!"

def run_flask():
    # Render অটোমেটিক PORT এনভায়রনমেন্ট ভেরিয়েবল সেট করে
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

SUBJECT_TIPS = {
    "math": ["গাণিতিক সূত্রগুলো রিভিশন করো।", "আজ অন্তত ২টা সৃজনশীল সমাধান করো।"],
    "english": ["৫টি নতুন Vocabulary শিখো।", "Right forms of verbs প্র্যাকটিস করো।"],
    "science": ["বিজ্ঞানের চিত্রগুলো লেবেলিং প্র্যাকটিস করো।", "মেইন বইয়ের লাল চিহ্নিত লাইনগুলো পড়ো।"],
    "general": ["পড়ার সময় সোশ্যাল মিডিয়া থেকে দূরে থাকো।", "পর্যাপ্ত পানি পান করো ও সুস্থ থাকো।"]
}

# ================= FUNCTIONS =================

def get_days_left():
    # বাংলাদেশ টাইমজোন সেট করা
    tz = pytz.timezone('Asia/Dhaka')
    today = datetime.datetime.now(tz).date()
    exam_date = datetime.datetime.strptime(SSC_EXAM_DATE, "%Y-%m-%d").date()
    delta = exam_date - today
    return max(0, delta.days)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    days_left = get_days_left()
    subject = random.choice(list(SUBJECT_TIPS.keys()))
    tip = random.choice(SUBJECT_TIPS[subject])
    
    message = (
        f"📚 **SSC ২০২৬ প্রস্তুতি আপডেট** 📚\n\n"
        f"⏰ পরীক্ষা বাকি: `{days_left}` দিন মাত্র!\n"
        f"💡 আজকের টিপস: {tip}\n\n"
        f"পড়াশোনা শুরু করো, সময় নষ্ট করো না! 💪"
    )
    try:
        await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Error sending message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "হ্যালো! আমি তোমার SSC স্টাডি বট।\n"
        "✅ আমি প্রতিদিন সকাল ৭টা ও সন্ধ্যা ৬টায় তোমাকে রিমাইন্ডার দিব।\n"
        "✅ যেকোনো প্রশ্ন করলে আমি উত্তর দিব (Gemini AI ব্যবহার করে)।"
    )

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_chat_action("typing")
    
    try:
        # Gemini AI prompt
        prompt = f"তুমি একজন SSC পরীক্ষার্থীর সাহায্যকারী মেন্টর। ছাত্রের প্রশ্ন: {user_text}। সংক্ষেপে বাংলায় উত্তর দাও।"
        response = gemini_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("দুঃখিত, এই মুহূর্তে আমি উত্তর দিতে পারছি না।")

# ================= MAIN RUNNER =================

def main():
    # ১. Flask সার্ভার চালু করা (একটি আলাদা থ্রেডে)
    threading.Thread(target=run_flask, daemon=True).start()

    # ২. টেলিগ্রাম বট সেটাআপ
    application = Application.builder().token(BOT_TOKEN).build()

    # ৩. হ্যান্ডলার যুক্ত করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # ৪. সিডিউলার সেট করা (বাংলাদেশ সময় অনুযায়ী)
    scheduler = AsyncIOScheduler(timezone="Asia/Dhaka")
    # প্রতিদিন সকাল ৭:০০ এবং সন্ধ্যা ৬:০০ টায় মেসেজ পাঠাবে
    scheduler.add_job(send_reminder, 'cron', hour=7, minute=0, args=[application])
    scheduler.add_job(send_reminder, 'cron', hour=18, minute=0, args=[application])
    scheduler.start()

    # ৫. বট চালু করা
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
