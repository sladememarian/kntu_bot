# ==========================================
# KNTU Bot 25 — Abilities Shop (Punch, Hug, Kiss, Kill)
# ==========================================

import io
import os
import random
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    add_inventory_item, has_item,
)
from strings import STRINGS

ABILITIES = {
    "punch":  {"name_fa": "مشت 👊", "name_en": "Punch 👊", "price": 100, "emoji": "👊", "color": (220, 50, 50)},
    "hug":    {"name_fa": "بغل 🤗", "name_en": "Hug 🤗", "price": 80, "emoji": "🤗", "color": (255, 182, 193)},
    "kiss":   {"name_fa": "بوسه 💋", "name_en": "Kiss 💋", "price": 120, "emoji": "💋", "color": (255, 20, 147)},
    "kill":   {"name_fa": "کشتن 💀", "name_en": "Kill 💀", "price": 300, "emoji": "💀", "color": (30, 30, 30)},
    "slap":   {"name_fa": "سیلی 🫲", "name_en": "Slap 🫲", "price": 90, "emoji": "🫲", "color": (200, 100, 50)},
    "tickle": {"name_fa": "قلقلک 😆", "name_en": "Tickle 😆", "price": 70, "emoji": "😆", "color": (255, 255, 100)},
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
}

BG_COLOR = (30, 30, 46)
BOX_FILL = (69, 71, 90)
TEXT_COLOR = (205, 214, 244)
TITLE_COLOR = (137, 180, 250)
PRICE_COLOR = (166, 227, 161)


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for p in ["C:\\Windows\\Fonts\\tahoma.ttf",
              "C:\\Windows\\Fonts\\arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _render_abilities_image(lang: str) -> io.BytesIO:
    font = _get_font(16)
    font_title = _get_font(22)
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 420
    H = 60 + len(ABILITIES) * (item_h + 10) + pad

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title = "⚔️ فروشگاه قدرت" if lang == "fa" else "⚔️ Ability Shop"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 14), title, fill=TITLE_COLOR, font=font_title)

    y = 55
    for ab_id, info in ABILITIES.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = info["price"]
        color = info["color"]

        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)
        draw.ellipse([pad + 10, y + 10, pad + 50, y + item_h - 10], fill=color)
        draw.text((pad + 62, y + 8), name, fill=TEXT_COLOR, font=font)
        draw.text((pad + 62, y + 32), f"{price}$", fill=PRICE_COLOR, font=font_price)

        id_text = f"/buyability {ab_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_action_image(ability_id: str, user_name: str, target_name: str, lang: str) -> io.BytesIO:
    info = ABILITIES[ability_id]
    color = info["color"]

    W, H = 400, 180
    font = _get_font(18)
    font_big = _get_font(36)
    font_sm = _get_font(14)

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Two circles (user → target)
    draw.ellipse([40, 40, 110, 110], fill=(70, 130, 180), outline=(255, 255, 255), width=2)
    tb1 = draw.textbbox((0, 0), user_name[:3], font=font)
    draw.text((75 - (tb1[2] - tb1[0]) // 2, 65), user_name[:3], fill=TEXT_COLOR, font=font)

    # Emoji in middle
    etb = draw.textbbox((0, 0), info["emoji"], font=font_big)
    draw.text((W // 2 - (etb[2] - etb[0]) // 2, 55), info["emoji"], font=font_big)

    draw.ellipse([290, 40, 360, 110], fill=color, outline=(255, 255, 255), width=2)
    tb2 = draw.textbbox((0, 0), target_name[:3], font=font)
    draw.text((325 - (tb2[2] - tb2[0]) // 2, 65), target_name[:3], fill=TEXT_COLOR, font=font)

    # Arrow
    draw.line([(115, 75), (285, 75)], fill=(255, 255, 255), width=2)
    draw.polygon([(280, 65), (295, 75), (280, 85)], fill=(255, 255, 255))

    # Label
    label = info["name_fa"] if lang == "fa" else info["name_en"]
    ltb = draw.textbbox((0, 0), label, font=font)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 130), label, fill=TITLE_COLOR, font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
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


async def use_ability_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Use an ability on someone: /punch, /hug, /kiss, /kill, /slap, /tickle (reply)"""
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    # Extract ability name from command (e.g. /punch → punch)
    cmd = update.message.text.split()[0].lstrip("/").lower()
    if cmd not in ABILITIES:
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

    msg = random.choice(ACTION_MSGS[cmd][lang]).format(user=user_name, target=target_name)
    buf = _render_action_image(cmd, user_name, target_name, lang)
    await update.message.reply_photo(photo=buf, caption=msg, parse_mode="Markdown")
