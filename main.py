import os
import datetime
import random
import threading
import pytz
import asyncio
from flask import Flask
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "8721015114:AAH3Rh8mv2J2kfJrO4wFfoOkXfril0ACgWc"
CHAT_ID = "6730772884"
GEMINI_API_KEY = "AIzaSyCJlJ3X2ynVaFuq8l45lxI72EDA7NtX4j8"
SSC_EXAM_DATE = "2026-04-21"

# Gemini AI Setup
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # সেফটি সেটিংস পুরোপুরি শিথিল করা হয়েছে যাতে এরর না আসে
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    gemini_model = genai.GenerativeModel(
        model_name='gemini-2.5-flash-lite',
        safety_settings=safety_settings
    )
    print("Gemini Model Initialized Successfully")
except Exception as e:
    print(f"Gemini Init Error: {e}")

# Flask App for Render/Cron-job
app = Flask(__name__)

@app.route('/')
def home():
    return "SSC Bot is Online! Waiting for cron-job..."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

SUBJECT_TIPS = {
    "math": ["বীজগণিতের সূত্রগুলো একবার লিখে ফেলো।", "আজ অন্তত ৫টি জ্যামিতি প্র্যাকটিস করো।"],
    "english": ["দৈনিক ৫টি নতুন Vocabulary মুখস্থ করো।", "একটি Completing Story নিজে লেখার চেষ্টা করো।"],
    "science": ["পদার্থবিজ্ঞানের গাণিতিক সমস্যাগুলো সমাধান করো।", "জীববিজ্ঞানের চিত্রগুলো লেবেলিং প্র্যাকটিস করো।"],
    "general": ["পড়ার টেবিল গুছিয়ে রাখো, মনোযোগ বাড়বে।", "রাত জেগে না পড়ে ভোরে পড়ার অভ্যাস করো।"]
}

# ================= FUNCTIONS =================

def get_days_left():
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
        f"🔔 **এসএসসি ২০২৬ রিমাইন্ডার** 🔔\n\n"
        f"📖 পরীক্ষা শুরু হতে বাকি: `{days_left}` দিন মাত্র!\n"
        f"💡 আজকের বিশেষ টিপস: {tip}\n\n"
        f"সময়কে কাজে লাগাও! 💪"
    )
    try:
        await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Reminder Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("হ্যালো! আমি তোমার SSC স্টাডি পার্টনার। আমাকে পড়াশোনা নিয়ে যেকোনো প্রশ্ন করতে পারো।")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_chat_action("typing")
    
    try:
        # Prompt তৈরি
        prompt = f"তুমি একজন এসএসসি পরীক্ষার্থীর মেন্টর। ছাত্রের প্রশ্ন: {user_text}। সংক্ষেপে বাংলায় উত্তর দাও।"
        
        # Synchronous call-কে Thread-এ চালানো হচ্ছে যাতে বট হ্যাং না হয়
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("দুঃখিত, Gemini কোনো উত্তর দিতে পারেনি (হয়তো সেফটি ফিল্টারে ব্লক হয়েছে)।")
            
    except Exception as e:
        # আসল এরর মেসেজটি টেলিগ্রামে দেখাবে যাতে আমরা বুঝতে পারি সমস্যা কোথায়
        error_msg = str(e)
        print(f"Full Error: {error_msg}")
        await update.message.reply_text(f"⚠️ দুঃখিত, একটি সমস্যা হয়েছে।\nError: `{error_msg[:100]}`", parse_mode='Markdown')

# ================= MAIN EXECUTION =================

def main():
    # ১. Flask চালু করা
    threading.Thread(target=run_flask, daemon=True).start()

    # ২. টেলিগ্রাম বট তৈরি (JobQueue সহ)
    application = Application.builder().token(BOT_TOKEN).build()

    # ৩. রিমাইন্ডার সিডিউল (BD Time)
    job_queue = application.job_queue
    tz = pytz.timezone('Asia/Dhaka')

    # প্রতিদিন সকাল ৭টা ও সন্ধ্যা ৬টা
    job_queue.run_daily(send_reminder, time=datetime.time(hour=7, minute=0, tzinfo=tz))
    job_queue.run_daily(send_reminder, time=datetime.time(hour=18, minute=0, tzinfo=tz))

    # ৪. হ্যান্ডলার যুক্ত করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # ৫. বট স্টার্ট
    print("Bot is starting with Synchronous AI support...")
    application.run_polling()

if __name__ == "__main__":
    main()
