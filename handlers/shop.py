# ==========================================
# KNTU Bot 25 — Shop System (Clothes, Accessories, Shoes, Socks, Rings)
# ==========================================

import io
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    get_inventory, add_inventory_item, remove_inventory_item, has_item,
)
from strings import STRINGS

# ---------- Shop Catalog ----------
SHOP_ITEMS = {
    "clothes": {
        "tshirt":    {"name_fa": "تی‌شرت 👕", "name_en": "T-Shirt 👕", "price": 80, "emoji": "👕", "color": (70, 130, 180)},
        "hoodie":    {"name_fa": "هودی 🧥", "name_en": "Hoodie 🧥", "price": 150, "emoji": "🧥", "color": (139, 69, 19)},
        "jacket":    {"name_fa": "کاپشن 🧥", "name_en": "Jacket 🧥", "price": 250, "emoji": "🧥", "color": (50, 50, 50)},
        "suit":      {"name_fa": "کت و شلوار 🤵", "name_en": "Suit 🤵", "price": 400, "emoji": "🤵", "color": (25, 25, 112)},
        "dress":     {"name_fa": "لباس مجلسی 👗", "name_en": "Dress 👗", "price": 350, "emoji": "👗", "color": (220, 20, 60)},
    },
    "accessories": {
        "watch":     {"name_fa": "ساعت ⌚", "name_en": "Watch ⌚", "price": 200, "emoji": "⌚", "color": (218, 165, 32)},
        "glasses":   {"name_fa": "عینک 🕶", "name_en": "Sunglasses 🕶", "price": 120, "emoji": "🕶", "color": (30, 30, 30)},
        "hat":       {"name_fa": "کلاه 🎩", "name_en": "Hat 🎩", "price": 100, "emoji": "🎩", "color": (60, 60, 60)},
        "necklace":  {"name_fa": "گردنبند 📿", "name_en": "Necklace 📿", "price": 180, "emoji": "📿", "color": (255, 215, 0)},
        "bracelet":  {"name_fa": "دستبند 📿", "name_en": "Bracelet 📿", "price": 130, "emoji": "📿", "color": (192, 192, 192)},
    },
    "shoes": {
        "sneakers":  {"name_fa": "کتونی 👟", "name_en": "Sneakers 👟", "price": 160, "emoji": "👟", "color": (255, 255, 255)},
        "boots":     {"name_fa": "بوت 🥾", "name_en": "Boots 🥾", "price": 220, "emoji": "🥾", "color": (101, 67, 33)},
        "heels":     {"name_fa": "پاشنه بلند 👠", "name_en": "Heels 👠", "price": 280, "emoji": "👠", "color": (255, 0, 0)},
        "sandals":   {"name_fa": "صندل 🩴", "name_en": "Sandals 🩴", "price": 90, "emoji": "🩴", "color": (210, 180, 140)},
    },
    "socks": {
        "basic_sock":  {"name_fa": "جوراب ساده 🧦", "name_en": "Basic Socks 🧦", "price": 30, "emoji": "🧦", "color": (200, 200, 200)},
        "fancy_sock":  {"name_fa": "جوراب فانتزی 🧦", "name_en": "Fancy Socks 🧦", "price": 60, "emoji": "🧦", "color": (138, 43, 226)},
        "sport_sock":  {"name_fa": "جوراب ورزشی 🧦", "name_en": "Sport Socks 🧦", "price": 50, "emoji": "🧦", "color": (0, 128, 0)},
    },
    "rings": {
        "ring":        {"name_fa": "حلقه ساده 💍", "name_en": "Simple Ring 💍", "price": 200, "emoji": "💍", "color": (192, 192, 192)},
        "gold_ring":   {"name_fa": "حلقه طلا 💍", "name_en": "Gold Ring 💍", "price": 500, "emoji": "💍", "color": (255, 215, 0)},
        "diamond_ring": {"name_fa": "حلقه الماس 💎", "name_en": "Diamond Ring 💎", "price": 800, "emoji": "💎", "color": (185, 242, 255)},
    },
}

CATEGORY_NAMES = {
    "fa": {"clothes": "👕 لباس", "accessories": "⌚ اکسسوری", "shoes": "👟 کفش", "socks": "🧦 جوراب", "rings": "💍 حلقه"},
    "en": {"clothes": "👕 Clothes", "accessories": "⌚ Accessories", "shoes": "👟 Shoes", "socks": "🧦 Socks", "rings": "💍 Rings"},
}

# ---------- Image helpers ----------
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


def _render_shop_image(category: str, lang: str) -> io.BytesIO:
    items = SHOP_ITEMS[category]
    cat_name = CATEGORY_NAMES[lang][category]

    font = _get_font(16)
    font_title = _get_font(22)
    font_emoji = _get_font(28)
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 420
    H = 60 + len(items) * (item_h + 10) + pad

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    title = f"🛒 {cat_name}"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 14), title, fill=TITLE_COLOR, font=font_title)

    y = 55
    for item_id, info in items.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = info["price"]
        color = info["color"]

        # Item box
        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)

        # Color swatch
        draw.rounded_rectangle([pad + 10, y + 10, pad + 50, y + item_h - 10], radius=6, fill=color)

        # Name
        draw.text((pad + 62, y + 8), name, fill=TEXT_COLOR, font=font)

        # Price
        price_text = f"{price}$"
        draw.text((pad + 62, y + 32), price_text, fill=PRICE_COLOR, font=font_price)

        # ID
        id_text = f"/{item_id}" if lang == "en" else f"/{item_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_item_image(item_id: str, info: dict, lang: str) -> io.BytesIO:
    """Render a card for a single purchased item."""
    name = info["name_fa"] if lang == "fa" else info["name_en"]
    color = info["color"]

    W, H = 300, 200
    font = _get_font(18)
    font_big = _get_font(40)
    font_sm = _get_font(14)

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Colored circle as item representation
    cx, cy = W // 2, 80
    draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=color, outline=(255, 255, 255), width=3)

    # Emoji in center
    etb = draw.textbbox((0, 0), info["emoji"], font=font_big)
    ew = etb[2] - etb[0]
    draw.text((cx - ew // 2, cy - 20), info["emoji"], font=font_big)

    # Name
    ntb = draw.textbbox((0, 0), name, font=font)
    draw.text(((W - ntb[2] + ntb[0]) // 2, 140), name, fill=TEXT_COLOR, font=font)

    # Purchased label
    label = "✅ خریداری شد!" if lang == "fa" else "✅ Purchased!"
    ltb = draw.textbbox((0, 0), label, font=font_sm)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 170), label, fill=PRICE_COLOR, font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------- Find item across all categories ----------
def _find_item(item_id: str):
    """Returns (category, item_id, info) or None."""
    for cat, items in SHOP_ITEMS.items():
        if item_id in items:
            return cat, item_id, items[item_id]
    return None


# ---------- /shop command ----------
async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    args = context.args if context.args else []

    # /shop → show categories
    if not args:
        buttons = []
        for cat_key, cat_name in CATEGORY_NAMES[lang].items():
            buttons.append([InlineKeyboardButton(cat_name, callback_data=f"shop_cat:{cat_key}")])
        text = s["shop_welcome"]
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    # /shop <category> → show items image
    cat = args[0].lower()
    if cat in SHOP_ITEMS:
        buf = _render_shop_image(cat, lang)
        usage = s["shop_buy_usage"]
        await update.message.reply_photo(photo=buf, caption=usage)
        return

    await update.message.reply_text(s["shop_usage"], parse_mode="Markdown")


# ---------- Shop category callback ----------
async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("shop_cat:"):
        cat = data.split(":", 1)[1]
        chat_id = query.message.chat.id
        lang = get_lang(chat_id)
        s = STRINGS[lang]

        if cat in SHOP_ITEMS:
            buf = _render_shop_image(cat, lang)
            usage = s["shop_buy_usage"]
            await query.message.reply_photo(photo=buf, caption=usage)
        await query.answer()
        return

    await query.answer()


# ---------- /buy command ----------
async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(s["buy_usage"], parse_mode="Markdown")
        return

    item_id = context.args[0].lower()
    result = _find_item(item_id)
    if not result:
        await update.message.reply_text(s["buy_not_found"], parse_mode="Markdown")
        return

    cat, iid, info = result
    price = info["price"]
    bal = get_balance(chat.id, user.id)

    if price > bal:
        await update.message.reply_text(
            s["buy_no_money"].format(price=price, balance=bal), parse_mode="Markdown"
        )
        return

    # Check if already owned (for unique items like rings)
    if has_item(chat.id, user.id, iid):
        await update.message.reply_text(s["buy_already_owned"], parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -price)
    name = info["name_fa"] if lang == "fa" else info["name_en"]
    add_inventory_item(chat.id, user.id, {
        "item_id": iid,
        "category": cat,
        "name": name,
    })

    buf = _render_item_image(iid, info, lang)
    new_bal = get_balance(chat.id, user.id)
    caption = s["buy_success"].format(item=name, price=price, balance=new_bal)
    await update.message.reply_photo(photo=buf, caption=caption)


# ---------- /inventory command ----------
async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    inv = get_inventory(chat.id, user.id)
    if not inv:
        await update.message.reply_text(s["inventory_empty"], parse_mode="Markdown")
        return

    lines = []
    for it in inv:
        lines.append(f"• {it.get('name', it.get('item_id', '?'))}")

    header = s["inventory_header"].format(user=user.first_name or "User")
    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")


# ---------- /gift command ----------
async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text(s["gift_usage"], parse_mode="Markdown")
        return

    item_id = context.args[0].lower()
    target = update.message.reply_to_message.from_user
    if target.id == user.id or target.is_bot:
        await update.message.reply_text(s["gift_usage"], parse_mode="Markdown")
        return

    if not has_item(chat.id, user.id, item_id):
        await update.message.reply_text(s["gift_not_owned"], parse_mode="Markdown")
        return

    # Find item info
    inv = get_inventory(chat.id, user.id)
    item_data = None
    for it in inv:
        if it.get("item_id") == item_id:
            item_data = it
            break

    if not item_data:
        await update.message.reply_text(s["gift_not_owned"], parse_mode="Markdown")
        return

    remove_inventory_item(chat.id, user.id, item_id)
    add_inventory_item(chat.id, target.id, item_data)

    name = item_data.get("name", item_id)
    target_name = target.first_name or "User"
    await update.message.reply_text(
        s["gift_done"].format(item=name, user=target_name),
        parse_mode="Markdown",
    )
