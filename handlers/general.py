# ==========================================
# KNTU Bot 25 — General Commands (start, help, lang, debug)
# ==========================================

import json
from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from storage import get_lang, set_lang, get_debug, set_debug, load_data
from strings import STRINGS


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    await update.message.reply_text(s["bot_start"], parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    await update.message.reply_text(s["help"], parse_mode="Markdown")


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    current = get_lang(chat.id)
    new_lang = "en" if current == "fa" else "fa"
    set_lang(chat.id, new_lang)
    s = STRINGS[new_lang]
    label = "English 🇬🇧" if new_lang == "en" else "فارسی 🇮🇷"
    await update.message.reply_text(
        s["lang_changed"].format(lang=label), parse_mode="Markdown"
    )


async def debug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text(s["debug_not_admin"], parse_mode="Markdown")
        return

    current = get_debug()
    set_debug(not current)
    msg = s["debug_on"] if not current else s["debug_off"]
    await update.message.reply_text(msg, parse_mode="Markdown")


async def dumpdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: send current data.json as a file via Telegram."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    data = load_data()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    bio = __import__("io").BytesIO(text.encode("utf-8"))
    bio.name = "data.json"
    await update.message.reply_document(document=bio, caption="📦 Live data.json backup")
