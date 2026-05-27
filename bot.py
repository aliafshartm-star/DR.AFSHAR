import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

PRICE = 1000000
CARD_NUMBER = "5859831868090340"
CARD_OWNER = "دکتر ناهید افشار"

WORK_DAYS = ["شنبه", "دوشنبه", "چهارشنبه"]

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
    status TEXT,
    receipt TEXT
)
""")
conn.commit()

# =========================
# USER STATE
# =========================
user_state = {}

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["فارسی", "English"]]
    await update.message.reply_text(
        "زبان را انتخاب کنید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# MAIN MENU
# =========================
async def main_menu(update: Update):
    keyboard = [["📅 درخواست نوبت"]]
    await update.message.reply_text(
        "به سیستم نوبت‌دهی خوش آمدید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# SHOW DAYS
# =========================
async def show_days(update: Update):
    keyboard = [[d] for d in WORK_DAYS]
    await update.message.reply_text(
        "روز را انتخاب کنید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# SHOW TIMES
# =========================
def get_times(day):
    cursor.execute("""
    SELECT time FROM appointments
    WHERE day=? AND status='confirmed'
    """, (day,))
    booked = [i[0] for i in cursor.fetchall()]

    times = []
    for h in range(14, 19):
        for m in [0, 30]:
            t = f"{h:02d}:{m:02d}"
            if t not in booked:
                times.append(t)
    return times

async def show_times(update: Update, day):
    times = get_times(day)
    keyboard = [[t] for t in times]

    await update.message.reply_text(
        "ساعت را انتخاب کنید",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# =========================
# SAVE APPOINTMENT
# =========================
async def save_appointment(update: Update, day, time):
    user = update.message.from_user

    cursor.execute("""
    INSERT INTO appointments (user_id, username, day, time, status)
    VALUES (?, ?, ?, ?, 'pending')
    """, (user.id, user.username, day, time))
    conn.commit()

    await update.message.reply_text(f"""
📅 نوبت ثبت شد (در انتظار رسید)

💰 هزینه: {PRICE}
💳 کارت: {CARD_NUMBER}
👤 به نام: {CARD_OWNER}

لطفاً عکس رسید را ارسال کنید.
""")

    if OWNER_ID:
        await context.bot.send_message(
            OWNER_ID,
            f"📌 نوبت جدید\n@{user.username}\n{day} {time}"
        )

# =========================
# HANDLE PHOTO (RECEIPT)
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    photo = update.message.photo[-1].file_id

    cursor.execute("""
    SELECT id FROM appointments
    WHERE user_id=? ORDER BY id DESC LIMIT 1
    """, (user.id,))

    row = cursor.fetchone()
    if not row:
        return

    appt_id = row[0]

    cursor.execute("""
    UPDATE appointments
    SET receipt=?, status='waiting_admin'
    WHERE id=?
    """, (photo, appt_id))
    conn.commit()

    await update.message.reply_text("رسید دریافت شد، منتظر تایید باشید")

    if OWNER_ID:
        await context.bot.send_photo(
            OWNER_ID,
            photo=photo,
            caption=f"""
📌 رسید جدید

User: @{user.username}
ID: {user.id}
ID appt: {appt_id}

/confirm_{appt_id}
/reject_{appt_id}
"""
        )

# =========================
# ADMIN CONFIRM / REJECT
# =========================
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return

    appt_id = update.message.text.split("_")[1]

    cursor.execute("""
    UPDATE appointments
    SET status='confirmed'
    WHERE id=?
    """, (appt_id,))
    conn.commit()

    await update.message.reply_text("تایید شد")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return

    appt_id = update.message.text.split("_")[1]

    cursor.execute("""
    UPDATE appointments
    SET status='rejected'
    WHERE id=?
    """, (appt_id,))
    conn.commit()

    await update.message.reply_text("رد شد")

# =========================
# MESSAGE HANDLER
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "فارسی":
        await main_menu(update)

    elif text == "📅 درخواست نوبت":
        await show_days(update)

    elif text in WORK_DAYS:
        user_state[user_id] = {"day": text}
        await show_times(update, text)

    elif ":" in text:
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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Regex(r"^/confirm_"), confirm))
    app.add_handler(MessageHandler(filters.Regex(r"^/reject_"), reject))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
