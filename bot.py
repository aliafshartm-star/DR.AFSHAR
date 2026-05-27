import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# =========================
# CONFIG (ENV VARIABLES)
# =========================
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

PRICE = int(os.getenv("PRICE", "1000000"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
CARD_OWNER = os.getenv("CARD_OWNER", "Doctor")

WORK_DAYS = ["Saturday", "Monday", "Wednesday"]

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("clinic.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    day TEXT,
    time TEXT,
    status TEXT
)
""")
conn.commit()

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["فارسی", "English"]]
    await update.message.reply_text(
        "زبان را انتخاب کنید / Choose language",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# MENU
# =========================
async def main_menu(update: Update):
    keyboard = [["📅 درخواست نوبت"]]
    await update.message.reply_text(
        "به سیستم نوبت‌دهی خوش آمدید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# DAYS
# =========================
async def show_days(update: Update):
    keyboard = [[day] for day in WORK_DAYS]
    await update.message.reply_text(
        "روز مورد نظر را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# TIME SLOTS
# =========================
def get_available_times(day):
    cursor.execute("SELECT time FROM appointments WHERE day=? AND status='confirmed'", (day,))
    booked = [i[0] for i in cursor.fetchall()]

    times = []
    for hour in range(14, 19):
        for minute in [0, 30]:
            t = f"{hour:02d}:{minute:02d}"
            if t not in booked:
                times.append(t)

    return times

async def show_times(update: Update, day):
    times = get_available_times(day)
    keyboard = [[t] for t in times]

    await update.message.reply_text(
        "ساعت مورد نظر را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# SAVE APPOINTMENT
# =========================
async def save_appointment(update: Update, day, time):
    user = update.message.from_user

    cursor.execute("""
    INSERT INTO appointments (user_id, username, day, time, status)
    VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, day, time, "pending"))
    conn.commit()

    await update.message.reply_text(
        f"""
📅 نوبت شما ثبت شد (در انتظار تایید)

👨‍⚕️ هزینه ویزیت: {PRICE}
💳 کارت: {CARD_NUMBER}
👤 به نام: {CARD_OWNER}

لطفاً پس از پرداخت، عکس رسید را ارسال کنید.
        """
    )

    # notify owner
    if OWNER_ID:
        await context.bot.send_message(
            OWNER_ID,
            f"📌 نوبت جدید\nUser: @{user.username}\nDay: {day}\nTime: {time}"
        )

# =========================
# MESSAGE HANDLER
# =========================
user_state = {}

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    # language
    if text == "فارسی":
        await main_menu(update)

    elif text == "📅 درخواست نوبت":
        await show_days(update)

    elif text in WORK_DAYS:
        user_state[user_id] = {"day": text}
        await show_times(update, text)

    elif ":" in text:  # time selection
        day = user_state.get(user_id, {}).get("day")

        if day:
            await save_appointment(update, day, text)

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
