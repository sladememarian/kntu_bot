# ==========================================
# KNTU Bot 25 — Random Drop System
# Cash bags drop every 80-150 messages
# ==========================================

import random
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_lang, add_balance, set_user_name

# In-memory — resets on restart (acceptable)
_counters: dict[int, int] = {}
_thresholds: dict[int, int] = {}
_active_drops: dict[int, dict] = {}

_DROP_MIN = 80
_DROP_MAX = 150
_DROP_EXPIRE = 60  # seconds


def _next_threshold(chat_id: int) -> int:
    t = random.randint(_DROP_MIN, _DROP_MAX)
    _thresholds[chat_id] = t
    return t


async def drop_counter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MessageHandler — counts messages, occasionally drops a cash bag."""
    if not update.effective_chat or not update.message:
        return
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    text = update.message.text or ""
    if not text or text.startswith("/"):
        return

    cid = update.effective_chat.id
    _counters[cid] = _counters.get(cid, 0) + 1
    threshold = _thresholds.get(cid) or _next_threshold(cid)

    if _counters[cid] < threshold:
        return

    # Reset
    _counters[cid] = 0
    _next_threshold(cid)

    # Don't overlap active drops
    if cid in _active_drops:
        if time.time() - _active_drops[cid]["time"] < _DROP_EXPIRE:
            return
        del _active_drops[cid]

    lang = get_lang(cid)
    is_big = random.random() < 0.15
    value = random.randint(300, 900) if is_big else random.randint(50, 250)

    _active_drops[cid] = {"value": value, "time": time.time()}

    if lang == "fa":
        text = (
            f"🎁 *یه کیسه پول از آسمون افتاد!*\n\n"
            f"💰 مبلغ: *{value:,}$*\n"
            f"⏰ *{_DROP_EXPIRE} ثانیه* وقت داری!\n\n"
            f"_اولین نفری که بزنه میبره!_"
        )
        btn = "🎯 بقاپ!"
    else:
        text = (
            f"🎁 *A cash bag dropped from the sky!*\n\n"
            f"💰 Amount: *{value:,}$*\n"
            f"⏰ *{_DROP_EXPIRE} seconds* to grab!\n\n"
            f"_First click wins!_"
        )
        btn = "🎯 Grab!"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn, callback_data=f"grab:{cid}")]
    ])
    await context.bot.send_message(
        chat_id=cid, text=text, parse_mode="Markdown", reply_markup=keyboard,
    )


async def grab_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CallbackQueryHandler for grab:{chat_id}."""
    query = update.callback_query
    user = query.from_user
    chat = update.effective_chat
    lang = get_lang(chat.id)

    parts = query.data.split(":")
    if len(parts) != 2:
        return
    target_chat = int(parts[1])
    if target_chat != chat.id:
        await query.answer("❌", show_alert=False)
        return

    drop = _active_drops.pop(chat.id, None)
    if not drop:
        await query.answer(
            "❌ دیر رسیدی!" if lang == "fa" else "❌ Too late!", show_alert=True)
        try:
            await query.edit_message_text(
                "💨 قبلاً قاپیده شد!" if lang == "fa" else "💨 Already grabbed!")
        except Exception:
            pass
        return

    if time.time() - drop["time"] > _DROP_EXPIRE:
        await query.answer(
            "❌ وقتش تمام شد!" if lang == "fa" else "❌ Expired!", show_alert=True)
        try:
            await query.edit_message_text(
                "⏰ وقتش تمام شد!" if lang == "fa" else "⏰ Expired!")
        except Exception:
            pass
        return

    value = drop["value"]
    new_bal = add_balance(chat.id, user.id, value)
    set_user_name(chat.id, user.id, user.first_name or "User")
    await query.answer(f"🎉 +{value}$!", show_alert=False)

    if lang == "fa":
        await query.edit_message_text(
            f"🎉 *{user.first_name}* کیسه رو قاپید!\n\n"
            f"💰 دریافتی: *{value:,}$*\n"
            f"💳 موجودی: *{new_bal:,}$*",
            parse_mode="Markdown")
    else:
        await query.edit_message_text(
            f"🎉 *{user.first_name}* grabbed the bag!\n\n"
            f"💰 Earned: *{value:,}$*\n"
            f"💳 Balance: *{new_bal:,}$*",
            parse_mode="Markdown")
