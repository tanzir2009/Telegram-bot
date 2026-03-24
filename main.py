import os
import datetime
import random
import threading
import pytz
import asyncio
import re
from flask import Flask
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "8721015114:AAH3Rh8mv2J2kfJrO4wFfoOkXfril0ACgWc"
CHAT_ID = "6730772884"
SSC_EXAM_DATE = "2026-04-21"

# আপনার দেওয়া Hugging Face Token
HF_TOKEN = "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"

# DeepSeek AI Setup (Using Hugging Face Router & AsyncOpenAI)
hf_client = AsyncOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# Flask App (Render-এর পোর্ট এরর এবং Cron-job.org এর জন্য)
app = Flask(__name__)

@app.route('/')
def home():
    return "SSC Bot is Online with DeepSeek-R1 AI!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# পড়াশোনার টিপস ডাটাবেস
SUBJECT_TIPS = {
    "math":["বীজগণিতের সূত্রগুলো একবার লিখে ফেলো।", "আজ অন্তত ৫টি জ্যামিতি প্র্যাকটিস করো।"],
    "english":["দৈনিক ৫টি নতুন Vocabulary মুখস্থ করো।", "একটি Completing Story নিজে লেখার চেষ্টা করো।"],
    "science":["পদার্থবিজ্ঞানের গাণিতিক সমস্যাগুলো সমাধান করো।", "জীববিজ্ঞানের চিত্রগুলো লেবেলিং প্র্যাকটিস করো।"],
    "general":["পড়ার টেবিল গুছিয়ে রাখো, মনোযোগ বাড়বে।", "রাত জেগে না পড়ে ভোরে পড়ার অভ্যাস করো।"]
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
    await update.message.reply_text(
        "হ্যালো! আমি তোমার SSC স্টাডি পার্টনার (DeepSeek AI)।\n\n"
        "✅ প্রতিদিন সকাল ৭টা ও সন্ধ্যা ৬টায় আমি তোমাকে রিমাইন্ডার দিব।\n"
        "✅ পড়াশোনা নিয়ে যেকোনো প্রশ্ন করলে আমি উত্তর দিব।"
    )

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # বট টাইপিং স্ট্যাটাস দেখাবে
    await update.message.reply_chat_action("typing")
    
    try:
        prompt = f"তুমি একজন এসএসসি পরীক্ষার্থীর সাহায্যকারী শিক্ষক। ছাত্রের প্রশ্ন: {user_text}। সংক্ষেপে এবং সুন্দর করে বাংলায় উত্তর দাও।"
        
        # Hugging Face Router দিয়ে DeepSeek-R1 কল করা
        response = await hf_client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        # DeepSeek-R1 মডেলের <think> ট্যাগটি মুছে আসল উত্তরটি বের করা হচ্ছে
        clean_answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
        
        if not clean_answer:
            clean_answer = answer # যদি কোনো কারণে ট্যাগ না থাকে
            
        await update.message.reply_text(clean_answer)
            
    except Exception as e:
        error_msg = str(e)
        print(f"DeepSeek Error: {error_msg}")
        await update.message.reply_text(f"⚠️ এআই সার্ভারে সমস্যা হচ্ছে।\nError: `{error_msg[:100]}`\nদয়া করে একটু পর আবার চেষ্টা করো।", parse_mode='Markdown')

# ================= MAIN EXECUTION =================

def main():
    # ১. Flask সার্ভার আলাদা থ্রেডে চালু করা
    threading.Thread(target=run_flask, daemon=True).start()

    # ২. টেলিগ্রাম বট এপ্লিকেশন তৈরি (JobQueue সহ)
    application = Application.builder().token(BOT_TOKEN).build()

    # ৩. রিমাইন্ডার সিডিউল করা
    job_queue = application.job_queue
    tz = pytz.timezone('Asia/Dhaka')

    # প্রতিদিন সকাল ৭:০০ টায় রিমাইন্ডার (BD Time)
    job_queue.run_daily(send_reminder, time=datetime.time(hour=7, minute=0, tzinfo=tz))

    # প্রতিদিন সন্ধ্যা ৬:০০ টায় রিমাইন্ডার (BD Time)
    job_queue.run_daily(send_reminder, time=datetime.time(hour=18, minute=0, tzinfo=tz))

    # ৪. কমান্ড এবং মেসেজ হ্যান্ডলার যুক্ত করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # ৫. বট পোলিং শুরু করা
    print("Bot is starting with DeepSeek-R1...")
    application.run_polling()

if __name__ == "__main__":
    main()
