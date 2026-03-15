import os
import logging
import requests
from datetime import time, datetime
from dotenv import load_dotenv

load_dotenv()
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SHEET_URL  = os.environ.get("SHEET_URL", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

(BP_UPPER, BP_LOWER, MORNING_MED, EVENING_MED, NOSE_BLEED, DAY_SUMMARY, OTHER_TEXT) = range(7)

YES_NO_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("✅ Yes"), KeyboardButton("❌ No")]],
    resize_keyboard=True, one_time_keyboard=True
)

DAY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Normal"),            KeyboardButton("Mild Symptoms")],
        [KeyboardButton("Moderate Symptoms"), KeyboardButton("Severe Symptoms")],
        [KeyboardButton("Fever"),             KeyboardButton("Fatigue")],
        [KeyboardButton("Hypertension"),      KeyboardButton("Hypotension")],
        [KeyboardButton("Anxiety"),           KeyboardButton("Optimistic")],
        [KeyboardButton("Lethargy"),          KeyboardButton("Stable")],
        [KeyboardButton("Infection/Cold"),    KeyboardButton("Vigorous")],
        [KeyboardButton("Other (specify below)")]
    ],
    resize_keyboard=True, one_time_keyboard=True
)

DAY_OPTIONS_MAP = {
    "Normal": "Normal", "Mild Symptoms": "Mild Symptoms",
    "Moderate Symptoms": "Moderate Symptoms", "Severe Symptoms": "Severe Symptoms",
    "Fever": "Fever", "Fatigue": "Fatigue",
    "Hypertension": "Hypertension", "Hypotension": "Hypotension",
    "Anxiety": "Anxiety", "Optimistic": "Optimistic",
    "Lethargy": "Lethargy", "Stable": "Stable",
    "Infection/Cold": "Respiratory Infection/Cold", "Vigorous": "Vigorous",
}

def is_before_8pm() -> bool:
    return datetime.now().hour < 20

async def finish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    payload = {
        "date":        now.strftime("%d/%m/%Y"),
        "time":        now.strftime("%I:%M %p"),
        "bp_upper":    ctx.user_data.get("bp_upper", "-"),
        "bp_lower":    ctx.user_data.get("bp_lower", "-"),
        "morning_med": ctx.user_data.get("morning_med", "-"),
        "evening_med": ctx.user_data.get("evening_med", "-"),
        "nose_bleed":  ctx.user_data.get("nose_bleed", "-"),
        "day_summary": ctx.user_data.get("day_summary", "-"),
    }
    logging.info(f"📤 Payload: {payload}")
    try:
        resp = requests.post(SHEET_URL, json=payload, timeout=15, allow_redirects=True)
        logging.info(f"📊 Sheet: {resp.text}")
        saved = "✅ Your report has been saved!"
    except Exception as ex:
        logging.error(f"❌ Error: {ex}")
        saved = "⚠️ Could not save. Please try again."

    bp_warn = ""
    try:
        upper, lower = int(payload["bp_upper"]), int(payload["bp_lower"])
        if upper > 140 or lower > 90:
            bp_warn = "\n⚠️ *Hypertension Detected: BP Elevated. Consult Healthcare Provider.*"
        elif upper < 90 or lower < 60:
            bp_warn = "\n⚠️ *Hypotension Detected: BP Low. Ensure adequate rest and hydration.*"
        else:
            bp_warn = "\n✅ *Blood Pressure Within Normal Range.*"
    except Exception:
        pass

    med_warn = ""
    if payload.get("morning_med") == "No" or payload.get("evening_med") == "No":
        med_warn = "\n💊 *Important: Medication Compliance is Critical. Do not miss scheduled doses.*"

    evening_display = "Not yet ⏰" if "before 8 PM" in payload["evening_med"] else payload["evening_med"]

    summary = (
        f"✅ *Clinical Health Report Completed*\n\n"
        f"📅 Date: {payload['date']}\n"
        f"🕐 Time: {payload['time']}\n\n"
        f"📊 Blood Pressure: *{payload['bp_upper']}/{payload['bp_lower']} mmHg*{bp_warn}\n"
        f"💊 Morning Medication (10 AM): *{payload['morning_med']}*\n"
        f"💊 Evening Medication (8 PM): *{evening_display}*{med_warn}\n"
        f"🩸 Epistaxis (Nose Bleeding): *{payload['nose_bleed']}*\n"
        f"📋 Clinical Status: *{payload['day_summary']}*\n\n"
        f"{saved}\n\nPlease maintain your health regimen. 💙"
    )
    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.bot_data["father_chat_id"] = update.effective_chat.id
    await update.message.reply_text(
        "👋 Welcome to Clinical Health Monitoring\n\n"
        "I am your *Daily Health Assessment Bot* 🤖\n\n"
        "Automated reminders scheduled:\n"
        "🌅 *11:00 AM* — Morning Clinical Assessment\n"
        "🌆 *8:00 PM*  — Evening Health Evaluation\n\n"
        "Available Commands:\n"
        "👉 /health — Initiate Health Check\n"
        "👉 /cancel — Cancel Assessment\n\n"
        "Maintaining consistent health monitoring is essential. 💙",
        parse_mode="Markdown"
    )

async def health_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.bot_data["father_chat_id"] = update.effective_chat.id
    ctx.user_data.clear()
    await update.message.reply_text(
        "🩺 *Clinical Assessment Protocol Initiated*\n\n"
        "Please enter systolic blood pressure reading (mmHg):\n\nExample: *130*",
        parse_mode="Markdown"
    )
    return BP_UPPER

async def get_bp_upper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().translate(str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789"))
    if not text.isdigit():
        await update.message.reply_text("⚠️ Invalid input. Numbers only.\n\nExample: *130*", parse_mode="Markdown")
        return BP_UPPER
    ctx.user_data["bp_upper"] = text
    await update.message.reply_text(f"✓ Systolic: *{text}* mmHg recorded\n\nNow enter diastolic reading:\n\nExample: *80*", parse_mode="Markdown")
    return BP_LOWER

async def get_bp_lower(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().translate(str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789"))
    if not text.isdigit():
        await update.message.reply_text("⚠️ Invalid input. Numbers only.\n\nExample: *80*", parse_mode="Markdown")
        return BP_LOWER
    ctx.user_data["bp_lower"] = text
    await update.message.reply_text(
        f"✓ Diastolic: *{text}* mmHg recorded\n\n💊 Did you take your *morning medication (10 AM)?*",
        parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD
    )
    return MORNING_MED

async def get_morning_med(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "yes" in text:
        ctx.user_data["morning_med"] = "Yes"
    elif "no" in text:
        ctx.user_data["morning_med"] = "No"
    else:
        await update.message.reply_text("⚠️ Please tap *Yes* or *No* 👆", parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD)
        return MORNING_MED

    if is_before_8pm():
        ctx.user_data["evening_med"] = "Not yet (before 8 PM)"
        await update.message.reply_text(
            "⏰ *Evening medication time (8 PM) has not arrived yet*\n\n"
            "🩸 Did you experience *epistaxis (nose bleeding)* today?",
            parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD
        )
        return NOSE_BLEED
    else:
        await update.message.reply_text(
            "💊 Did you take your *evening medication dose (8 PM)?*",
            parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD
        )
        return EVENING_MED

async def get_evening_med(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "yes" in text:
        ctx.user_data["evening_med"] = "Yes"
    elif "no" in text:
        ctx.user_data["evening_med"] = "No"
    else:
        await update.message.reply_text("⚠️ Please tap *Yes* or *No* 👆", parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD)
        return EVENING_MED
    await update.message.reply_text("🩸 Did you experience *epistaxis (nose bleeding)* today?", parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD)
    return NOSE_BLEED

async def get_nose_bleed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "yes" in text:
        ctx.user_data["nose_bleed"] = "Yes"
    elif "no" in text:
        ctx.user_data["nose_bleed"] = "No"
    else:
        await update.message.reply_text("⚠️ Please tap *Yes* or *No* 👆", parse_mode="Markdown", reply_markup=YES_NO_KEYBOARD)
        return NOSE_BLEED
    await update.message.reply_text(
        "📋 *Clinical Status Assessment*\n\nSelect your current health condition:\n_(Or select Other to provide custom details)_",
        parse_mode="Markdown", reply_markup=DAY_KEYBOARD
    )
    return DAY_SUMMARY

async def get_day_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if "Other" in text:
        await update.message.reply_text("✍️ Please document any additional clinical observations:", reply_markup=ReplyKeyboardRemove())
        return OTHER_TEXT
    ctx.user_data["day_summary"] = DAY_OPTIONS_MAP.get(text, text)
    logging.info(f"✅ day_summary = '{ctx.user_data['day_summary']}'")
    return await finish(update, ctx)

async def get_other_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["day_summary"] = update.message.text.strip()
    return await finish(update, ctx)

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assessment cancelled. Type /health to resume. 🙏", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Please type /health and follow the prompts 👆")

async def send_morning_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.bot_data.get("father_chat_id")
    if chat_id:
        await ctx.bot.send_message(chat_id=chat_id, parse_mode="Markdown",
            text="🌅 *Morning Clinical Assessment Reminder* 🙏\n\nTime for your morning health evaluation.\n\n👉 Type */health* to start\n\nHealth monitoring is essential. 💙")

async def send_evening_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.bot_data.get("father_chat_id")
    if chat_id:
        await ctx.bot.send_message(chat_id=chat_id, parse_mode="Markdown",
            text="🌆 *Evening Clinical Assessment Reminder* 🙏\n\nTime for your evening health evaluation.\nAlso time to take your *evening medication (8 PM)*!\n\n👉 Type */health* to complete assessment\n\nRest well. 💙")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("health", health_start)],
        states={
            BP_UPPER:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bp_upper)],
            BP_LOWER:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bp_lower)],
            MORNING_MED: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_morning_med)],
            EVENING_MED: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_evening_med)],
            NOSE_BLEED:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nose_bleed)],
            DAY_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_day_summary)],
            OTHER_TEXT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_other_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True, per_message=False,
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.job_queue.run_daily(send_morning_reminder, time=time(hour=5, minute=30, second=0))   # 11 AM IST
    app.job_queue.run_daily(send_evening_reminder, time=time(hour=14, minute=30, second=0))  # 8 PM IST
    print("🤖 Anna Health Bot is running!")
    print("⏰ Morning reminder: 11:00 AM IST")
    print("⏰ Evening reminder:  8:00 PM IST")
    print("Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
