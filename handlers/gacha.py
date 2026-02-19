# ==========================================
# KNTU Bot 25 — Gacha Character Rolling System
# Roll, Collect, Trade, Sell characters
# ==========================================

import random
import time
import os
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

# ═══ RPG PORTRAIT CHARACTERS (local images) ═══
_RPG_CHARS = [
    # ─── Common (⚪) ───
    ("p001", "اسپرایت", "Sprite", "common", 12, "🧚‍♂️", 1),
    ("p002", "براونی", "Brownie", "common", 9, "🫘", 2),
    ("p003", "نوم", "Gnome", "common", 15, "🧙", 3),
    ("p004", "ترول", "Troll", "common", 20, "🧌", 4),
    ("p005", "لپرکان", "Leprechaun", "common", 11, "🍀", 5),
    ("p006", "رایث", "Wraith", "common", 18, "👤", 6),
    ("p007", "شید", "Shade", "common", 8, "🌑", 7),
    ("p008", "سیلف", "Sylph", "common", 14, "💨", 8),
    ("p009", "آندین", "Undine", "common", 16, "💧", 9),
    ("p010", "ساتیر", "Satyr", "common", 10, "🐏", 10),
    ("p011", "چنجلینگ", "Changeling", "common", 13, "🎭", 11),
    ("p012", "بوگارت", "Boggart", "common", 11, "👹", 12),
    ("p013", "غول", "Ghoul", "common", 19, "💀", 13),
    ("p014", "اسپکتر", "Specter", "common", 9, "🌫️", 14),
    ("p015", "ویسپ", "Wisp", "common", 8, "🔮", 15),
    ("p016", "هارپی", "Harpy", "common", 17, "🦅", 16),
    ("p017", "گرملین", "Gremlin", "common", 10, "😼", 17),
    ("p018", "کوبلد", "Kobold", "common", 12, "🐉", 18),
    ("p019", "نایاد", "Naiad", "common", 15, "🌊", 19),
    ("p020", "کلپی", "Kelpie", "common", 14, "🐴", 20),
    ("p021", "تنگو", "Tengu", "common", 18, "👺", 21),
    ("p022", "اونی", "Oni", "common", 21, "👹", 22),
    ("p023", "دوموووی", "Domovoi", "common", 9, "🏠", 23),
    ("p024", "لشی", "Leshy", "common", 16, "🌿", 24),
    ("p025", "روسالکا", "Rusalka", "common", 17, "💦", 25),
    ("p026", "استریکس", "Strix", "common", 13, "🦉", 26),
    ("p027", "ریونانت", "Revenant", "common", 20, "⚰️", 27),
    ("p028", "وایت", "Wight", "common", 11, "💀", 28),
    ("p029", "فانتوم", "Phantom", "common", 15, "👻", 29),
    ("p030", "فامیلیار", "Familiar", "common", 10, "🐈‍⬛", 30),
    ("p031", "نوماد", "Nomad", "common", 14, "🏜️", 31),
    ("p032", "کاتب", "Scribe", "common", 8, "✍️", 32),
    ("p033", "سنتینل", "Sentinel", "common", 22, "🛡️", 33),
    ("p034", "سرگردان", "Wanderer", "common", 12, "🚶", 34),
    ("p035", "مسافر", "Wayfarer", "common", 11, "🗺️", 35),
    ("p036", "شاگرد", "Acolyte", "common", 9, "📿", 36),
    ("p037", "درویش", "Dervish", "common", 19, "🌀", 37),
    ("p038", "زاهد", "Hermit", "common", 13, "🏔️", 38),
    ("p039", "شمن", "Shaman", "common", 16, "🪶", 39),
    ("p040", "نوازنده", "Bard", "common", 14, "🎵", 40),
    ("p041", "دزدِ دریا", "Corsair", "common", 20, "🏴‍☠️", 41),
    ("p042", "رنجر", "Ranger", "common", 17, "🏹", 42),
    ("p043", "راهب", "Monk", "common", 15, "🧘", 43),
    ("p044", "دروئید", "Druid", "common", 18, "🌲", 44),
    ("p045", "کیمیاگر", "Alchemist", "common", 21, "⚗️", 45),
    # ─── Uncommon (🟢) ───
    ("p046", "مدوسا", "Medusa", "uncommon", 38, "🐍", 46),
    ("p047", "اسفنکس", "Sphinx", "uncommon", 45, "🦁", 47),
    ("p048", "اکیدنا", "Echidna", "uncommon", 42, "🐲", 48),
    ("p049", "موریگان", "Morrigan", "uncommon", 48, "🪶", 49),
    ("p050", "بریجید", "Brigid", "uncommon", 35, "🔥", 50),
    ("p051", "سرنونوس", "Cernunnos", "uncommon", 44, "🦌", 51),
    ("p052", "مائویی", "Maui", "uncommon", 50, "🪝", 52),
    ("p053", "آنانکه", "Ananke", "uncommon", 36, "⏳", 53),
    ("p054", "نیکس", "Nyx", "uncommon", 47, "🌑", 54),
    ("p055", "اروس", "Eros", "uncommon", 33, "💘", 55),
    ("p056", "ایریس", "Iris", "uncommon", 30, "🌈", 56),
    ("p057", "پان", "Pan", "uncommon", 40, "🎶", 57),
    ("p058", "مورفئوس", "Morpheus", "uncommon", 46, "💤", 58),
    ("p059", "اسکولد", "Skuld", "uncommon", 52, "🔮", 59),
    ("p060", "وِردَندی", "Verdandi", "uncommon", 49, "⚖️", 60),
    ("p061", "اورد", "Urd", "uncommon", 43, "📜", 61),
    ("p062", "انکیدو", "Enkidu", "uncommon", 55, "🦬", 62),
    ("p063", "ایشتار", "Ishtar", "uncommon", 51, "⭐", 63),
    ("p064", "ماردوک", "Marduk", "uncommon", 53, "🗡️", 64),
    ("p065", "کتزال", "Quetzal", "uncommon", 37, "🐦", 65),
    ("p066", "اینانا", "Inanna", "uncommon", 41, "🌟", 66),
    ("p067", "تیامات", "Tiamat", "uncommon", 54, "🐉", 67),
    ("p068", "سخمت", "Sekhmet", "uncommon", 39, "🦁", 68),
    ("p069", "سوبِک", "Sobek", "uncommon", 43, "🐊", 69),
    ("p070", "خونسو", "Khonsu", "uncommon", 34, "🌙", 70),
    # ─── Rare (🔵) ───
    ("p071", "پوزئیدون", "Poseidon", "rare", 92, "🔱", 71),
    ("p072", "هادس", "Hades", "rare", 88, "💎", 72),
    ("p073", "آرِس", "Ares", "rare", 85, "⚔️", 73),
    ("p074", "هِفائستوس", "Hephaestus", "rare", 78, "🔨", 74),
    ("p075", "آپولو", "Apollo", "rare", 90, "🎵", 75),
    ("p076", "تیر", "Tyr", "rare", 82, "⚖️", 76),
    ("p077", "ویشنو", "Vishnu", "rare", 95, "🪷", 77),
    ("p078", "شیوا", "Shiva", "rare", 93, "🔥", 78),
    ("p079", "کالی", "Kali", "rare", 87, "⚡", 79),
    ("p080", "گانِشا", "Ganesha", "rare", 76, "🐘", 80),
    ("p081", "کتزالکوتل", "Quetzalcoatl", "rare", 91, "🐍", 81),
    ("p082", "ایزاناگی", "Izanagi", "rare", 84, "⛩️", 82),
    ("p083", "کو خولین", "Cu Chulainn", "rare", 89, "🗡️", 83),
    ("p084", "بئوولف", "Beowulf", "rare", 80, "🐲", 84),
    ("p085", "زیگفرید", "Siegfried", "rare", 83, "⚔️", 85),
    ("p086", "آشیل", "Achilles", "rare", 94, "🏛️", 86),
    ("p087", "آینیاس", "Aeneas", "rare", 77, "🛡️", 87),
    ("p088", "ادیسئوس", "Odysseus", "rare", 86, "🧭", 88),
    # ─── Epic (🟣) ───
    ("p089", "پرومتئوس", "Prometheus", "epic", 165, "🔥", 89),
    ("p090", "هرکول", "Hercules", "epic", 185, "💪", 90),
    ("p091", "پرسئوس", "Perseus", "epic", 160, "🛡️", 91),
    ("p092", "راما", "Rama", "epic", 195, "🏹", 92),
    ("p093", "هانومان", "Hanuman", "epic", 178, "🐵", 93),
    ("p094", "سورتر", "Surtr", "epic", 188, "🔥", 94),
    ("p095", "ایندرا", "Indra", "epic", 172, "⚡", 95),
    ("p096", "راوانا", "Ravana", "epic", 182, "👑", 96),
    ("p097", "آرجونا", "Arjuna", "epic", 168, "🏹", 97),
    # ─── Legendary (🟡) ───
    ("p098", "برهما", "Brahma", "legendary", 450, "🌸", 98),
    ("p099", "کرونوس", "Kronos", "legendary", 380, "⏰", 99),
    ("p100", "ایزانامی", "Izanami", "legendary", 420, "⛩️", 100),
]

for _id, _fa, _en, _rar, _pow, _emo, _num in _RPG_CHARS:
    CHARACTERS.append({
        "id": _id, "name_fa": _fa, "name_en": _en,
        "rarity": _rar, "power": _pow, "emoji": _emo,
        "image": f"rpg-character ({_num}).png",
    })

_CHAR_BY_ID = {c["id"]: c for c in CHARACTERS}

MAX_ROLLS = 5
ROLL_COOLDOWN = 4 * 3600  # 4 hours

_RARITY_STARS = {
    "common": "⭐", "uncommon": "⭐⭐", "rare": "⭐⭐⭐",
    "epic": "⭐⭐⭐⭐", "legendary": "⭐⭐⭐⭐⭐",
}


def _pick_character() -> dict:
    """Two-step: pick rarity by weight, then random char of that rarity."""
    rarities = list(RARITY_CONFIG.keys())
    weights = [RARITY_CONFIG[r]["weight"] for r in rarities]
    rarity = random.choices(rarities, weights=weights, k=1)[0]
    pool = [c for c in CHARACTERS if c["rarity"] == rarity]
    return random.choice(pool)


_DICEBEAR_BASE = "https://api.dicebear.com/9.x/adventurer/png"


def _char_image_url(char: dict) -> str:
    """DiceBear avatar URL — unique per character name."""
    seed = char["name_en"].replace(" ", "")
    return f"{_DICEBEAR_BASE}?seed={seed}&size=256"


_IMAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "gatcha_images", "RPG Character Portraits MEGAPACK 1",
)


def _get_char_image(char: dict):
    """Return local image file path if available, else DiceBear URL."""
    if "image" in char:
        path = os.path.join(_IMAGE_DIR, char["image"])
        if os.path.isfile(path):
            return path
    return _char_image_url(char)


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
    reset_at = info.get("reset_at") or 0
    try:
        reset_at = float(reset_at)
    except (ValueError, TypeError):
        reset_at = 0
    count = info.get("count", 0)

    if reset_at and reset_at > now:
        if count >= MAX_ROLLS:
            remaining = int(reset_at - now)
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
        reset_time = reset_at if reset_at > 0 else (now + ROLL_COOLDOWN)
    set_roll_info(chat.id, user.id, {"count": count, "reset_at": str(reset_time)})

    img_src = _get_char_image(char)
    is_local = isinstance(img_src, str) and os.path.isfile(img_src)

    async def _send_photo(**kw):
        try:
            if is_local:
                with open(img_src, "rb") as f:
                    await update.message.reply_photo(photo=f, **kw)
            else:
                await update.message.reply_photo(photo=img_src, **kw)
        except Exception:
            await update.message.reply_text(
                kw.get("caption", ""), parse_mode=kw.get("parse_mode"),
                reply_markup=kw.get("reply_markup"))

    if not is_claimed:
        btn = "🎯 بگیرش!" if lang == "fa" else "🎯 Claim!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn, callback_data=f"gacha_claim:{char['id']}")]
        ])
        await _send_photo(caption=text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await _send_photo(caption=text, parse_mode="Markdown")


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
