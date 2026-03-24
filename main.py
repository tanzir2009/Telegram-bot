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

# Gemini AI Setup (With Safety Settings Fix)
genai.configure(api_key=GEMINI_API_KEY)
# সেফটি সেটিংস অফ করা হয়েছে যাতে সব প্রশ্নের উত্তর দেয়
gemini_model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
)

# Flask App for Render/Cron-job
app = Flask(__name__)

@app.route('/')
def home():
    return "SSC Bot is Active and AI is working!"

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
        f"🔔 **এসএসসি ২০২৬ আপডেট** 🔔\n\n"
        f"📖 পরীক্ষা শুরু হতে বাকি: `{days_left}` দিন মাত্র!\n"
        f"💡 আজকের বিশেষ টিপস: {tip}\n\n"
        f"সময়কে কাজে লাগাও! 💪"
    )
    try:
        await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Reminder Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("হ্যালো! আমি তোমার SSC স্টাডি পার্টনার। প্রশ্ন করো, আমি উত্তর দিচ্ছি!")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_chat_action("typing")
    
    try:
        # Gemini-র Async মেথড ব্যবহার করা হয়েছে
        prompt = f"তুমি একজন এসএসসি পরীক্ষার্থীর মেন্টর। ছাত্রের প্রশ্ন: {user_text}। সংক্ষেপে বাংলায় উত্তর দাও।"
        response = await gemini_model.generate_content_async(prompt)
        
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("দুঃখিত, আমি উত্তরটি তৈরি করতে পারছি না।")
            
    except Exception as e:
        print(f"Gemini Error: {e}")
        await update.message.reply_text(f"AI এরর: {str(e)[:50]}... দয়া করে আবার চেষ্টা করো।")

# ================= MAIN EXECUTION =================

def main():
    # Flask চালু করা
    threading.Thread(target=run_flask, daemon=True).start()

    # টেলিগ্রাম বট তৈরি
    application = Application.builder().token(BOT_TOKEN).build()

    # রিমাইন্ডার সিডিউল
    job_queue = application.job_queue
    tz = pytz.timezone('Asia/Dhaka')

    # সকাল ৭টা ও সন্ধ্যা ৬টা
    job_queue.run_daily(send_reminder, time=datetime.time(hour=7, minute=0, tzinfo=tz))
    job_queue.run_daily(send_reminder, time=datetime.time(hour=18, minute=0, tzinfo=tz))

    # হ্যান্ডলার
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    print("Bot is starting with Gemini Async Fix...")
    application.run_polling()

if __name__ == "__main__":
    main()
