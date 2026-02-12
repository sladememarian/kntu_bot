# ==========================================
# KNTU Bot 25 — Food Shop
# ==========================================

import io
import os
import urllib.request
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    add_inventory_item, has_item,
)
from strings import STRINGS

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


# ---------- Food Catalog ----------
FOODS = {
    "tea":        {"name_fa": "چای", "name_en": "Tea", "price": 12, "icon": "1f375", "color": (34, 139, 34)},
    "coffee":     {"name_fa": "قهوه", "name_en": "Coffee", "price": 18, "icon": "2615", "color": (101, 67, 33)},
    "cookie":     {"name_fa": "کلوچه", "name_en": "Cookie", "price": 22, "icon": "1f36a", "color": (210, 160, 60)},
    "icecream":   {"name_fa": "بستنی", "name_en": "Ice Cream", "price": 25, "icon": "1f366", "color": (255, 192, 203)},
    "donut":      {"name_fa": "دونات", "name_en": "Donut", "price": 28, "icon": "1f369", "color": (255, 130, 170)},
    "popcorn":    {"name_fa": "پاپ‌کورن", "name_en": "Popcorn", "price": 30, "icon": "1f37f", "color": (255, 230, 150)},
    "fries":      {"name_fa": "سیب‌زمینی", "name_en": "Fries", "price": 32, "icon": "1f35f", "color": (255, 200, 50)},
    "chocolate":  {"name_fa": "شکلات", "name_en": "Chocolate", "price": 35, "icon": "1f36b", "color": (101, 50, 20)},
    "burger":     {"name_fa": "برگر", "name_en": "Burger", "price": 38, "icon": "1f354", "color": (180, 120, 60)},
    "hotdog":     {"name_fa": "هات‌داگ", "name_en": "Hot Dog", "price": 36, "icon": "1f32d", "color": (200, 100, 50)},
    "pizza":      {"name_fa": "پیتزا", "name_en": "Pizza", "price": 42, "icon": "1f355", "color": (255, 165, 0)},
    "taco":       {"name_fa": "تاکو", "name_en": "Taco", "price": 45, "icon": "1f32e", "color": (200, 150, 50)},
    "ramen":      {"name_fa": "رامن", "name_en": "Ramen", "price": 48, "icon": "1f35c", "color": (255, 200, 50)},
    "cake":       {"name_fa": "کیک", "name_en": "Cake", "price": 50, "icon": "1f382", "color": (255, 105, 180)},
    "kebab":      {"name_fa": "کباب", "name_en": "Kebab", "price": 55, "icon": "1f362", "color": (139, 69, 19)},
    "sushi":      {"name_fa": "سوشی", "name_en": "Sushi", "price": 65, "icon": "1f363", "color": (255, 100, 100)},
    "steak":      {"name_fa": "استیک", "name_en": "Steak", "price": 90, "icon": "1f969", "color": (178, 34, 34)},
    "lobster":    {"name_fa": "لابستر", "name_en": "Lobster", "price": 120, "icon": "1f99e", "color": (220, 50, 50)},
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


def _render_foodshop_image(lang):
    font = _get_font(16)
    font_title = _get_font(22)
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 440
    H = 60 + len(FOODS) * (item_h + 10) + pad

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    title = "فودشاپ" if lang == "fa" else "Food Shop"
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=TITLE_COLOR, font=font_title)

    y = 58
    for food_id, info in FOODS.items():
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

        id_text = f"/buyfood {food_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_food_card(food_id, info, lang):
    name = info["name_fa"] if lang == "fa" else info["name_en"]

    W, H = 300, 220
    font = _get_font(18)
    font_sm = _get_font(14)

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, 85
    draw.ellipse([cx - 48, cy - 48, cx + 48, cy + 48],
                 fill=info["color"], outline=(255, 255, 255), width=3)

    icon_img = _download_icon(info["icon"], 60)
    if icon_img:
        img.paste(icon_img, (cx - 30, cy - 30), icon_img)

    ntb = draw.textbbox((0, 0), name, font=font)
    draw.text(((W - ntb[2] + ntb[0]) // 2, 150), name, fill=TEXT_COLOR, font=font)

    label = "نوش جان!" if lang == "fa" else "Enjoy your meal!"
    ltb = draw.textbbox((0, 0), label, font=font_sm)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 180), label, fill=PRICE_COLOR, font=font_sm)

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def foodshop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    buf = _render_foodshop_image(lang)
    usage = s["foodshop_usage"]
    await update.message.reply_photo(photo=buf, caption=usage)


async def buyfood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(s["buyfood_usage"], parse_mode="Markdown")
        return

    food_id = context.args[0].lower()
    if food_id not in FOODS:
        await update.message.reply_text(s["buyfood_not_found"], parse_mode="Markdown")
        return

    info = FOODS[food_id]
    price = info["price"]
    bal = get_balance(chat.id, user.id)

    if price > bal:
        await update.message.reply_text(
            s["buy_no_money"].format(price=price, balance=bal), parse_mode="Markdown"
        )
        return

    add_balance(chat.id, user.id, -price)
    name = info["name_fa"] if lang == "fa" else info["name_en"]
    add_inventory_item(chat.id, user.id, {
        "item_id": f"food_{food_id}",
        "category": "food",
        "name": name,
    })

    buf = _render_food_card(food_id, info, lang)
    new_bal = get_balance(chat.id, user.id)
    caption = s["buyfood_success"].format(food=name, price=price, balance=new_bal)
    await update.message.reply_photo(photo=buf, caption=caption)
