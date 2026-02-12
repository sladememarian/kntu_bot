# ==========================================
# KNTU Bot 25 — Fun Features: Ship, Lagab, Rizz, Gay rate
# ==========================================

import random
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from storage import get_lang, get_lagabs, set_lagab, get_members, add_warn, get_warns, reset_warns
from strings import STRINGS


def _get_s(chat_id: int):
    return STRINGS[get_lang(chat_id)]


def _bar(percent: int) -> str:
    filled = round(percent / 10)
    return "█" * filled + "░" * (10 - filled)


def _rate_comment(percent: int, lang: str) -> str:
    s = STRINGS[lang]
    if percent < 35:
        return random.choice(s["rate_comments_low"])
    elif percent < 70:
        return random.choice(s["rate_comments_mid"])
    else:
        return random.choice(s["rate_comments_high"])


# --------- /ship ---------
async def ship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    s = _get_s(chat.id)
    members = get_members(chat.id)

    if len(members) < 2:
        await update.message.reply_text(s["ship_need_members"])
        return

    pair = random.sample(members, 2)
    try:
        m1 = await context.bot.get_chat_member(chat.id, pair[0])
        m2 = await context.bot.get_chat_member(chat.id, pair[1])
        name1 = m1.user.first_name or "User1"
        name2 = m2.user.first_name or "User2"
    except Exception:
        name1, name2 = f"User {pair[0]}", f"User {pair[1]}"

    percent = random.randint(0, 100)
    hearts_count = round(percent / 10)
    hearts = "❤️" * hearts_count + "🖤" * (10 - hearts_count)

    text = s["ship_result"].format(user1=name1, user2=name2, percent=percent, hearts=hearts)
    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /lagab ---------
async def lagab_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    s = _get_s(chat.id)

    # If no arguments and no reply → show list
    if not context.args and not update.message.reply_to_message:
        lagabs = get_lagabs(chat.id)
        if not lagabs:
            await update.message.reply_text(s["lagab_empty"])
            return
        items = ""
        for uid, nick in lagabs.items():
            try:
                member = await context.bot.get_chat_member(chat.id, int(uid))
                name = member.user.first_name
            except Exception:
                name = f"User {uid}"
            items += f"• {name}: *{nick}*\n"
        await update.message.reply_text(
            s["lagab_list"].format(items=items), parse_mode="Markdown"
        )
        return

    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text(s["lagab_usage"], parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    lagab_text = " ".join(context.args)
    set_lagab(chat.id, target.id, lagab_text)
    name = target.first_name or "User"
    await update.message.reply_text(
        s["lagab_set"].format(user=name, lagab=lagab_text), parse_mode="Markdown"
    )


# --------- /rizz ---------
async def rizz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    percent = random.randint(0, 100)
    bar = _bar(percent)
    comment = _rate_comment(percent, lang)
    name = user.first_name or "User"

    await update.message.reply_text(
        s["rizz_result"].format(user=name, percent=percent, bar=bar, comment=comment),
        parse_mode="Markdown",
    )


# --------- /gay ---------
async def gay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    percent = random.randint(0, 100)
    bar = _bar(percent)
    comment = _rate_comment(percent, lang)
    name = user.first_name or "User"

    await update.message.reply_text(
        s["gay_result"].format(user=name, percent=percent, bar=bar, comment=comment),
        parse_mode="Markdown",
    )


# --------- اخطار (warn via keyword) ---------
async def warn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when an admin replies to a message with 'اخطار'."""
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    message = update.message

    if not message or not message.text:
        return

    text = message.text.strip()
    if text not in ("اخطار",):
        return

    # Must be a reply
    if not message.reply_to_message:
        await message.reply_text(s["warn_usage"], parse_mode="Markdown")
        return

    # Check if sender is admin
    sender = await context.bot.get_chat_member(chat.id, update.effective_user.id)
    if sender.status not in ("administrator", "creator"):
        await message.reply_text(s["warn_not_admin"], parse_mode="Markdown")
        return

    target = message.reply_to_message.from_user
    if target.is_bot:
        return

    name = target.first_name or "User"
    count = add_warn(chat.id, target.id)

    if count >= 3:
        # Kick user after 3 warns
        try:
            await context.bot.ban_chat_member(chat.id, target.id)
            await context.bot.unban_chat_member(chat.id, target.id)  # unban so they can rejoin
            reset_warns(chat.id, target.id)
            await message.reply_text(s["warn_kick"].format(user=name), parse_mode="Markdown")
        except Exception:
            await message.reply_text(
                s["warn_given"].format(user=name, count=count), parse_mode="Markdown"
            )
    else:
        await message.reply_text(
            s["warn_given"].format(user=name, count=count), parse_mode="Markdown"
        )


# --------- /resetwarn ---------
async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin replies to a user's message with /resetwarn to clear their warns."""
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    sender = await context.bot.get_chat_member(chat.id, update.effective_user.id)
    if sender.status not in ("administrator", "creator"):
        await update.message.reply_text(s["warn_not_admin"], parse_mode="Markdown")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(s["warn_usage"], parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    name = target.first_name or "User"
    reset_warns(chat.id, target.id)
    await update.message.reply_text(
        s["warn_reset"].format(user=name), parse_mode="Markdown"
    )
