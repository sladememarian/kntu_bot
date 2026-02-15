# ==========================================
# KNTU Bot 25 — Shop System (Clothes, Accessories, Shoes, Socks, Rings)
# ==========================================

import io
import os
import urllib.request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    get_inventory, add_inventory_item, remove_inventory_item, has_item,
    get_purchase_counts, record_purchase,
)
from strings import STRINGS


# ── Inflation / Supply-Demand ──
_INFLATION_STEP = 15      # each purchase adds this many % points (spread over buys)
_INFLATION_DIVISOR = 5    # purchases needed to add one full step
_MAX_MULTIPLIER = 3.0     # price can at most triple


def _dynamic_price(base: int, item_id: str, chat_id: int) -> int:
    """Return inflation-adjusted price based on demand."""
    counts = get_purchase_counts(chat_id)
    bought = counts.get(item_id, 0)
    multiplier = 1.0 + (bought / _INFLATION_DIVISOR) * (_INFLATION_STEP / 100)
    multiplier = min(multiplier, _MAX_MULTIPLIER)
    return max(base, int(base * multiplier))

# ---------- Icon cache & downloader ----------
_icon_cache: dict = {}


def _download_icon(codepoint: str, size: int = 40):
    """Download a Twemoji PNG and cache it. Falls back to None."""
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


# ---------- Shop Catalog ----------
SHOP_ITEMS = {
    "clothes": {
        "tshirt":    {"name_fa": "تی‌شرت", "name_en": "T-Shirt", "price": 80, "icon": "1f455", "color": (70, 130, 180)},
        "jeans":     {"name_fa": "شلوار جین", "name_en": "Jeans", "price": 100, "icon": "1f456", "color": (30, 80, 160)},
        "hoodie":    {"name_fa": "هودی", "name_en": "Hoodie", "price": 150, "icon": "1f9e5", "color": (139, 69, 19)},
        "kimono":    {"name_fa": "کیمونو", "name_en": "Kimono", "price": 180, "icon": "1f458", "color": (178, 34, 34)},
        "dress":     {"name_fa": "لباس مجلسی", "name_en": "Dress", "price": 220, "icon": "1f457", "color": (220, 20, 60)},
        "jacket":    {"name_fa": "کاپشن", "name_en": "Jacket", "price": 280, "icon": "1f9e5", "color": (50, 50, 50)},
        "lab_coat":  {"name_fa": "روپوش آزمایشگاه", "name_en": "Lab Coat", "price": 320, "icon": "1f97c", "color": (240, 240, 240)},
        "suit":      {"name_fa": "کت و شلوار", "name_en": "Suit", "price": 450, "icon": "1f454", "color": (25, 25, 112)},
    },
    "accessories": {
        "scarf":     {"name_fa": "شال", "name_en": "Scarf", "price": 70, "icon": "1f9e3", "color": (200, 50, 50)},
        "cap":       {"name_fa": "کلاه کپ", "name_en": "Cap", "price": 85, "icon": "1f9e2", "color": (30, 100, 200)},
        "glasses":   {"name_fa": "عینک آفتابی", "name_en": "Sunglasses", "price": 120, "icon": "1f576-fe0f", "color": (30, 30, 30)},
        "bracelet":  {"name_fa": "دستبند", "name_en": "Bracelet", "price": 140, "icon": "1f4ff", "color": (192, 192, 192)},
        "necklace":  {"name_fa": "گردنبند", "name_en": "Necklace", "price": 190, "icon": "1f4ff", "color": (255, 215, 0)},
        "watch":     {"name_fa": "ساعت", "name_en": "Watch", "price": 230, "icon": "231a", "color": (218, 165, 32)},
        "tophat":    {"name_fa": "کلاه شعبده‌باز", "name_en": "Top Hat", "price": 300, "icon": "1f3a9", "color": (40, 40, 40)},
        "crown":     {"name_fa": "تاج پادشاهی", "name_en": "Royal Crown", "price": 800, "icon": "1f451", "color": (255, 200, 0)},
    },
    "shoes": {
        "sandals":   {"name_fa": "صندل", "name_en": "Sandals", "price": 70, "icon": "1fa74", "color": (210, 180, 140)},
        "flats":     {"name_fa": "کفش تخت", "name_en": "Ballet Flats", "price": 110, "icon": "1f97f", "color": (200, 150, 100)},
        "sneakers":  {"name_fa": "کتونی", "name_en": "Sneakers", "price": 160, "icon": "1f45f", "color": (255, 255, 255)},
        "loafers":   {"name_fa": "کفش رسمی", "name_en": "Loafers", "price": 190, "icon": "1f45e", "color": (100, 60, 30)},
        "boots":     {"name_fa": "بوت", "name_en": "Boots", "price": 230, "icon": "1f97e", "color": (101, 67, 33)},
        "heels":     {"name_fa": "پاشنه بلند", "name_en": "High Heels", "price": 280, "icon": "1f460", "color": (255, 0, 0)},
        "skates":    {"name_fa": "اسکیت یخ", "name_en": "Ice Skates", "price": 350, "icon": "26f8-fe0f", "color": (100, 180, 255)},
    },
    "socks": {
        "basic_sock":  {"name_fa": "جوراب ساده", "name_en": "Basic Socks", "price": 25, "icon": "1f9e6", "color": (200, 200, 200)},
        "sport_sock":  {"name_fa": "جوراب ورزشی", "name_en": "Sport Socks", "price": 45, "icon": "1f9e6", "color": (0, 128, 0)},
        "fancy_sock":  {"name_fa": "جوراب فانتزی", "name_en": "Fancy Socks", "price": 65, "icon": "1f9e6", "color": (138, 43, 226)},
        "wool_sock":   {"name_fa": "جوراب پشمی", "name_en": "Wool Socks", "price": 85, "icon": "1f9e6", "color": (180, 120, 60)},
        "knee_sock":   {"name_fa": "جوراب ساق‌بلند", "name_en": "Knee Socks", "price": 120, "icon": "1f9e6", "color": (60, 60, 60)},
    },
    "rings": {
        "ring":          {"name_fa": "حلقه ساده", "name_en": "Simple Ring", "price": 200, "icon": "1f48d", "color": (192, 192, 192)},
        "gold_ring":     {"name_fa": "حلقه طلا", "name_en": "Gold Ring", "price": 500, "icon": "1f48d", "color": (255, 215, 0)},
        "emerald_ring":  {"name_fa": "حلقه زمرد", "name_en": "Emerald Ring", "price": 600, "icon": "1f49a", "color": (0, 180, 80)},
        "ruby_ring":     {"name_fa": "حلقه یاقوت", "name_en": "Ruby Ring", "price": 700, "icon": "2764-fe0f", "color": (200, 20, 20)},
        "diamond_ring":  {"name_fa": "حلقه الماس", "name_en": "Diamond Ring", "price": 900, "icon": "1f48e", "color": (185, 242, 255)},
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
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 440
    H = 60 + len(items) * (item_h + 10) + pad

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    tb = draw.textbbox((0, 0), cat_name, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), cat_name, fill=TITLE_COLOR, font=font_title)

    y = 58
    for item_id, info in items.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = info["price"]

        # Item box
        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)

        # Icon from Twemoji (fallback: colored swatch)
        icon_img = _download_icon(info["icon"], 40)
        if icon_img:
            img.paste(icon_img, (pad + 10, y + 10), icon_img)
        else:
            draw.rounded_rectangle(
                [pad + 10, y + 10, pad + 50, y + item_h - 10],
                radius=6, fill=info["color"],
            )

        # Name
        draw.text((pad + 60, y + 8), name, fill=TEXT_COLOR, font=font)

        # Price
        draw.text((pad + 60, y + 32), f"{price}K", fill=PRICE_COLOR, font=font_price)

        # Buy command hint
        id_text = f"/buy {item_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_item_image(item_id: str, info: dict, lang: str) -> io.BytesIO:
    """Render a card for a single purchased item."""
    name = info["name_fa"] if lang == "fa" else info["name_en"]

    W, H = 300, 220
    font = _get_font(18)
    font_sm = _get_font(14)

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # Decorative circle background
    cx, cy = W // 2, 85
    draw.ellipse([cx - 48, cy - 48, cx + 48, cy + 48],
                 fill=info["color"], outline=(255, 255, 255), width=3)

    # Twemoji icon in center
    icon_img = _download_icon(info["icon"], 60)
    if icon_img:
        img.paste(icon_img, (cx - 30, cy - 30), icon_img)

    # Name
    ntb = draw.textbbox((0, 0), name, font=font)
    draw.text(((W - ntb[2] + ntb[0]) // 2, 150), name, fill=TEXT_COLOR, font=font)

    # Purchased label
    label = "خریداری شد!" if lang == "fa" else "Purchased!"
    ltb = draw.textbbox((0, 0), label, font=font_sm)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 180), label, fill=PRICE_COLOR, font=font_sm)

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
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
    price = _dynamic_price(info["price"], iid, chat.id)
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
    record_purchase(chat.id, iid)
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
