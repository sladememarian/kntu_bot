# ==========================================
# KNTU Bot 25 — Clan/Gang System
# Create, join, manage clans, war for loot
# ==========================================

import random

from telegram import Update
from telegram.ext import ContextTypes

from storage import (
    get_lang, get_balance, add_balance,
    get_all_clans, get_clan, save_clan, delete_clan,
    get_user_clan, set_user_clan, get_user_name, set_user_name,
)

CLAN_CREATE_COST = 5000
CLAN_MAX_MEMBERS = 10
WAR_COOLDOWN = {}  # {chat_id: {clan_name: last_war_time}} — in-memory


async def clan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    args = context.args or []

    if not args:
        if lang == "fa":
            text = (
                "⚔️ *سیستم کلن*\n\n"
                "📝 /clan create <نام> — ساخت کلن (5,000$)\n"
                "🤝 /clan join — عضویت (ریپلای به عضو کلن)\n"
                "🚪 /clan leave — خروج از کلن\n"
                "📊 /clan info — اطلاعات کلن\n"
                "👥 /clan members — لیست اعضا\n"
                "💰 /clan deposit <مبلغ> — واریز به صندوق\n"
                "💸 /clan withdraw <مبلغ> — برداشت (رهبر)\n"
                "⚔️ /clan war — جنگ کلن (ریپلای به دشمن)\n"
                "📋 /clan list — لیست کل کلن‌ها"
            )
        else:
            text = (
                "⚔️ *Clan System*\n\n"
                "📝 /clan create <name> — Create clan (5,000$)\n"
                "🤝 /clan join — Join (reply to member)\n"
                "🚪 /clan leave — Leave your clan\n"
                "📊 /clan info — Clan info\n"
                "👥 /clan members — List members\n"
                "💰 /clan deposit <amount> — Deposit to bank\n"
                "💸 /clan withdraw <amount> — Withdraw (leader)\n"
                "⚔️ /clan war — Clan war (reply to enemy)\n"
                "📋 /clan list — List all clans"
            )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    sub = args[0].lower()
    handlers = {
        "create": _clan_create, "join": _clan_join, "leave": _clan_leave,
        "info": _clan_info, "members": _clan_members, "deposit": _clan_deposit,
        "withdraw": _clan_withdraw, "war": _clan_war, "list": _clan_list,
    }
    handler = handlers.get(sub)
    if handler:
        await handler(update, context, args[1:], lang)
    else:
        msg = "❌ زیرفرمان نامعتبر! /clan بنویس." if lang == "fa" else "❌ Invalid subcommand! Type /clan."
        await update.message.reply_text(msg)


async def _clan_create(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        msg = "📝 /clan create <نام کلن>" if lang == "fa" else "📝 /clan create <clan name>"
        await update.message.reply_text(msg)
        return

    if get_user_clan(chat.id, user.id):
        msg = "❌ قبلاً عضو یه کلنی! اول /clan leave کن." if lang == "fa" else "❌ Already in a clan! /clan leave first."
        await update.message.reply_text(msg)
        return

    name = " ".join(args)[:20].strip()
    if not name:
        return

    if get_clan(chat.id, name):
        msg = "❌ این اسم گرفته شده!" if lang == "fa" else "❌ Name already taken!"
        await update.message.reply_text(msg)
        return

    bal = get_balance(chat.id, user.id)
    if bal < CLAN_CREATE_COST:
        msg = (f"❌ پول کافی نداری! نیاز: *{CLAN_CREATE_COST:,}$*" if lang == "fa"
               else f"❌ Need *{CLAN_CREATE_COST:,}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -CLAN_CREATE_COST)
    save_clan(chat.id, name, {
        "leader": user.id,
        "members": [user.id],
        "bank": 0,
        "wins": 0,
        "losses": 0,
    })
    set_user_clan(chat.id, user.id, name)
    set_user_name(chat.id, user.id, user.first_name or "User")

    if lang == "fa":
        await update.message.reply_text(
            f"⚔️ *کلن «{name}» ساخته شد!*\n💰 هزینه: *{CLAN_CREATE_COST:,}$*\n👑 رهبر: {user.first_name}",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"⚔️ *Clan \"{name}\" created!*\n💰 Cost: *{CLAN_CREATE_COST:,}$*\n👑 Leader: {user.first_name}",
            parse_mode="Markdown")


async def _clan_join(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    if get_user_clan(chat.id, user.id):
        msg = "❌ قبلاً عضو یه کلنی!" if lang == "fa" else "❌ Already in a clan!"
        await update.message.reply_text(msg)
        return

    if not update.message.reply_to_message:
        msg = "📝 به پیام عضو کلن ریپلای کن." if lang == "fa" else "📝 Reply to a clan member."
        await update.message.reply_text(msg)
        return

    target = update.message.reply_to_message.from_user
    target_clan = get_user_clan(chat.id, target.id)
    if not target_clan:
        msg = "❌ این کاربر عضو کلنی نیست!" if lang == "fa" else "❌ This user isn't in a clan!"
        await update.message.reply_text(msg)
        return

    clan_data = get_clan(chat.id, target_clan)
    if not clan_data:
        return

    if len(clan_data.get("members", [])) >= CLAN_MAX_MEMBERS:
        msg = f"❌ کلن پره! حداکثر {CLAN_MAX_MEMBERS} نفر." if lang == "fa" else f"❌ Clan full! Max {CLAN_MAX_MEMBERS}."
        await update.message.reply_text(msg)
        return

    clan_data["members"].append(user.id)
    save_clan(chat.id, target_clan, clan_data)
    set_user_clan(chat.id, user.id, target_clan)
    set_user_name(chat.id, user.id, user.first_name or "User")

    if lang == "fa":
        await update.message.reply_text(
            f"🤝 *{user.first_name}* عضو کلن «{target_clan}» شد! ⚔️",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"🤝 *{user.first_name}* joined clan \"{target_clan}\"! ⚔️",
            parse_mode="Markdown")


async def _clan_leave(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    clan_name = get_user_clan(chat.id, user.id)
    if not clan_name:
        msg = "❌ عضو کلنی نیستی!" if lang == "fa" else "❌ Not in any clan!"
        await update.message.reply_text(msg)
        return

    clan_data = get_clan(chat.id, clan_name)
    if not clan_data:
        set_user_clan(chat.id, user.id, None)
        return

    if clan_data["leader"] == user.id:
        for mid in clan_data.get("members", []):
            set_user_clan(chat.id, mid, None)
        bank = clan_data.get("bank", 0)
        if bank > 0:
            add_balance(chat.id, user.id, bank)
        delete_clan(chat.id, clan_name)
        if lang == "fa":
            await update.message.reply_text(
                f"💥 کلن «{clan_name}» منحل شد!\n💰 صندوق *{bank:,}$* برگشت داده شد.",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"💥 Clan \"{clan_name}\" disbanded!\n💰 Bank *{bank:,}$* returned.",
                parse_mode="Markdown")
    else:
        clan_data["members"] = [m for m in clan_data["members"] if m != user.id]
        save_clan(chat.id, clan_name, clan_data)
        set_user_clan(chat.id, user.id, None)
        msg = f"🚪 از کلن «{clan_name}» خارج شدی." if lang == "fa" else f"🚪 Left clan \"{clan_name}\"."
        await update.message.reply_text(msg)


async def _clan_info(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    clan_name = get_user_clan(chat.id, user.id)
    if not clan_name:
        msg = "❌ عضو کلنی نیستی! /clan list رو ببین." if lang == "fa" else "❌ Not in a clan! See /clan list."
        await update.message.reply_text(msg)
        return

    clan = get_clan(chat.id, clan_name)
    if not clan:
        return

    leader_name = get_user_name(chat.id, clan["leader"]) or f"User {clan['leader']}"
    members = len(clan.get("members", []))
    bank = clan.get("bank", 0)
    wins = clan.get("wins", 0)
    losses = clan.get("losses", 0)
    wr = int(wins / max(wins + losses, 1) * 100)

    if lang == "fa":
        text = (
            f"⚔️ *کلن «{clan_name}»*\n{'═' * 24}\n\n"
            f"👑 رهبر: *{leader_name}*\n"
            f"👥 اعضا: *{members}/{CLAN_MAX_MEMBERS}*\n"
            f"💰 صندوق: *{bank:,}$*\n"
            f"🏆 برد: *{wins}* | 💀 باخت: *{losses}* | 📊 نرخ: *{wr}%*\n"
        )
    else:
        text = (
            f"⚔️ *Clan \"{clan_name}\"*\n{'═' * 24}\n\n"
            f"👑 Leader: *{leader_name}*\n"
            f"👥 Members: *{members}/{CLAN_MAX_MEMBERS}*\n"
            f"💰 Bank: *{bank:,}$*\n"
            f"🏆 Wins: *{wins}* | 💀 Losses: *{losses}* | 📊 WR: *{wr}%*\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def _clan_members(update, context, args, lang):
    chat = update.effective_chat
    clan_name = get_user_clan(chat.id, update.effective_user.id)
    if not clan_name:
        msg = "❌ عضو کلنی نیستی!" if lang == "fa" else "❌ Not in a clan!"
        await update.message.reply_text(msg)
        return

    clan = get_clan(chat.id, clan_name)
    if not clan:
        return

    lines = []
    for i, mid in enumerate(clan.get("members", [])):
        name = get_user_name(chat.id, mid) or f"User {mid}"
        prefix = "👑" if mid == clan["leader"] else f"*{i + 1}.*"
        lines.append(f"{prefix} {name}")

    header = (f"👥 *اعضای «{clan_name}»*\n{'═' * 24}\n\n" if lang == "fa"
              else f"👥 *Members of \"{clan_name}\"*\n{'═' * 24}\n\n")
    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")


async def _clan_deposit(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    clan_name = get_user_clan(chat.id, user.id)
    if not clan_name:
        msg = "❌ عضو کلنی نیستی!" if lang == "fa" else "❌ Not in a clan!"
        await update.message.reply_text(msg)
        return

    if not args or not args[0].isdigit():
        msg = "📝 /clan deposit <مبلغ>" if lang == "fa" else "📝 /clan deposit <amount>"
        await update.message.reply_text(msg)
        return

    amount = int(args[0])
    if amount <= 0:
        return

    bal = get_balance(chat.id, user.id)
    if bal < amount:
        msg = f"❌ پول کافی نداری! موجودی: *{bal:,}$*" if lang == "fa" else f"❌ Not enough! Balance: *{bal:,}$*"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    clan = get_clan(chat.id, clan_name)
    if not clan:
        return

    add_balance(chat.id, user.id, -amount)
    clan["bank"] = clan.get("bank", 0) + amount
    save_clan(chat.id, clan_name, clan)

    if lang == "fa":
        await update.message.reply_text(
            f"💰 *{amount:,}$* واریز شد!\n🏦 صندوق کلن: *{clan['bank']:,}$*",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"💰 *{amount:,}$* deposited!\n🏦 Clan bank: *{clan['bank']:,}$*",
            parse_mode="Markdown")


async def _clan_withdraw(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    clan_name = get_user_clan(chat.id, user.id)
    if not clan_name:
        msg = "❌ عضو کلنی نیستی!" if lang == "fa" else "❌ Not in a clan!"
        await update.message.reply_text(msg)
        return

    clan = get_clan(chat.id, clan_name)
    if not clan:
        return

    if clan["leader"] != user.id:
        msg = "❌ فقط رهبر میتونه برداشت کنه!" if lang == "fa" else "❌ Only the leader can withdraw!"
        await update.message.reply_text(msg)
        return

    if not args or not args[0].isdigit():
        msg = "📝 /clan withdraw <مبلغ>" if lang == "fa" else "📝 /clan withdraw <amount>"
        await update.message.reply_text(msg)
        return

    amount = int(args[0])
    if amount <= 0:
        return

    if clan.get("bank", 0) < amount:
        msg = (f"❌ صندوق کافی نیست! صندوق: *{clan.get('bank', 0):,}$*" if lang == "fa"
               else f"❌ Not enough! Bank: *{clan.get('bank', 0):,}$*")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    clan["bank"] -= amount
    save_clan(chat.id, clan_name, clan)
    add_balance(chat.id, user.id, amount)

    if lang == "fa":
        await update.message.reply_text(
            f"💸 *{amount:,}$* برداشت شد!\n🏦 صندوق: *{clan['bank']:,}$*",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"💸 *{amount:,}$* withdrawn!\n🏦 Bank: *{clan['bank']:,}$*",
            parse_mode="Markdown")


async def _clan_war(update, context, args, lang):
    chat = update.effective_chat
    user = update.effective_user

    my_clan_name = get_user_clan(chat.id, user.id)
    if not my_clan_name:
        msg = "❌ عضو کلنی نیستی!" if lang == "fa" else "❌ Not in a clan!"
        await update.message.reply_text(msg)
        return

    if not update.message.reply_to_message:
        msg = "📝 به پیام عضو کلن دشمن ریپلای کن." if lang == "fa" else "📝 Reply to an enemy clan member."
        await update.message.reply_text(msg)
        return

    target = update.message.reply_to_message.from_user
    target_clan_name = get_user_clan(chat.id, target.id)
    if not target_clan_name:
        msg = "❌ این کاربر عضو کلنی نیست!" if lang == "fa" else "❌ This user isn't in a clan!"
        await update.message.reply_text(msg)
        return

    if my_clan_name == target_clan_name:
        msg = "❌ نمیتونی با کلن خودت بجنگی!" if lang == "fa" else "❌ Can't war your own clan!"
        await update.message.reply_text(msg)
        return

    my_clan = get_clan(chat.id, my_clan_name)
    enemy_clan = get_clan(chat.id, target_clan_name)
    if not my_clan or not enemy_clan:
        return

    # War power: members * 10 + wins * 3 + random 1-60
    my_power = len(my_clan["members"]) * 10 + my_clan.get("wins", 0) * 3 + random.randint(1, 60)
    enemy_power = len(enemy_clan["members"]) * 10 + enemy_clan.get("wins", 0) * 3 + random.randint(1, 60)
    loot = random.randint(200, 1000)

    if my_power >= enemy_power:
        my_clan["wins"] = my_clan.get("wins", 0) + 1
        enemy_clan["losses"] = enemy_clan.get("losses", 0) + 1
        my_clan["bank"] = my_clan.get("bank", 0) + loot
        winner, loser = my_clan_name, target_clan_name
    else:
        enemy_clan["wins"] = enemy_clan.get("wins", 0) + 1
        my_clan["losses"] = my_clan.get("losses", 0) + 1
        enemy_clan["bank"] = enemy_clan.get("bank", 0) + loot
        winner, loser = target_clan_name, my_clan_name

    save_clan(chat.id, my_clan_name, my_clan)
    save_clan(chat.id, target_clan_name, enemy_clan)

    if lang == "fa":
        await update.message.reply_text(
            f"⚔️ *جنگ کلن!*\n\n"
            f"«{my_clan_name}» (💪{my_power}) ⚔️ «{target_clan_name}» (💪{enemy_power})\n\n"
            f"🏆 *«{winner}» پیروز شد!*\n"
            f"💰 غنیمت: *{loot:,}$* → صندوق برنده\n"
            f"💀 «{loser}» باخت!",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"⚔️ *Clan War!*\n\n"
            f"\"{my_clan_name}\" (💪{my_power}) ⚔️ \"{target_clan_name}\" (💪{enemy_power})\n\n"
            f"🏆 *\"{winner}\" wins!*\n"
            f"💰 Loot: *{loot:,}$* → winner's bank\n"
            f"💀 \"{loser}\" lost!",
            parse_mode="Markdown")


async def _clan_list(update, context, args, lang):
    chat = update.effective_chat
    clans = get_all_clans(chat.id)

    if not clans:
        msg = "📋 هنوز کلنی ساخته نشده!" if lang == "fa" else "📋 No clans yet!"
        await update.message.reply_text(msg)
        return

    sorted_clans = sorted(clans.items(), key=lambda x: x[1].get("wins", 0), reverse=True)
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (cname, cdata) in enumerate(sorted_clans[:10]):
        prefix = medals[i] if i < 3 else f"*{i + 1}.*"
        members = len(cdata.get("members", []))
        wins = cdata.get("wins", 0)
        lines.append(f"{prefix} *{cname}* — 👥{members} | 🏆{wins}")

    header = (f"📋 *کلن‌های گروه*\n{'═' * 24}\n\n" if lang == "fa"
              else f"📋 *Group Clans*\n{'═' * 24}\n\n")
    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")
