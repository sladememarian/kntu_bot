# ==========================================
# KNTU Bot 25 — Welcome / Greet New Members
# ==========================================

from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes

from storage import get_lang, track_member
from strings import STRINGS


async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the group via ChatMemberUpdated."""
    result = _extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    if not was_member and is_member:
        user = update.chat_member.new_chat_member.user
        chat = update.effective_chat
        lang = get_lang(chat.id)
        s = STRINGS[lang]
        name = user.first_name or "User"
        track_member(chat.id, user.id)
        await context.bot.send_message(
            chat_id=chat.id,
            text=s["welcome_group"].format(name=name),
            parse_mode="Markdown",
        )


async def greet_via_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback: greet via new_chat_members in Message."""
    if not update.message or not update.message.new_chat_members:
        return

    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "User"
        track_member(chat.id, member.id)
        await update.message.reply_text(
            s["welcome_group"].format(name=name),
            parse_mode="Markdown",
        )


def _extract_status_change(chat_member_update: ChatMemberUpdated):
    """Extract whether a user joined or left."""
    if chat_member_update is None:
        return None
    status_change = chat_member_update.difference().get("status")
    if status_change is None:
        return None
    old_status, new_status = status_change
    was_member = old_status in ("member", "administrator", "creator")
    is_member = new_status in ("member", "administrator", "creator")
    return was_member, is_member


async def track_message_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track users who send messages so /ship can pick from them."""
    if update.effective_user and update.effective_chat:
        track_member(update.effective_chat.id, update.effective_user.id)
