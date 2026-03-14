import logging
import requests
from datetime import time, datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

# ── Config ────────────────────────────────────────────────
BOT_TOKEN = "8215129997:AAF46COi9aEbPr_yBv38V-6LAvSqhwPPKSQ"
SHEET_URL  = "https://script.google.com/macros/s/AKfycbw1YaoRq6B3s_Pf3epwTK93zYN5H0Iw1OzkCgrM_KTwUd629sPyzeN9wSaLq2mefnWbdA/exec"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ── Conversation States ───────────────────────────────────
# Using distinct integers — no ambiguity between states
(
    BP_UPPER,
    BP_LOWER,
    MORNING_MED,
    AFTERNOON_MED,
    NOSE_BLEED,
    DAY_SUMMARY,
    OTHER_TEXT,        # separate state for free-text after "Other"
) = range(7)

YES_NO_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("✅ Yes"), KeyboardButton("❌ No")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

DAY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("😊 Great"),      KeyboardButton("🙂 Good")],
        [KeyboardButton("😐 Okay"),       KeyboardButton("😔 Not Good")],
        [KeyboardButton("😷 Sick"),       KeyboardButton("😴 Tired")],
        [KeyboardButton("😤 Stressed"),   KeyboardButton("😠 Frustrated")],
        [KeyboardButton("😰 Anxious"),    KeyboardButton("🤩 Energetic")],
        [KeyboardButton("🥱 Bored"),      KeyboardButton("😌 Peaceful")],
        [KeyboardButton("🤒 Fever/Cold"), KeyboardButton("💪 Active")],
        [KeyboardButton("✍️ Other (type below)")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ── Explicit map: button → clean sheet value ──────────────
DAY_OPTIONS_MAP = {
    "😊 Great":      "Great",
    "🙂 Good":       "Good",
    "😐 Okay":       "Okay",
    "😔 Not Good":   "Not Good",
    "😷 Sick":       "Sick",
    "😴 Tired":      "Tired",
    "😤 Stressed":   "Stressed",
    "😠 Frustrated": "Frustrated",
    "😰 Anxious":    "Anxious",
    "🤩 Energetic":  "Energetic",
    "🥱 Bored":      "Bored",
    "😌 Peaceful":   "Peaceful",
    "🤒 Fever/Cold": "Fever/Cold",
    "💪 Active":     "Active",
}

# ── Helper ────────────────────────────────────────────────
def is_before_1pm() -> bool:
    return datetime.now().hour < 13

# ── Save to sheet & send summary ─────────────────────────
async def finish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    payload = {
        "date":          now.strftime("%d/%m/%Y"),
        "time":          now.strftime("%I:%M %p"),
        "bp_upper":      ctx.user_data.get("bp_upper", "-"),
        "bp_lower":      ctx.user_data.get("bp_lower", "-"),
        "morning_med":   ctx.user_data.get("morning_med", "-"),
        "afternoon_med": ctx.user_data.get("afternoon_med", "-"),
        "nose_bleed":    ctx.user_data.get("nose_bleed", "-"),
        "day_summary":   ctx.user_data.get("day_summary", "-"),
    }

    logging.info(f"📤 Final payload: {payload}")

    try:
        resp = requests.post(SHEET_URL, json=payload, timeout=15, allow_redirects=True)
        logging.info(f"📊 Sheet response: {resp.text}")
        saved = "✅ Your report has been saved!"
    except Exception as ex:
        logging.error(f"❌ Sheet error: {ex}")
        saved = "⚠️ Could not save. Please try again."

    # BP warning
    bp_warn = ""
    try:
        upper = int(payload["bp_upper"])
        lower = int(payload["bp_lower"])
        if upper > 140 or lower > 90:
            bp_warn = "\n⚠️ *BP is high! Please consult your doctor.*"
        elif upper < 90 or lower < 60:
            bp_warn = "\n⚠️ *BP is low! Please take rest.*"
        else:
            bp_warn = "\n✅ *BP is normal! Well done!*"
    except Exception:
        pass

    # Medicine warning
    med_warn = ""
    if payload.get("morning_med") == "No" or payload.get("afternoon_med") == "No":
        med_warn = "\n💊 *Reminder: Please don't miss your medicines!*"

    # Afternoon display
    afternoon_display = payload["afternoon_med"]
    if "before 1 PM" in afternoon_display:
        afternoon_display = "Not yet ⏰"

    summary = (
        f"🎉 *Health Check Complete!*\n\n"
        f"📅 Date: {payload['date']}\n"
        f"🕐 Time: {payload['time']}\n\n"
        f"💉 BP: *{payload['bp_upper']}/{payload['bp_lower']}*{bp_warn}\n"
        f"🌅 Morning Medicine: *{payload['morning_med']}*\n"
        f"🌤️ Afternoon Medicine: *{afternoon_display}*{med_warn}\n"
        f"🩸 Nose Bleeding: *{payload['nose_bleed']}*\n"
        f"😊 How was your day: *{payload['day_summary']}*\n\n"
        f"{saved}\n\n"
        f"Take care Papa! 💙🙏"
    )

    await update.message.reply_text(
        summary,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── /start ────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.bot_data["father_chat_id"] = update.effective_chat.id
    await update.message.reply_text(
        "👋 Hello Papa!\n\n"
        "I am your *Daily Health Bot* 🤖\n\n"
        "I will remind you every day:\n"
        "🌅 *11:00 AM* — Morning health check\n"
        "🌆 *7:00 PM*  — Evening check-in\n\n"
        "Commands:\n"
        "👉 /health — Start health check\n"
        "👉 /cancel — Cancel anytime\n\n"
        "Stay healthy, stay happy! 💙",
        parse_mode="Markdown"
    )

# ── /health ───────────────────────────────────────────────
async def health_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.bot_data["father_chat_id"] = update.effective_chat.id
    ctx.user_data.clear()
    await update.message.reply_text(
        "🩺 *Daily Health Check Started!*\n\n"
        "What is your BP upper number?\n\nExample: *130*",
        parse_mode="Markdown"
    )
    return BP_UPPER

# ── BP Upper ──────────────────────────────────────────────
async def get_bp_upper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    text = text.translate(str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789"))

    if not text.isdigit():
        await update.message.reply_text(
            "⚠️ Please enter numbers only!\n\nExample: *130*",
            parse_mode="Markdown"
        )
        return BP_UPPER

    ctx.user_data["bp_upper"] = text
    await update.message.reply_text(
        f"👍 BP Upper: *{text}* — noted!\n\n"
        "Now what is your BP lower number?\n\nExample: *80*",
        parse_mode="Markdown"
    )
    return BP_LOWER

# ── BP Lower ──────────────────────────────────────────────
async def get_bp_lower(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    text = text.translate(str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789"))

    if not text.isdigit():
        await update.message.reply_text(
            "⚠️ Please enter numbers only!\n\nExample: *80*",
            parse_mode="Markdown"
        )
        return BP_LOWER

    ctx.user_data["bp_lower"] = text
    await update.message.reply_text(
        f"👍 BP Lower: *{text}* — noted!\n\n"
        "💊 Did you take your *morning medicine?*",
        parse_mode="Markdown",
        reply_markup=YES_NO_KEYBOARD
    )
    return MORNING_MED

# ── Morning Medicine ──────────────────────────────────────
async def get_morning_med(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if "yes" in text:
        ctx.user_data["morning_med"] = "Yes"
    elif "no" in text:
        ctx.user_data["morning_med"] = "No"
    else:
        await update.message.reply_text(
            "⚠️ Please tap *Yes* or *No* button 👆",
            parse_mode="Markdown",
            reply_markup=YES_NO_KEYBOARD
        )
        return MORNING_MED

    # ── KEY FIX: skip afternoon properly ─────────────────
    if is_before_1pm():
        ctx.user_data["afternoon_med"] = "Not yet (before 1 PM)"
        await update.message.reply_text(
            "⏰ *It's before 1 PM* — afternoon medicine time hasn't come yet!\n\n"
            "🩸 Did *nose bleeding* happen today?",
            parse_mode="Markdown",
            reply_markup=YES_NO_KEYBOARD
        )
        return NOSE_BLEED   # ← goes directly to NOSE_BLEED, skipping AFTERNOON_MED
    else:
        await update.message.reply_text(
            "💊 Did you take your *afternoon medicine?*",
            parse_mode="Markdown",
            reply_markup=YES_NO_KEYBOARD
        )
        return AFTERNOON_MED

# ── Afternoon Medicine ────────────────────────────────────
async def get_afternoon_med(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if "yes" in text:
        ctx.user_data["afternoon_med"] = "Yes"
    elif "no" in text:
        ctx.user_data["afternoon_med"] = "No"
    else:
        await update.message.reply_text(
            "⚠️ Please tap *Yes* or *No* button 👆",
            parse_mode="Markdown",
            reply_markup=YES_NO_KEYBOARD
        )
        return AFTERNOON_MED

    await update.message.reply_text(
        "🩸 Did *nose bleeding* happen today?",
        parse_mode="Markdown",
        reply_markup=YES_NO_KEYBOARD
    )
    return NOSE_BLEED

# ── Nose Bleed ────────────────────────────────────────────
async def get_nose_bleed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if "yes" in text:
        ctx.user_data["nose_bleed"] = "Yes"
    elif "no" in text:
        ctx.user_data["nose_bleed"] = "No"
    else:
        await update.message.reply_text(
            "⚠️ Please tap *Yes* or *No* button 👆",
            parse_mode="Markdown",
            reply_markup=YES_NO_KEYBOARD
        )
        return NOSE_BLEED

    await update.message.reply_text(
        "😊 *How was your day today?*\n\n"
        "Please select from the options below 👇\n"
        "_(Or tap Other to type your own!)_",
        parse_mode="Markdown",
        reply_markup=DAY_KEYBOARD
    )
    return DAY_SUMMARY   # ← always goes to DAY_SUMMARY next, whether skipped or not

# ── Day Summary ───────────────────────────────────────────
async def get_day_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "Other" in text:
        await update.message.reply_text(
            "✍️ Please type how you are feeling today:",
            reply_markup=ReplyKeyboardRemove()
        )
        return OTHER_TEXT   # ← separate clean state for free text

    # Look up clean value from map
    ctx.user_data["day_summary"] = DAY_OPTIONS_MAP.get(text, text)
    logging.info(f"✅ day_summary = '{ctx.user_data['day_summary']}'")
    return await finish(update, ctx)

# ── Other Free Text ───────────────────────────────────────
async def get_other_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["day_summary"] = update.message.text.strip()
    logging.info(f"✅ day_summary (other) = '{ctx.user_data['day_summary']}'")
    return await finish(update, ctx)

# ── /cancel ───────────────────────────────────────────────
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Health check cancelled.\nType /health anytime to start again! 🙏",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── Voice Note ────────────────────────────────────────────
async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎤 Voice note received Papa!\n\n"
        "Please type /health and use the buttons 👆\n"
        "Only 5 steps, very easy! 😊"
    )

# ── Morning Reminder — 11:00 AM IST ──────────────────────
async def send_morning_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.bot_data.get("father_chat_id")
    if chat_id:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                "🌅 *Good Morning Papa!* 🙏\n\n"
                "Time for your morning health check!\n\n"
                "👉 Type */health* to start\n\n"
                "Have a healthy and happy day! 💙"
            ),
            parse_mode="Markdown"
        )

# ── Evening Reminder — 7:00 PM IST ───────────────────────
async def send_evening_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.bot_data.get("father_chat_id")
    if chat_id:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                "🌆 *Good Evening Papa!* 🙏\n\n"
                "How are you feeling today?\n"
                "Did you fill your health report?\n\n"
                "👉 Type */health* to fill it now\n\n"
                "Take rest and stay well! 💙"
            ),
            parse_mode="Markdown"
        )

# ── Main ──────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("health", health_start)],
        states={
            BP_UPPER:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bp_upper)],
            BP_LOWER:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bp_lower)],
            MORNING_MED:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_morning_med)],
            AFTERNOON_MED: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_afternoon_med)],
            NOSE_BLEED:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nose_bleed)],
            DAY_SUMMARY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_day_summary)],
            OTHER_TEXT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_other_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # 🌅 Morning reminder — 11:00 AM IST (05:30 UTC)
    app.job_queue.run_daily(
        send_morning_reminder,
        time=time(hour=5, minute=30, second=0)
    )

    # 🌆 Evening reminder — 7:00 PM IST (13:30 UTC)
    app.job_queue.run_daily(
        send_evening_reminder,
        time=time(hour=13, minute=30, second=0)
    )

    print("🤖 Anna Health Bot is running!")
    print("⏰ Morning reminder: 11:00 AM IST")
    print("⏰ Evening reminder:  7:00 PM IST")
    print("Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
