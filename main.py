import os
import datetime
import random
import threading
import pytz
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "8721015114:AAH3Rh8mv2J2kfJrO4wFfoOkXfril0ACgWc"
CHAT_ID = "6730772884"
GEMINI_API_KEY = "AIzaSyCJlJ3X2ynVaFuq8l45lxI72EDA7NtX4j8"
SSC_EXAM_DATE = "2026-04-21"

# Gemini AI Setup
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Flask App (Render-এর পোর্ট এরর এবং Cron-job.org এর জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    # এটি cron-job.org কে রেসপন্স দিবে
    return "SSC Bot is Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# পড়াশোনার টিপস ডাটাবেস
SUBJECT_TIPS = {
    "math": ["বীজগণিতের সূত্রগুলো একবার লিখে ফেলো।", "আজ অন্তত ৫টি জ্যামিতি প্র্যাকটিস করো।"],
    "english": ["দৈনিক ৫টি নতুন Vocabulary মুখস্থ করো।", "একটি Completing Story নিজে লেখার চেষ্টা করো।"],
    "science": ["পদার্থবিজ্ঞানের গাণিতিক সমস্যাগুলো সমাধান করো।", "জীববিজ্ঞানের চিত্রগুলো লেবেলিং প্র্যাকটিস করো।"],
    "general": ["পড়ার টেবিল গুছিয়ে রাখো, মনোযোগ বাড়বে।", "রাত জেগে না পড়ে ভোরে পড়ার অভ্যাস করো।", "পড়ার সময় স্মার্টফোন অন্য রুমে রাখো।"]
}

# ================= FUNCTIONS =================

def get_days_left():
    # বাংলাদেশ সময় অনুযায়ী দিন গণনা
    tz = pytz.timezone('Asia/Dhaka')
    today = datetime.datetime.now(tz).date()
    exam_date = datetime.datetime.strptime(SSC_EXAM_DATE, "%Y-%m-%d").date()
    delta = exam_date - today
    return max(0, delta.days)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """প্রতিদিন নির্দিষ্ট সময়ে এই ফাংশনটি মেসেজ পাঠাবে"""
    days_left = get_days_left()
    subject = random.choice(list(SUBJECT_TIPS.keys()))
    tip = random.choice(SUBJECT_TIPS[subject])
    
    message = (
        f"🔔 **এসএসসি ২০২৬ রিমাইন্ডার** 🔔\n\n"
        f"📖 পরীক্ষা শুরু হতে বাকি: `{days_left}` দিন মাত্র!\n"
        f"💡 আজকের বিশেষ টিপস: {tip}\n\n"
        f"সময়কে কাজে লাগাও, স্বপ্ন তোমার হাতের মুঠোয়! 💪"
    )
    try:
        # সরাসরি আপনার CHAT_ID তে মেসেজ পাঠাবে
        await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Error sending message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start কমান্ড দিলে এই মেসেজটি আসবে"""
    await update.message.reply_text(
        "স্বাগতম! আমি তোমার SSC স্টাডি পার্টনার।\n\n"
        "✅ প্রতিদিন সকাল ৭টা ও সন্ধ্যা ৬টায় আমি তোমাকে রিমাইন্ডার দিব।\n"
        "✅ যেকোনো প্রশ্ন করলে আমি Gemini AI ব্যবহার করে উত্তর দিব।"
    )

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """যেকোনো টেক্সট মেসেজ আসলে AI উত্তর দিবে"""
    user_text = update.message.text
    # বট টাইপিং স্ট্যাটাস দেখাবে
    await update.message.reply_chat_action("typing")
    
    try:
        prompt = f"তুমি একজন এসএসসি পরীক্ষার্থীর মেন্টর। ছাত্রের প্রশ্ন: {user_text}। সংক্ষেপে বাংলায় উত্তর দাও।"
        response = gemini_model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("দুঃখিত বন্ধু, আমি এই মুহূর্তে উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করো।")

# ================= MAIN EXECUTION =================

def main():
    # ১. Flask সার্ভার আলাদা থ্রেডে চালু করা (Render/Cron-job এর জন্য)
    threading.Thread(target=run_flask, daemon=True).start()

    # ২. টেলিগ্রাম বট এপ্লিকেশন তৈরি (JobQueue সহ)
    application = Application.builder().token(BOT_TOKEN).build()

    # ৩. রিমাইন্ডার সিডিউল করা (Job Queue ব্যবহার করে)
    job_queue = application.job_queue
    tz = pytz.timezone('Asia/Dhaka')

    # প্রতিদিন সকাল ৭:০০ টায় রিমাইন্ডার (BD Time)
    time_7am = datetime.time(hour=7, minute=0, second=0, tzinfo=tz)
    job_queue.run_daily(send_reminder, time=time_7am)

    # প্রতিদিন সন্ধ্যা ৬:০০ টায় রিমাইন্ডার (BD Time)
    time_6pm = datetime.time(hour=18, minute=0, second=0, tzinfo=tz)
    job_queue.run_daily(send_reminder, time=time_6pm)

    # ৪. কমান্ড এবং মেসেজ হ্যান্ডলার যুক্ত করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # ৫. বট পোলিং শুরু করা
    print("SSC Study Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
