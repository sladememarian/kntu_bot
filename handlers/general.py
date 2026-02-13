# ==========================================
# KNTU Bot 25 — General Commands (start, help, lang, debug)
# ==========================================

import json
from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from storage import get_lang, set_lang, get_debug, set_debug, load_data, _use_pg, save_data
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


async def dbstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: show database backend status."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    import os
    db_url = os.environ.get("DATABASE_URL", "")
    data = load_data()
    keys_count = len(data)
    wallets = len(data.get("wallets", {}).get(str(update.effective_chat.id), {}))
    inv_count = sum(
        len(items) for items in data.get("inventory", {}).get(str(update.effective_chat.id), {}).values()
    )

    if _use_pg:
        backend = "✅ PostgreSQL (persistent)"
    elif db_url:
        backend = "⚠️ DATABASE_URL set but PG connection failed — using JSON"
    else:
        backend = "❌ JSON file (NOT persistent — data resets on deploy!)"

    text = (
        f"🗄 *Database Status*\n\n"
        f"Backend: {backend}\n"
        f"Data keys: `{keys_count}`\n"
        f"Wallets in this chat: `{wallets}`\n"
        f"Inventory items: `{inv_count}`\n"
        f"DATABASE\\_URL: {'`set`' if db_url else '`NOT SET`'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def syncdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: force sync current data to PostgreSQL (or save to file)."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    data = load_data()
    save_data(data)
    backend = "PostgreSQL" if _use_pg else "JSON file"
    await update.message.reply_text(f"✅ Data synced to {backend}! ({len(data)} keys)")


async def loaddata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: upload a data.json file and overwrite the database with it."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    reply = update.message.reply_to_message
    doc = None
    if reply and reply.document:
        doc = reply.document
    elif update.message.document:
        doc = update.message.document

    if not doc:
        await update.message.reply_text(
            "📥 Send or reply to a `.json` file, then use /loaddata",
            parse_mode="Markdown",
        )
        return

    try:
        file = await context.bot.get_file(doc.file_id)
        bio = __import__("io").BytesIO()
        await file.download_to_memory(bio)
        bio.seek(0)
        new_data = json.loads(bio.read().decode("utf-8"))
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to parse file: {e}")
        return

    save_data(new_data)
    backend = "PostgreSQL" if _use_pg else "JSON file"
    wallets = len(new_data.get("wallets", {}).get(str(update.effective_chat.id), {}))
    await update.message.reply_text(
        f"✅ Data loaded into {backend}!\n"
        f"Keys: `{len(new_data)}` | Wallets: `{wallets}`",
        parse_mode="Markdown",
    )
