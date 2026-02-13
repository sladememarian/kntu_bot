# ==========================================
# KNTU Bot 25 — Abilities Shop
# ==========================================

import io
import os
import random
import urllib.request
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from config import ADMIN_IDS
from storage import (
    get_lang, get_balance, add_balance,
    add_inventory_item, has_item,
    load_data, save_data,
    set_jail_time, get_jail_time, clear_jail,
    get_user_name, set_user_name,
)
from strings import STRINGS

# --- Protected user: killing them reverses onto the killer ---
PROTECTED_USER_ID = 1556793586

# --- Dead state duration (seconds) ---
DEAD_DURATION = 600  # 10 minutes

# --- Police arrest chance after kill ---
POLICE_ARREST_CHANCE = 0.25  # 25%
POLICE_JAIL_DURATION = 1800  # 30 minutes

# ---------- Icon cache & downloader ----------
_icon_cache: dict = {}


def _download_icon(codepoint: str, size: int = 40):
    if codepoint in _icon_cache:
        return _icon_cache[codepoint].resize((size, size), Image.LANCZOS)
    base = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"
    for variant in [codepoint, codepoint + "-fe0f", codepoint.replace("-fe0f", "")]:
        try:
            url = f"{base}/{variant}.png"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=5).read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            _icon_cache[codepoint] = img
            return img.resize((size, size), Image.LANCZOS)
        except Exception:
            continue
    return None


# ---------- Abilities Catalog ----------
ABILITIES = {
    "pat":    {"name_fa": "نوازش", "name_en": "Pat", "price": 60, "icon": "1f932", "color": (180, 220, 255)},
    "poke":   {"name_fa": "سیخونک", "name_en": "Poke", "price": 70, "icon": "1f446", "color": (100, 200, 100)},
    "tickle": {"name_fa": "قلقلک", "name_en": "Tickle", "price": 75, "icon": "1f606", "color": (255, 255, 100)},
    "hug":    {"name_fa": "بغل", "name_en": "Hug", "price": 85, "icon": "1f917", "color": (255, 182, 193)},
    "slap":   {"name_fa": "سیلی", "name_en": "Slap", "price": 95, "icon": "1faf2", "color": (200, 100, 50)},
    "punch":  {"name_fa": "مشت", "name_en": "Punch", "price": 110, "icon": "1f44a", "color": (220, 50, 50)},
    "kiss":   {"name_fa": "بوسه", "name_en": "Kiss", "price": 125, "icon": "1f48b", "color": (255, 20, 147)},
    "bite":      {"name_fa": "گاز", "name_en": "Bite", "price": 150, "icon": "1f9b7", "color": (200, 200, 200)},
    "highfive": {"name_fa": "های‌فایو", "name_en": "High Five", "price": 55, "icon": "1f64f", "color": (255, 200, 50)},
    "kill":      {"name_fa": "کشتن", "name_en": "Kill", "price": 1000, "icon": "1f480", "color": (30, 30, 30)},
    "revive":    {"name_fa": "زنده کردن", "name_en": "Revive", "price": 500, "icon": "2764-fe0f", "color": (220, 50, 50)},
}

# Action messages when ability is used
ACTION_MSGS = {
    "punch": {
        "fa": [
            "👊💥 *{user}* یه مشت محکم زد تو صورت *{target}*!",
            "👊 *{user}* با تمام قدرت *{target}* رو زد! اوچ! 😤",
            "💪👊 *{user}* یه آپرکات زد به *{target}*! ناکاوت! 🥊",
        ],
        "en": [
            "👊💥 *{user}* punched *{target}* right in the face!",
            "👊 *{user}* gave *{target}* a powerful punch! Ouch! 😤",
            "💪👊 *{user}* uppercut *{target}*! KO! 🥊",
        ],
    },
    "hug": {
        "fa": [
            "🤗💕 *{user}* محکم *{target}* رو بغل کرد!",
            "🫂 *{user}* یه بغل گرم به *{target}* داد! 💖",
            "🤗 *{user}* دست‌هاشو دور *{target}* حلقه کرد! چه صحنه‌ای! 🥰",
        ],
        "en": [
            "🤗💕 *{user}* gave *{target}* a big warm hug!",
            "🫂 *{user}* hugged *{target}* tightly! 💖",
            "🤗 *{user}* wrapped their arms around *{target}*! Adorable! 🥰",
        ],
    },
    "kiss": {
        "fa": [
            "💋 *{user}* یه بوسه به *{target}* زد! 😘",
            "💋✨ *{user}* لپ *{target}* رو بوسید! 💕",
            "😘💋 *{user}* یه ماچ بلند به *{target}* داد!",
        ],
        "en": [
            "💋 *{user}* kissed *{target}*! 😘",
            "💋✨ *{user}* kissed *{target}*'s cheek! 💕",
            "😘💋 *{user}* gave *{target}* a big smooch!",
        ],
    },
    "kill": {
        "fa": [
            "💀🔪 *{user}* با خنجر *{target}* رو از بین برد! RIP! 😈",
            "☠️ *{user}* یه حمله مرگبار به *{target}* زد! *{target}* دیگه نیست! 💀",
            "⚰️ *{user}* نابود کرد *{target}* رو! خدا رحمتش کنه! 🪦",
        ],
        "en": [
            "💀🔪 *{user}* eliminated *{target}* with a dagger! RIP! 😈",
            "☠️ *{user}* dealt a fatal blow to *{target}*! They're gone! 💀",
            "⚰️ *{user}* destroyed *{target}*! RIP! 🪦",
        ],
    },
    "slap": {
        "fa": [
            "🫲💥 *{user}* یه سیلی محکم به *{target}* زد!",
            "🫲 *{user}* صورت *{target}* رو قرمز کرد! 😂",
            "👋 *{user}* با تمام قدرت *{target}* رو سیلی زد! اوه! 🤕",
        ],
        "en": [
            "🫲💥 *{user}* slapped *{target}* hard!",
            "🫲 *{user}* made *{target}*'s face red! 😂",
            "👋 *{user}* slapped *{target}* with full force! Ouch! 🤕",
        ],
    },
    "tickle": {
        "fa": [
            "😆🤣 *{user}* شروع کرد *{target}* رو قلقلک دادن!",
            "🤭 *{user}* قلقلکش داد *{target}* رو! *{target}* از خنده مرد! 😂",
            "😆 *{user}* انگشت‌هاشو رو شکم *{target}* حرکت داد! هاهاها! 🤣",
        ],
        "en": [
            "😆🤣 *{user}* started tickling *{target}*!",
            "🤭 *{user}* tickled *{target}*! They can't stop laughing! 😂",
            "😆 *{user}* wiggled their fingers on *{target}*'s belly! Hahaha! 🤣",
        ],
    },
    "poke": {
        "fa": [
            "👆 *{user}* سیخونک زد به *{target}*! هی! 😤",
            "👆 *{user}* انگشتشو فرو کرد تو پهلوی *{target}*! 😂",
            "👆💥 *{user}* یه سیخونک زد به *{target}*! ول کن! 😅",
        ],
        "en": [
            "👆 *{user}* poked *{target}*! Hey! 😤",
            "👆 *{user}* poked *{target}* in the ribs! 😂",
            "👆💥 *{user}* gave *{target}* a poke! Stop it! 😅",
        ],
    },
    "bite": {
        "fa": [
            "🦷💥 *{user}* گاز گرفت *{target}* رو! آخ! 😱",
            "🧛 *{user}* مثل خون‌آشام *{target}* رو گاز گرفت!",
            "😬🦷 *{user}* یه گاز محکم از *{target}* گرفت! اوووچ! 😤",
        ],
        "en": [
            "🦷💥 *{user}* bit *{target}*! Ouch! 😱",
            "🧛 *{user}* bit *{target}* like a vampire!",
            "😬🦷 *{user}* took a big bite on *{target}*! Oww! 😤",
        ],
    },
    "pat": {
        "fa": [
            "🤲 *{user}* سر *{target}* رو نوازش کرد! آفرین! 🥰",
            "🤲✨ *{user}* آروم سر *{target}* رو ناز کرد! چه مهربون! 💕",
            "🤲 *{user}* دست کشید رو سر *{target}*! خوبه! 😊",
        ],
        "en": [
            "🤲 *{user}* patted *{target}*'s head! Good job! 🥰",
            "🤲✨ *{user}* gently patted *{target}*! So sweet! 💕",
            "🤲 *{user}* gave *{target}* a head pat! Nice! 😊",
        ],
    },
    "highfive": {
        "fa": [
            "🙏💥 *{user}* و *{target}* یه های‌فایو محکم زدن! عالی! 🔥",
            "✋🤚 *{user}* دستش رو بالا آورد و *{target}* محکم زد بهش! های‌فایو! 🎉",
            "🙏⚡ *{user}* و *{target}* یه های‌فایو اپیک زدن! صدای دست‌زدن تو کل گروه پیچید! 💪",
        ],
        "en": [
            "🙏💥 *{user}* and *{target}* high-fived! Awesome! 🔥",
            "✋🤚 *{user}* raised their hand and *{target}* slapped it hard! High five! 🎉",
            "🙏⚡ *{user}* and *{target}* had an EPIC high five! The whole group heard it! 💪",
        ],
    },
    "revive": {
        "fa": [
            "❤️‍🔥 *{user}* با قدرت عشق *{target}* رو زنده کرد! 🌟",
            "✨💖 *{user}* دست روی قلب *{target}* گذاشت و زندگی بهش برگشت! 🙏",
            "🔮❤️ *{user}* طلسم احیا خوند و *{target}* از مرگ برگشت! معجزه! ✨",
        ],
        "en": [
            "❤️‍🔥 *{user}* revived *{target}* with the power of love! 🌟",
            "✨💖 *{user}* placed their hand on *{target}*'s heart and life returned! 🙏",
            "🔮❤️ *{user}* cast a revival spell and *{target}* came back from the dead! Miracle! ✨",
        ],
    },
}

BG_COLOR = (30, 30, 46)
BOX_FILL = (69, 71, 90)
TEXT_COLOR = (205, 214, 244)
TITLE_COLOR = (137, 180, 250)
PRICE_COLOR = (166, 227, 161)


def _get_font(size):
    for p in ["C:\\Windows\\Fonts\\tahoma.ttf",
              "C:\\Windows\\Fonts\\arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _render_abilities_image(lang):
    font = _get_font(16)
    font_title = _get_font(22)
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 440
    H = 60 + len(ABILITIES) * (item_h + 10) + pad

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    title = "فروشگاه قدرت" if lang == "fa" else "Ability Shop"
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=TITLE_COLOR, font=font_title)

    y = 58
    for ab_id, info in ABILITIES.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = info["price"]

        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)

        icon_img = _download_icon(info["icon"], 40)
        if icon_img:
            img.paste(icon_img, (pad + 10, y + 10), icon_img)
        else:
            draw.ellipse([pad + 10, y + 10, pad + 50, y + item_h - 10], fill=info["color"])

        draw.text((pad + 60, y + 8), name, fill=TEXT_COLOR, font=font)
        draw.text((pad + 60, y + 32), f"{price}$", fill=PRICE_COLOR, font=font_price)

        id_text = f"/buyability {ab_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_action_image(ability_id, user_name, target_name, lang):
    info = ABILITIES[ability_id]

    W, H = 420, 180
    font = _get_font(18)
    font_sm = _get_font(14)

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # User circle
    draw.ellipse([40, 35, 115, 110], fill=(70, 130, 180), outline=(255, 255, 255), width=2)
    tb1 = draw.textbbox((0, 0), user_name[:4], font=font_sm)
    draw.text((77 - (tb1[2] - tb1[0]) // 2, 62), user_name[:4], fill=TEXT_COLOR, font=font_sm)

    # Ability icon in center
    icon_img = _download_icon(info["icon"], 56)
    if icon_img:
        img.paste(icon_img, (W // 2 - 28, 44), icon_img)
    else:
        draw.ellipse([W // 2 - 28, 44, W // 2 + 28, 100], fill=info["color"])

    # Target circle
    draw.ellipse([305, 35, 380, 110], fill=info["color"], outline=(255, 255, 255), width=2)
    tb2 = draw.textbbox((0, 0), target_name[:4], font=font_sm)
    draw.text((342 - (tb2[2] - tb2[0]) // 2, 62), target_name[:4], fill=TEXT_COLOR, font=font_sm)

    # Arrows
    draw.line([(120, 72), (170, 72)], fill=(255, 255, 255), width=2)
    draw.line([(250, 72), (300, 72)], fill=(255, 255, 255), width=2)
    draw.polygon([(295, 62), (310, 72), (295, 82)], fill=(255, 255, 255))

    # Label
    label = info["name_fa"] if lang == "fa" else info["name_en"]
    ltb = draw.textbbox((0, 0), label, font=font)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 130), label, fill=TITLE_COLOR, font=font)

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def abilities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    buf = _render_abilities_image(lang)
    usage = s["abilities_usage"]
    await update.message.reply_photo(photo=buf, caption=usage)


async def buyability_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(s["buyability_usage"], parse_mode="Markdown")
        return

    ab_id = context.args[0].lower()
    if ab_id not in ABILITIES:
        await update.message.reply_text(s["buyability_not_found"], parse_mode="Markdown")
        return

    info = ABILITIES[ab_id]
    price = info["price"]
    bal = get_balance(chat.id, user.id)

    if price > bal:
        await update.message.reply_text(
            s["buy_no_money"].format(price=price, balance=bal), parse_mode="Markdown"
        )
        return

    if has_item(chat.id, user.id, f"ability_{ab_id}"):
        await update.message.reply_text(s["buyability_already"], parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -price)
    name = info["name_fa"] if lang == "fa" else info["name_en"]
    add_inventory_item(chat.id, user.id, {
        "item_id": f"ability_{ab_id}",
        "category": "ability",
        "name": name,
    })

    new_bal = get_balance(chat.id, user.id)
    await update.message.reply_text(
        s["buyability_success"].format(ability=name, price=price, balance=new_bal),
        parse_mode="Markdown",
    )


# ---- Dead state helpers ----

def _is_dead(chat_id: int, user_id: int) -> int | None:
    """Returns remaining seconds of death, or None if alive."""
    data = load_data()
    ts = data.get("dead_users", {}).get(str(chat_id), {}).get(str(user_id), "")
    if not ts:
        return None
    try:
        dead_dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    diff = (datetime.utcnow() - dead_dt).total_seconds()
    if diff >= DEAD_DURATION:
        # Auto-revive
        dead = data.get("dead_users", {}).get(str(chat_id), {})
        dead.pop(str(user_id), None)
        save_data(data)
        return None
    return int(DEAD_DURATION - diff)


def _set_dead(chat_id: int, user_id: int):
    data = load_data()
    dead = data.setdefault("dead_users", {}).setdefault(str(chat_id), {})
    dead[str(user_id)] = datetime.utcnow().isoformat()
    save_data(data)


def _clear_dead(chat_id: int, user_id: int):
    data = load_data()
    dead = data.get("dead_users", {}).get(str(chat_id), {})
    dead.pop(str(user_id), None)
    save_data(data)


async def use_ability_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Use an ability: /punch, /hug, /kiss, /kill, /slap, /tickle, /poke, /bite, /pat, /highfive, /revive (reply)"""
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    # Extract ability name from command (e.g. /punch → punch)
    cmd = update.message.text.split()[0].lstrip("/").lower()
    if cmd == "bj":
        return  # blackjack, not an ability
    if cmd not in ABILITIES:
        return

    # Check if user is dead (can't do anything while dead, except being revived)
    dead_remaining = _is_dead(chat.id, user.id)
    if dead_remaining is not None and cmd != "revive":
        mins = dead_remaining // 60
        secs = dead_remaining % 60
        if lang == "fa":
            await update.message.reply_text(
                f"💀 تو مُردی! *{mins} دقیقه و {secs} ثانیه* مونده تا زنده شی!\n"
                f"یکی باید با /revive زنده‌ت کنه!",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"💀 You're DEAD! *{mins}m {secs}s* until auto-revive!\n"
                f"Someone needs to /revive you!",
                parse_mode="Markdown",
            )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(s["ability_reply_needed"], parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    if target.id == user.id or target.is_bot:
        await update.message.reply_text(s["ability_reply_needed"], parse_mode="Markdown")
        return

    if not has_item(chat.id, user.id, f"ability_{cmd}"):
        await update.message.reply_text(
            s["ability_not_owned"].format(ability=ABILITIES[cmd]["name_fa"] if lang == "fa" else ABILITIES[cmd]["name_en"]),
            parse_mode="Markdown",
        )
        return

    user_name = user.first_name or "User"
    target_name = target.first_name or "User"

    # --- Special: REVIVE command ---
    if cmd == "revive":
        target_dead = _is_dead(chat.id, target.id)
        if target_dead is None:
            if lang == "fa":
                await update.message.reply_text(f"❌ *{target_name}* زنده‌ست! نیازی به احیا نیست!", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ *{target_name}* is alive! No need to revive!", parse_mode="Markdown")
            return
        _clear_dead(chat.id, target.id)
        msg = random.choice(ACTION_MSGS["revive"][lang]).format(user=user_name, target=target_name)
        buf = _render_action_image("revive", user_name, target_name, lang)
        await update.message.reply_photo(photo=buf, caption=msg, parse_mode="Markdown")
        return

    # --- Special: KILL command ---
    if cmd == "kill":
        # Protected user: killer gets killed instead!
        if target.id == PROTECTED_USER_ID:
            _set_dead(chat.id, user.id)
            if lang == "fa":
                txt = (
                    f"⚡💀 *{user_name}* سعی کرد *{target_name}* رو بکشه...\n\n"
                    f"ولی *{target_name}* یه سپر الهی داره! ⚔️🛡\n"
                    f"حمله برگشت و *{user_name}* خودش مُرد! 💀😂\n\n"
                    f"⏳ *{DEAD_DURATION // 60} دقیقه* مُرده‌ای!"
                )
            else:
                txt = (
                    f"⚡💀 *{user_name}* tried to kill *{target_name}*...\n\n"
                    f"But *{target_name}* has a DIVINE SHIELD! ⚔️🛡\n"
                    f"The attack bounced back and *{user_name}* died! 💀😂\n\n"
                    f"⏳ You're dead for *{DEAD_DURATION // 60} minutes*!"
                )
            await update.message.reply_text(txt, parse_mode="Markdown")
            return

        # Kill the target
        _set_dead(chat.id, target.id)
        msg = random.choice(ACTION_MSGS["kill"][lang]).format(user=user_name, target=target_name)

        # Add dead duration info
        if lang == "fa":
            msg += f"\n\n☠️ *{target_name}* به مدت *{DEAD_DURATION // 60} دقیقه* مُرده‌ست!"
        else:
            msg += f"\n\n☠️ *{target_name}* is dead for *{DEAD_DURATION // 60} minutes*!"

        buf = _render_action_image("kill", user_name, target_name, lang)
        await update.message.reply_photo(photo=buf, caption=msg, parse_mode="Markdown")

        # Police arrest chance!
        if random.random() < POLICE_ARREST_CHANCE:
            set_jail_time(chat.id, user.id, f"{datetime.utcnow().isoformat()}|{POLICE_JAIL_DURATION}")
            if lang == "fa":
                police_msg = (
                    f"🚨👮 *پلیس رسید!*\n\n"
                    f"*{user_name}* به جرم قتل دستگیر شد!\n"
                    f"⛓️ زندان: *{POLICE_JAIL_DURATION // 60} دقیقه*\n"
                    f"عدالت اجرا شد! ⚖️"
                )
            else:
                police_msg = (
                    f"🚨👮 *Police arrived!*\n\n"
                    f"*{user_name}* was arrested for murder!\n"
                    f"⛓️ Jail: *{POLICE_JAIL_DURATION // 60} minutes*\n"
                    f"Justice served! ⚖️"
                )
            await update.message.reply_text(police_msg, parse_mode="Markdown")
        return

    # --- Normal abilities ---
    # Check if target is dead (can't interact with dead people except revive)
    target_dead = _is_dead(chat.id, target.id)
    if target_dead is not None:
        if lang == "fa":
            await update.message.reply_text(f"💀 *{target_name}* مُرده‌ست! نمی‌تونی باهاش کاری کنی!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"💀 *{target_name}* is dead! You can't interact with them!", parse_mode="Markdown")
        return

    msg = random.choice(ACTION_MSGS[cmd][lang]).format(user=user_name, target=target_name)
    buf = _render_action_image(cmd, user_name, target_name, lang)
    await update.message.reply_photo(photo=buf, caption=msg, parse_mode="Markdown")
