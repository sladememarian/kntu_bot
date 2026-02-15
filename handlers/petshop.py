# ==========================================
# KNTU Bot 25 — Pet Shop
# ==========================================

import io
import os
import urllib.request
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    get_inventory, add_inventory_item, has_item,
    get_purchase_counts, record_purchase,
)
from strings import STRINGS


# ── Inflation / Supply-Demand ──
_INFLATION_STEP = 15
_INFLATION_DIVISOR = 5
_MAX_MULTIPLIER = 3.0


def _dynamic_price(base: int, item_id: str, chat_id: int) -> int:
    counts = get_purchase_counts(chat_id)
    bought = counts.get(item_id, 0)
    multiplier = 1.0 + (bought / _INFLATION_DIVISOR) * (_INFLATION_STEP / 100)
    multiplier = min(multiplier, _MAX_MULTIPLIER)
    return max(base, int(base * multiplier))

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


# ---------- Pet Catalog ----------
PETS = {
    "fish":     {"name_fa": "ماهی", "name_en": "Fish", "price": 50, "icon": "1f41f", "color": (0, 150, 255)},
    "hamster":  {"name_fa": "همستر", "name_en": "Hamster", "price": 80, "icon": "1f439", "color": (230, 190, 138)},
    "turtle":   {"name_fa": "لاک‌پشت", "name_en": "Turtle", "price": 100, "icon": "1f422", "color": (34, 139, 34)},
    "rabbit":   {"name_fa": "خرگوش", "name_en": "Rabbit", "price": 120, "icon": "1f430", "color": (255, 200, 200)},
    "cat":      {"name_fa": "گربه", "name_en": "Cat", "price": 150, "icon": "1f431", "color": (255, 165, 0)},
    "dog":      {"name_fa": "سگ", "name_en": "Dog", "price": 180, "icon": "1f436", "color": (139, 90, 43)},
    "parrot":   {"name_fa": "طوطی", "name_en": "Parrot", "price": 200, "icon": "1f99c", "color": (0, 200, 0)},
    "fox":      {"name_fa": "روباه", "name_en": "Fox", "price": 250, "icon": "1f98a", "color": (255, 140, 0)},
    "snake":    {"name_fa": "مار", "name_en": "Snake", "price": 280, "icon": "1f40d", "color": (50, 150, 50)},
    "owl":      {"name_fa": "جغد", "name_en": "Owl", "price": 320, "icon": "1f989", "color": (139, 119, 101)},
    "penguin":  {"name_fa": "پنگوئن", "name_en": "Penguin", "price": 350, "icon": "1f427", "color": (30, 30, 30)},
    "panda":    {"name_fa": "پاندا", "name_en": "Panda", "price": 450, "icon": "1f43c", "color": (240, 240, 240)},
    "horse":    {"name_fa": "اسب", "name_en": "Horse", "price": 500, "icon": "1f434", "color": (139, 90, 43)},
    "unicorn":  {"name_fa": "تک‌شاخ", "name_en": "Unicorn", "price": 700, "icon": "1f984", "color": (200, 162, 255)},
    "dragon":   {"name_fa": "اژدها", "name_en": "Dragon", "price": 1000, "icon": "1f409", "color": (200, 0, 50)},
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


def _render_petshop_image(lang):
    font = _get_font(16)
    font_title = _get_font(22)
    font_price = _get_font(14)

    item_h = 60
    pad = 20
    W = 440
    H = 60 + len(PETS) * (item_h + 10) + pad

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    title = "پت‌شاپ" if lang == "fa" else "Pet Shop"
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=TITLE_COLOR, font=font_title)

    y = 58
    for pet_id, info in PETS.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = info["price"]

        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)

        icon_img = _download_icon(info["icon"], 40)
        if icon_img:
            img.paste(icon_img, (pad + 10, y + 10), icon_img)
        else:
            draw.ellipse([pad + 10, y + 10, pad + 50, y + item_h - 10], fill=info["color"])

        draw.text((pad + 60, y + 8), name, fill=TEXT_COLOR, font=font)
        draw.text((pad + 60, y + 32), f"{price}K", fill=PRICE_COLOR, font=font_price)

        id_text = f"/buypet {pet_id}"
        ptb = draw.textbbox((0, 0), id_text, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 10, y + 32), id_text, fill=(150, 150, 170), font=font_price)

        y += item_h + 10

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_pet_card(pet_id, info, lang):
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

    label = "حیوان جدیدت مبارک!" if lang == "fa" else "New pet acquired!"
    ltb = draw.textbbox((0, 0), label, font=font_sm)
    draw.text(((W - ltb[2] + ltb[0]) // 2, 180), label, fill=PRICE_COLOR, font=font_sm)

    out = Image.new("RGB", img.size, BG_COLOR)
    out.paste(img, mask=img.split()[3])
    buf = io.BytesIO()
    out.save(buf, format="PNG")
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
    price = _dynamic_price(info["price"], f"pet_{pet_id}", chat.id)
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
    record_purchase(chat.id, f"pet_{pet_id}")
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
