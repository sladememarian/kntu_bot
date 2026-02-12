# ==========================================
# KNTU Bot 25 — News Forwarding from Channels
# ==========================================

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, get_news_channels, add_news_channel, remove_news_channel
from strings import STRINGS
from config import ADMIN_IDS


# --------- /news ---------
async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    channels = get_news_channels(chat.id)
    if not channels:
        await update.message.reply_text(s["news_no_channels"], parse_mode="Markdown")
        return

    await update.message.reply_text(s["news_fetching"], parse_mode="Markdown")

    collected = []
    for ch_username in channels[:5]:  # limit to 5 channels
        try:
            # Forward the last 3 messages from each channel
            ch_username_clean = ch_username.lstrip("@")
            chat_obj = await context.bot.get_chat(f"@{ch_username_clean}")
            # We can't read channel history directly via Bot API without being admin.
            # Instead, we inform user to use the channel forwarding approach.
            collected.append(f"📡 @{ch_username_clean} — [مشاهده/View](https://t.me/{ch_username_clean})")
        except Exception as e:
            collected.append(f"❌ @{ch_username.lstrip('@')} — Error: {str(e)[:50]}")

    header = s["news_header"]
    body = "\n\n".join(collected)
    await update.message.reply_text(
        header + body,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# --------- /setnews ---------
async def setnews_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if not context.args:
        await update.message.reply_text(s["news_set_usage"], parse_mode="Markdown")
        return

    channel = context.args[0].lstrip("@").strip()
    add_news_channel(chat.id, channel)
    await update.message.reply_text(
        s["news_set_ok"].format(ch=channel), parse_mode="Markdown"
    )


# --------- /removenews ---------
async def removenews_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if not context.args:
        await update.message.reply_text(s["news_set_usage"], parse_mode="Markdown")
        return

    channel = context.args[0].lstrip("@").strip()
    remove_news_channel(chat.id, channel)
    await update.message.reply_text(
        s["news_removed"].format(ch=channel), parse_mode="Markdown"
    )
