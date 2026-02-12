# ==========================================
# KNTU Bot 25 — Pet Shop
# ==========================================

import io
import os
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    get_inventory, add_inventory_item, has_item,
)
from strings import STRINGS

PETS = {
    "cat":      {"name_fa": "گربه 🐱", "name_en": "Cat 🐱", "price": 150, "emoji": "🐱", "color": (255, 165, 0)},
    "dog":      {"name_fa": "سگ 🐶", "name_en": "Dog 🐶", "price": 180, "emoji": "🐶", "color": (139, 90, 43)},
    "rabbit":   {"name_fa": "خرگوش 🐰", "name_en": "Rabbit 🐰", "price": 120, "emoji": "🐰", "color": (255, 200, 200)},
    "parrot":   {"name_fa": "طوطی 🦜", "name_en": "Parrot 🦜", "price": 200, "emoji": "🦜", "color": (0, 200, 0)},
    "fish":     {"name_fa": "ماهی 🐟", "name_en": "Fish 🐟", "price": 60, "emoji": "🐟", "color": (0, 150, 255)},
    "hamster":  {"name_fa": "همستر 🐹", "name_en": "Hamster 🐹", "price": 90, "emoji": "🐹", "color": (230, 190, 138)},
    "turtle":   {"name_fa": "لاک‌پشت 🐢", "name_en": "Turtle 🐢", "price": 100, "emoji": "🐢", "color": (34, 139, 34)},
    "dragon":   {"name_fa": "اژدها 🐉", "name_en": "Dragon 🐉", "price": 700, "emoji": "🐉", "color": (200, 0, 50)},
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


def _render_petshop_image(lang: str) -> io.BytesIO:
    font = _get_font(16)
    font_title = _get_font(22)
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 420
    H = 60 + len(PETS) * (item_h + 10) + pad

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title = "🐾 پت شاپ" if lang == "fa" else "🐾 Pet Shop"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 14), title, fill=TITLE_COLOR, font=font_title)

    y = 55
    for pet_id, info in PETS.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = info["price"]
        color = info["color"]

        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)
        draw.ellipse([pad + 10, y + 10, pad + 50, y + item_h - 10], fill=color)
        draw.text((pad + 62, y + 8), name, fill=TEXT_COLOR, font=font)
        draw.text((pad + 62, y + 32), f"{price}$", fill=PRICE_COLOR, font=font_price)

        id_text = f"/buypet {pet_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_pet_card(pet_id: str, info: dict, lang: str) -> io.BytesIO:
    name = info["name_fa"] if lang == "fa" else info["name_en"]
    color = info["color"]

    W, H = 300, 200
    font = _get_font(18)
    font_big = _get_font(40)
    font_sm = _get_font(14)

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, 80
    draw.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], fill=color, outline=(255, 255, 255), width=3)
    etb = draw.textbbox((0, 0), info["emoji"], font=font_big)
    draw.text((cx - (etb[2] - etb[0]) // 2, cy - 20), info["emoji"], font=font_big)

    ntb = draw.textbbox((0, 0), name, font=font)
    draw.text(((W - ntb[2] + ntb[0]) // 2, 140), name, fill=TEXT_COLOR, font=font)

    label = "🎉 حیوان جدیدت مبارک!" if lang == "fa" else "🎉 New pet acquired!"
    ltb = draw.textbbox((0, 0), label, font=font_sm)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 170), label, fill=PRICE_COLOR, font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def petshop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    buf = _render_petshop_image(lang)
    usage = s["petshop_usage"]
    await update.message.reply_photo(photo=buf, caption=usage)


async def buypet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(s["buypet_usage"], parse_mode="Markdown")
        return

    pet_id = context.args[0].lower()
    if pet_id not in PETS:
        await update.message.reply_text(s["buypet_not_found"], parse_mode="Markdown")
        return

    info = PETS[pet_id]
    price = info["price"]
    bal = get_balance(chat.id, user.id)

    if price > bal:
        await update.message.reply_text(
            s["buy_no_money"].format(price=price, balance=bal), parse_mode="Markdown"
        )
        return

    if has_item(chat.id, user.id, f"pet_{pet_id}"):
        await update.message.reply_text(s["buypet_already"], parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -price)
    name = info["name_fa"] if lang == "fa" else info["name_en"]
    add_inventory_item(chat.id, user.id, {
        "item_id": f"pet_{pet_id}",
        "category": "pet",
        "name": name,
    })

    buf = _render_pet_card(pet_id, info, lang)
    new_bal = get_balance(chat.id, user.id)
    caption = s["buypet_success"].format(pet=name, price=price, balance=new_bal)
    await update.message.reply_photo(photo=buf, caption=caption)
