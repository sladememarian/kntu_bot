# ==========================================
# KNTU Bot 25 — AI Chat (Google Gemini)
# ==========================================

from telegram import Update
from telegram.ext import ContextTypes
from google import genai

from config import GEMINI_API_KEY
from storage import get_lang
from strings import STRINGS

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_PROMPT = (
    "You are kntu_bot25, a fun and helpful Telegram group bot. "
    "You can answer in both Persian (Farsi) and English. "
    "Keep answers concise and group-friendly. "
    "If the user writes in Persian, reply in Persian. "
    "If the user writes in English, reply in English."
)


async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if not context.args:
        await update.message.reply_text(s["ai_usage"], parse_mode="Markdown")
        return

    if not client:
        await update.message.reply_text(s["ai_error"], parse_mode="Markdown")
        return

    question = " ".join(context.args)
    thinking_msg = await update.message.reply_text(s["ai_thinking"], parse_mode="Markdown")

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{SYSTEM_PROMPT}\n\nUser: {question}",
        )
        answer = response.text.strip()
        await thinking_msg.edit_text(f"🧠 {answer}")
    except Exception as e:
        error_text = s["ai_error"]
        from storage import get_debug
        if get_debug():
            error_text += f"\n\nDebug: `{str(e)[:200]}`"
        await thinking_msg.edit_text(error_text, parse_mode="Markdown")
