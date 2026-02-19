# ==========================================
# KNTU Bot 25 — Gacha Character Rolling System
# Roll, Collect, Trade, Sell characters
# ==========================================

import random
import time
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import (
    get_lang, get_balance, add_balance,
    get_gacha_collection, add_gacha_character, remove_gacha_character,
    get_claimed_characters, claim_character, unclaim_character,
    get_roll_info, set_roll_info, get_user_name,
)


# ═══════════════════════════════════════════════════
# CHARACTER DATABASE
# ═══════════════════════════════════════════════════

RARITY_CONFIG = {
    "common":    {"emoji": "⚪", "label_fa": "معمولی",    "label_en": "Common",    "weight": 45, "sell": 50},
    "uncommon":  {"emoji": "🟢", "label_fa": "غیرمعمول",  "label_en": "Uncommon",  "weight": 25, "sell": 150},
    "rare":      {"emoji": "🔵", "label_fa": "کمیاب",     "label_en": "Rare",      "weight": 18, "sell": 400},
    "epic":      {"emoji": "🟣", "label_fa": "حماسی",     "label_en": "Epic",      "weight": 9,  "sell": 1000},
    "legendary": {"emoji": "🟡", "label_fa": "افسانه‌ای", "label_en": "Legendary", "weight": 3,  "sell": 3000},
}

CHARACTERS = [
    # ═══ COMMON (⚪) — Minor spirits & folk creatures ═══
    {"id": "c01", "name_fa": "آنانسی",         "name_en": "Anansi",          "rarity": "common",    "power": 12, "emoji": "🕷️"},
    {"id": "c02", "name_fa": "کایوت",          "name_en": "Coyote",          "rarity": "common",    "power": 8,  "emoji": "🐺"},
    {"id": "c03", "name_fa": "پاک",            "name_en": "Puck",            "rarity": "common",    "power": 15, "emoji": "🧚"},
    {"id": "c04", "name_fa": "تانوکی",         "name_en": "Tanuki",          "rarity": "common",    "power": 14, "emoji": "🦝"},
    {"id": "c05", "name_fa": "نیمف",           "name_en": "Nymph",           "rarity": "common",    "power": 18, "emoji": "🧝‍♀️"},
    {"id": "c06", "name_fa": "گابلین",         "name_en": "Goblin",          "rarity": "common",    "power": 10, "emoji": "👺"},
    {"id": "c07", "name_fa": "سلکی",           "name_en": "Selkie",          "rarity": "common",    "power": 13, "emoji": "🦭"},
    {"id": "c08", "name_fa": "پیکسی",          "name_en": "Pixie",           "rarity": "common",    "power": 20, "emoji": "✨"},
    {"id": "c09", "name_fa": "کیتسونه",        "name_en": "Kitsune",         "rarity": "common",    "power": 11, "emoji": "🦊"},
    {"id": "c10", "name_fa": "فان",            "name_en": "Faun",            "rarity": "common",    "power": 9,  "emoji": "🐐"},
    {"id": "c11", "name_fa": "بنشی",           "name_en": "Banshee",         "rarity": "common",    "power": 16, "emoji": "👻"},
    {"id": "c12", "name_fa": "دریاد",          "name_en": "Dryad",           "rarity": "common",    "power": 17, "emoji": "🌳"},
    {"id": "c13", "name_fa": "سیرن",           "name_en": "Siren",           "rarity": "common",    "power": 12, "emoji": "🧜‍♀️"},
    {"id": "c14", "name_fa": "ایمپ",           "name_en": "Imp",             "rarity": "common",    "power": 10, "emoji": "😈"},
    {"id": "c15", "name_fa": "والکیری",        "name_en": "Valkyrie",        "rarity": "common",    "power": 19, "emoji": "⚔️"},
    # ═══ UNCOMMON (🟢) — Lesser gods & heroes ═══
    {"id": "u01", "name_fa": "هرمس",           "name_en": "Hermes",          "rarity": "uncommon",  "power": 35, "emoji": "🪶"},
    {"id": "u02", "name_fa": "هایمدال",        "name_en": "Heimdall",        "rarity": "uncommon",  "power": 40, "emoji": "🌈"},
    {"id": "u03", "name_fa": "باستت",          "name_en": "Bastet",          "rarity": "uncommon",  "power": 45, "emoji": "🐱"},
    {"id": "u04", "name_fa": "رابین هود",      "name_en": "Robin Hood",      "rarity": "uncommon",  "power": 38, "emoji": "🏹"},
    {"id": "u05", "name_fa": "کاوه",           "name_en": "Kaveh",           "rarity": "uncommon",  "power": 42, "emoji": "⚒️"},
    {"id": "u06", "name_fa": "آرش",            "name_en": "Arash",           "rarity": "uncommon",  "power": 48, "emoji": "🎯"},
    {"id": "u07", "name_fa": "پرسفونه",        "name_en": "Persephone",      "rarity": "uncommon",  "power": 36, "emoji": "🌸"},
    {"id": "u08", "name_fa": "دیونیسوس",       "name_en": "Dionysus",        "rarity": "uncommon",  "power": 44, "emoji": "🍷"},
    {"id": "u09", "name_fa": "بالدر",          "name_en": "Baldur",          "rarity": "uncommon",  "power": 50, "emoji": "💫"},
    {"id": "u10", "name_fa": "توت",            "name_en": "Thoth",           "rarity": "uncommon",  "power": 46, "emoji": "📜"},
    # ═══ RARE (🔵) — Major gods & legends ═══
    {"id": "r01", "name_fa": "آرتمیس",         "name_en": "Artemis",         "rarity": "rare",      "power": 75, "emoji": "🌙"},
    {"id": "r02", "name_fa": "لوکی",           "name_en": "Loki",            "rarity": "rare",      "power": 80, "emoji": "🃏"},
    {"id": "r03", "name_fa": "هوروس",          "name_en": "Horus",           "rarity": "rare",      "power": 85, "emoji": "🦅"},
    {"id": "r04", "name_fa": "فریا",           "name_en": "Freya",           "rarity": "rare",      "power": 90, "emoji": "💎"},
    {"id": "r05", "name_fa": "مرلین",          "name_en": "Merlin",          "rarity": "rare",      "power": 88, "emoji": "🧙‍♂️"},
    {"id": "r06", "name_fa": "سان ووکونگ",     "name_en": "Sun Wukong",      "rarity": "rare",      "power": 82, "emoji": "🐒"},
    {"id": "r07", "name_fa": "سوسانو",         "name_en": "Susanoo",         "rarity": "rare",      "power": 78, "emoji": "🌊"},
    {"id": "r08", "name_fa": "گیلگمش",         "name_en": "Gilgamesh",       "rarity": "rare",      "power": 86, "emoji": "👑"},
    # ═══ EPIC (🟣) — Mighty gods ═══
    {"id": "e01", "name_fa": "آتنا",           "name_en": "Athena",          "rarity": "epic",      "power": 150, "emoji": "🦉"},
    {"id": "e02", "name_fa": "ثور",            "name_en": "Thor",            "rarity": "epic",      "power": 180, "emoji": "🔨"},
    {"id": "e03", "name_fa": "آنوبیس",         "name_en": "Anubis",          "rarity": "epic",      "power": 170, "emoji": "⚰️"},
    {"id": "e04", "name_fa": "رستم",           "name_en": "Rostam",          "rarity": "epic",      "power": 190, "emoji": "🦁"},
    {"id": "e05", "name_fa": "آماتراسو",       "name_en": "Amaterasu",       "rarity": "epic",      "power": 175, "emoji": "🔆"},
    # ═══ LEGENDARY (🟡) — Supreme beings ═══
    {"id": "l01", "name_fa": "زئوس",           "name_en": "Zeus",            "rarity": "legendary", "power": 350, "emoji": "⚡"},
    {"id": "l02", "name_fa": "اودین",          "name_en": "Odin",            "rarity": "legendary", "power": 400, "emoji": "👁️"},
    {"id": "l03", "name_fa": "رع",             "name_en": "Ra",              "rarity": "legendary", "power": 500, "emoji": "☀️"},
]

_CHAR_BY_ID = {c["id"]: c for c in CHARACTERS}

MAX_ROLLS = 5
ROLL_COOLDOWN = 4 * 3600  # 4 hours

_RARITY_STARS = {
    "common": "⭐", "uncommon": "⭐⭐", "rare": "⭐⭐⭐",
    "epic": "⭐⭐⭐⭐", "legendary": "⭐⭐⭐⭐⭐",
}


def _pick_character() -> dict:
    pool = []
    for c in CHARACTERS:
        pool.extend([c] * RARITY_CONFIG[c["rarity"]]["weight"])
    return random.choice(pool)


_DICEBEAR_BASE = "https://api.dicebear.com/9.x/adventurer/png"


def _char_image_url(char: dict) -> str:
    """DiceBear avatar URL — unique per character name."""
    seed = char["name_en"].replace(" ", "")
    return f"{_DICEBEAR_BASE}?seed={seed}&size=256"


async def _edit_msg(query, text, **kwargs):
    """Edit message — works for both photo captions and text messages."""
    try:
        await query.edit_message_caption(caption=text, **kwargs)
    except Exception:
        await query.edit_message_text(text, **kwargs)


# ═══════════════════════════════════════════════════
# /roll — Gacha character roll
# ═══════════════════════════════════════════════════

async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)

    info = get_roll_info(chat.id, user.id)
    now = time.time()
    reset_at = info.get("reset_at", "")
    count = info.get("count", 0)

    if reset_at and float(reset_at) > now:
        if count >= MAX_ROLLS:
            remaining = int(float(reset_at) - now)
            h, m = divmod(remaining // 60, 60)
            if lang == "fa":
                await update.message.reply_text(
                    f"🎰 رول‌هات تمام شده! ({MAX_ROLLS}/{MAX_ROLLS})\n"
                    f"⏰ ریست: *{h}* ساعت *{m}* دقیقه دیگه",
                    parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    f"🎰 No rolls left! ({MAX_ROLLS}/{MAX_ROLLS})\n"
                    f"⏰ Resets in: *{h}*h *{m}*m",
                    parse_mode="Markdown")
            return
    else:
        count = 0

    char = _pick_character()
    claimed = get_claimed_characters(chat.id)
    is_claimed = char["id"] in claimed
    owner_id = claimed.get(char["id"])
    rarity = RARITY_CONFIG[char["rarity"]]
    name = char.get(f"name_{lang}", char["name_en"])
    rarity_label = rarity.get(f"label_{lang}", rarity["label_en"])

    if lang == "fa":
        text = (
            f"🎰 *رول {count + 1}/{MAX_ROLLS}*\n"
            f"{'═' * 24}\n\n"
            f"{char['emoji']} *{name}*\n\n"
            f"📊 نادرگی: {rarity['emoji']} {rarity_label}\n"
            f"{_RARITY_STARS[char['rarity']]}\n"
            f"⚔️ قدرت: *{char['power']}*\n"
            f"💰 ارزش فروش: *{rarity['sell']}$*\n"
        )
        if is_claimed:
            owner_name = get_user_name(chat.id, owner_id) or f"User {owner_id}"
            text += f"\n❌ گرفته شده توسط *{owner_name}*"
        else:
            text += "\n✅ آزاد! بزن بگیرش!"
    else:
        text = (
            f"🎰 *Roll {count + 1}/{MAX_ROLLS}*\n"
            f"{'═' * 24}\n\n"
            f"{char['emoji']} *{name}*\n\n"
            f"📊 Rarity: {rarity['emoji']} {rarity_label}\n"
            f"{_RARITY_STARS[char['rarity']]}\n"
            f"⚔️ Power: *{char['power']}*\n"
            f"💰 Sell value: *{rarity['sell']}$*\n"
        )
        if is_claimed:
            owner_name = get_user_name(chat.id, owner_id) or f"User {owner_id}"
            text += f"\n❌ Already claimed by *{owner_name}*"
        else:
            text += "\n✅ Available! Click to claim!"

    count += 1
    if count >= MAX_ROLLS:
        reset_time = now + ROLL_COOLDOWN
    else:
        reset_time = float(info.get("reset_at", 0)) or (now + ROLL_COOLDOWN)
    set_roll_info(chat.id, user.id, {"count": count, "reset_at": str(reset_time)})

    img_url = _char_image_url(char)
    if not is_claimed:
        btn = "🎯 بگیرش!" if lang == "fa" else "🎯 Claim!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn, callback_data=f"gacha_claim:{char['id']}")]
        ])
        try:
            await update.message.reply_photo(
                photo=img_url, caption=text,
                parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            await update.message.reply_text(
                text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        try:
            await update.message.reply_photo(
                photo=img_url, caption=text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# Claim callback
# ═══════════════════════════════════════════════════

async def gacha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not data.startswith("gacha_claim:"):
        return
    await query.answer()

    char_id = data.split(":")[1]
    chat = update.effective_chat
    user = query.from_user
    lang = get_lang(chat.id)

    char = _CHAR_BY_ID.get(char_id)
    if not char:
        await _edit_msg(query, "❌ Character not found.")
        return

    claimed = get_claimed_characters(chat.id)
    if char_id in claimed:
        msg = "❌ دیر رسیدی! قبلاً گرفته شده. 😢" if lang == "fa" else "❌ Too late! Already claimed. 😢"
        await _edit_msg(query, msg)
        return

    claim_character(chat.id, user.id, char_id)
    char_copy = dict(char)
    char_copy["claimed_at"] = datetime.utcnow().isoformat()
    add_gacha_character(chat.id, user.id, char_copy)

    name = char.get(f"name_{lang}", char["name_en"])
    rarity = RARITY_CONFIG[char["rarity"]]

    if lang == "fa":
        text = (
            f"🎉 *{user.first_name}* شخصیت رو گرفت!\n\n"
            f"{char['emoji']} *{name}*\n"
            f"📊 {rarity['emoji']} {rarity.get('label_fa', rarity['label_en'])} | ⚔️ {char['power']}\n\n"
            f"✅ به مجموعه اضافه شد!"
        )
    else:
        text = (
            f"🎉 *{user.first_name}* claimed the character!\n\n"
            f"{char['emoji']} *{name}*\n"
            f"📊 {rarity['emoji']} {rarity['label_en']} | ⚔️ {char['power']}\n\n"
            f"✅ Added to collection!"
        )
    await _edit_msg(query, text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# /collection — Show your characters
# ═══════════════════════════════════════════════════

async def collection_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    collection = get_gacha_collection(chat.id, user.id)
    if not collection:
        msg = "🃏 مجموعه خالیه! از /roll استفاده کن." if lang == "fa" else "🃏 Collection empty! Use /roll to get characters."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "uncommon": 3, "common": 4}
    collection.sort(key=lambda c: (rarity_order.get(c.get("rarity", "common"), 5), -c.get("power", 0)))

    total_power = sum(c.get("power", 0) for c in collection)
    if lang == "fa":
        header = f"🃏 *مجموعه {user.first_name}* ({len(collection)} شخصیت)\n⚔️ قدرت کل: *{total_power}*\n{'═' * 24}\n\n"
    else:
        header = f"🃏 *{user.first_name}'s Collection* ({len(collection)} chars)\n⚔️ Total Power: *{total_power}*\n{'═' * 24}\n\n"

    lines = []
    for c in collection[:20]:
        rarity = RARITY_CONFIG.get(c.get("rarity", "common"), RARITY_CONFIG["common"])
        name = c.get(f"name_{lang}", c.get("name_en", "???"))
        lines.append(f"{c.get('emoji', '❓')} {name} {rarity['emoji']} ⚔️{c.get('power', 0)}")

    if len(collection) > 20:
        extra = len(collection) - 20
        lines.append(f"\n... +{extra} {'بیشتر' if lang == 'fa' else 'more'}")

    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# /sellchar <name> — Sell a character for coins
# ═══════════════════════════════════════════════════

async def sellchar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)

    if not context.args:
        msg = "📝 /sellchar <نام شخصیت>" if lang == "fa" else "📝 /sellchar <character name>"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    query_str = " ".join(context.args).lower()
    collection = get_gacha_collection(chat.id, user.id)

    found = None
    for c in collection:
        if query_str in c.get("name_fa", "").lower() or query_str in c.get("name_en", "").lower():
            found = c
            break

    if not found:
        msg = "❌ این شخصیت توی مجموعت نیست!" if lang == "fa" else "❌ Character not in your collection!"
        await update.message.reply_text(msg)
        return

    sell_value = RARITY_CONFIG.get(found.get("rarity", "common"), RARITY_CONFIG["common"])["sell"]
    name = found.get(f"name_{lang}", found.get("name_en", "???"))

    remove_gacha_character(chat.id, user.id, found["id"])
    unclaim_character(chat.id, found["id"])
    new_bal = add_balance(chat.id, user.id, sell_value)

    if lang == "fa":
        await update.message.reply_text(
            f"💰 *{name}* فروخته شد!\n💵 دریافتی: *{sell_value}$*\n💳 موجودی: *{new_bal}$*",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"💰 Sold *{name}*!\n💵 Earned: *{sell_value}$*\n💳 Balance: *{new_bal}$*",
            parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# /tradechar <name> — Trade a character (reply to target)
# ═══════════════════════════════════════════════════

async def tradechar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)

    if not update.message.reply_to_message or not context.args:
        msg = ("📝 ریپلای کن و بنویس: /tradechar <نام شخصیت>"
               if lang == "fa" else
               "📝 Reply to someone: /tradechar <character name>")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    if target.id == user.id or target.is_bot:
        msg = "❌ نمیتونی با خودت معامله کنی!" if lang == "fa" else "❌ Can't trade with yourself!"
        await update.message.reply_text(msg)
        return

    query_str = " ".join(context.args).lower()
    collection = get_gacha_collection(chat.id, user.id)

    found = None
    for c in collection:
        if query_str in c.get("name_fa", "").lower() or query_str in c.get("name_en", "").lower():
            found = c
            break

    if not found:
        msg = "❌ این شخصیت توی مجموعت نیست!" if lang == "fa" else "❌ Character not in your collection!"
        await update.message.reply_text(msg)
        return

    sell_value = RARITY_CONFIG.get(found.get("rarity", "common"), RARITY_CONFIG["common"])["sell"]
    name = found.get(f"name_{lang}", found.get("name_en", "???"))
    rarity = RARITY_CONFIG[found["rarity"]]

    if lang == "fa":
        text = (
            f"🔄 *پیشنهاد معامله!*\n\n"
            f"📤 {user.first_name} → {target.first_name}\n"
            f"{found['emoji']} *{name}* {rarity['emoji']} ⚔️{found['power']}\n"
            f"💰 قیمت: *{sell_value}$*\n\n"
            f"_{target.first_name} باید قبول یا رد کنه._"
        )
    else:
        text = (
            f"🔄 *Trade Offer!*\n\n"
            f"📤 {user.first_name} → {target.first_name}\n"
            f"{found['emoji']} *{name}* {rarity['emoji']} ⚔️{found['power']}\n"
            f"💰 Price: *{sell_value}$*\n\n"
            f"_{target.first_name} must accept or decline._"
        )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "✅ قبول" if lang == "fa" else "✅ Accept",
            callback_data=f"trade_yes:{user.id}:{target.id}:{found['id']}"
        ),
        InlineKeyboardButton(
            "❌ رد" if lang == "fa" else "❌ Decline",
            callback_data=f"trade_no:{target.id}"
        ),
    ]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if data.startswith("trade_no:"):
        target_id = int(data.split(":")[1])
        if user.id != target_id:
            await query.answer("❌ This is not for you!" if lang == "en" else "❌ این برای تو نیست!", show_alert=True)
            return
        await query.answer()
        await query.edit_message_text("❌ معامله رد شد." if lang == "fa" else "❌ Trade declined.")
        return

    if data.startswith("trade_yes:"):
        parts = data.split(":")
        seller_id = int(parts[1])
        target_id = int(parts[2])
        char_id = parts[3]

        if user.id != target_id:
            await query.answer("❌ This is not for you!" if lang == "en" else "❌ این برای تو نیست!", show_alert=True)
            return
        await query.answer()

        seller_col = get_gacha_collection(chat.id, seller_id)
        found = None
        for c in seller_col:
            if c.get("id") == char_id:
                found = c
                break
        if not found:
            await query.edit_message_text("❌ شخصیت دیگه موجود نیست." if lang == "fa" else "❌ Character no longer available.")
            return

        sell_value = RARITY_CONFIG.get(found.get("rarity", "common"), RARITY_CONFIG["common"])["sell"]
        buyer_bal = get_balance(chat.id, target_id)
        if buyer_bal < sell_value:
            msg = f"❌ پول کافی نداری! نیاز: *{sell_value}$*" if lang == "fa" else f"❌ Not enough money! Need *{sell_value}$*"
            await query.edit_message_text(msg, parse_mode="Markdown")
            return

        remove_gacha_character(chat.id, seller_id, char_id)
        unclaim_character(chat.id, char_id)
        claim_character(chat.id, target_id, char_id)
        char_copy = dict(found)
        char_copy["claimed_at"] = datetime.utcnow().isoformat()
        add_gacha_character(chat.id, target_id, char_copy)
        add_balance(chat.id, target_id, -sell_value)
        add_balance(chat.id, seller_id, sell_value)

        name = found.get(f"name_{lang}", found.get("name_en", "???"))
        if lang == "fa":
            await query.edit_message_text(
                f"✅ *معامله انجام شد!*\n{found['emoji']} *{name}* → *{user.first_name}*\n💰 *{sell_value}$* پرداخت شد.",
                parse_mode="Markdown")
        else:
            await query.edit_message_text(
                f"✅ *Trade complete!*\n{found['emoji']} *{name}* → *{user.first_name}*\n💰 *{sell_value}$* paid.",
                parse_mode="Markdown")
