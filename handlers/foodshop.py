# ==========================================
# KNTU Bot 25 — Food Shop
# ==========================================

import io
import os
import random
import urllib.request
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    add_inventory_item, has_item,
    get_inventory, remove_inventory_item,
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
        draw.text((pad + 60, y + 32), f"{price}K", fill=PRICE_COLOR, font=font_price)

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
    price = _dynamic_price(info["price"], food_id, chat.id)
    bal = get_balance(chat.id, user.id)

    if price > bal:
        await update.message.reply_text(
            s["buy_no_money"].format(price=price, balance=bal), parse_mode="Markdown"
        )
        return

    add_balance(chat.id, user.id, -price)
    record_purchase(chat.id, food_id)
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


# ════════════════════════════════════════════════════════════
# /eat — consume a food item from inventory (free for everyone)
# ════════════════════════════════════════════════════════════

_EAT_MSGS_FA = [
    "😋 *{user}* با ولع {food} رو خورد! نووووش جان! 🍽️",
    "🤤 *{user}* یه گاز بزرگ از {food} زد! عجب طعمی! 😍",
    "😆 *{user}* تا ته {food} رو بلعید! حتی بشقاب رو هم لیسید! 👅",
    "🍴 *{user}* آروم نشست و {food} رو مزه مزه کرد... عالی بود! ✨",
    "😤 *{user}* با خشم {food} رو خورد! گرسنگی آدمو عصبی می‌کنه! 🔥",
    "🤩 *{user}* چشماش برق زد وقتی {food} رو دید و یه لقمه‌ای زد! 💫",
    "🥴 *{user}* اینقدر {food} خوشمزه بود که چشماش چپ شد! 😵‍💫",
    "😎 *{user}* مثل آدم‌های کلاس بالا {food} خورد! با کارد و چنگال! 🍽️✨",
]

_EAT_MSGS_EN = [
    "😋 *{user}* devoured the {food}! Bon appétit! 🍽️",
    "🤤 *{user}* took a huge bite of {food}! What a flavor! 😍",
    "😆 *{user}* inhaled the {food}! Even licked the plate! 👅",
    "🍴 *{user}* sat down and savored the {food}... perfection! ✨",
    "😤 *{user}* angrily ate the {food}! Hunger makes you mad! 🔥",
    "🤩 *{user}*'s eyes lit up seeing the {food} and took a big bite! 💫",
    "🥴 *{user}* — the {food} was SO good their eyes crossed! 😵‍💫",
    "😎 *{user}* ate the {food} with class! Knife and fork! 🍽️✨",
]


async def eat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    user = update.effective_user

    if not context.args:
        if lang == "fa":
            await update.message.reply_text(
                "🍽️ *خوردن*\n\nاستفاده: `/eat [غذا]`\n"
                "مثال: `/eat burger`\n\n"
                "غذا باید توی کوله‌پشتیت باشه! از /foodshop بخر 🛒",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "🍽️ *Eat*\n\nUsage: `/eat [food]`\n"
                "Example: `/eat burger`\n\n"
                "Food must be in your inventory! Buy from /foodshop 🛒",
                parse_mode="Markdown")
        return

    item_key = context.args[0].lower()
    inv = get_inventory(chat.id, user.id)

    # Find a matching food item
    found = None
    for it in inv:
        iid = it.get("item_id", "")
        if iid == f"food_{item_key}" or iid == item_key:
            found = it
            break
    # Also try matching by name
    if not found:
        for it in inv:
            if it.get("category") == "food" and item_key in it.get("name", "").lower():
                found = it
                break

    if not found:
        if lang == "fa":
            await update.message.reply_text(
                f"❌ *{item_key}* توی کوله‌پشتیت نیست!\nاول از /foodshop بخر 🛒",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"❌ *{item_key}* is not in your inventory!\nBuy from /foodshop first 🛒",
                parse_mode="Markdown")
        return

    remove_inventory_item(chat.id, user.id, found["item_id"])
    name = found.get("name", item_key)
    user_name = user.first_name or "User"

    if lang == "fa":
        msg = random.choice(_EAT_MSGS_FA).format(user=user_name, food=name)
    else:
        msg = random.choice(_EAT_MSGS_EN).format(user=user_name, food=name)

    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# /drink — consume a drink from inventory (free for everyone)
# ════════════════════════════════════════════════════════════

_DRINK_MSGS_FA = [
    "🥤 *{user}* یه قلپ بزرگ از {drink} خورد! آااه! 😌",
    "😋 *{user}* تا ته {drink} رو سر کشید! تشنگی رفت! 💧",
    "🤤 *{user}* آروم {drink} رو نوشید و لبخند زد... عالی! 😊",
    "😆 *{user}* با عجله {drink} رو خورد و ریخت رو لباسش! 😂💦",
    "🍹 *{user}* یه نی انداخت توی {drink} و شروع کرد! فیس فیس! 🥤",
    "😎 *{user}* مثل فیلم‌ها {drink} رو بالا گرفت و یه نفس خورد! 🎬",
    "🥴 *{user}* اینقدر {drink} خوشمزه بود که نتونست متوقف بشه! 🔄",
    "🤩 *{user}* چشماش گرد شد وقتی {drink} رو مزه کرد! واو! ✨",
]

_DRINK_MSGS_EN = [
    "🥤 *{user}* took a big gulp of {drink}! Aahh! 😌",
    "😋 *{user}* chugged the {drink}! Thirst quenched! 💧",
    "🤤 *{user}* sipped the {drink} slowly and smiled... perfect! 😊",
    "😆 *{user}* drank the {drink} too fast and spilled on their shirt! 😂💦",
    "🍹 *{user}* dropped a straw in the {drink} and started sipping! 🥤",
    "😎 *{user}* raised the {drink} like in the movies and chugged it! 🎬",
    "🥴 *{user}* — the {drink} was so good they couldn't stop! 🔄",
    "🤩 *{user}*'s eyes went wide tasting the {drink}! Wow! ✨",
]


async def drink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    user = update.effective_user

    if not context.args:
        if lang == "fa":
            await update.message.reply_text(
                "🥤 *نوشیدن*\n\nاستفاده: `/drink [نوشیدنی]`\n"
                "مثال: `/drink beer` یا `/drink tea`\n\n"
                "نوشیدنی باید توی کوله‌پشتیت باشه!\n"
                "از /bar یا /foodshop بخر 🛒",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "🥤 *Drink*\n\nUsage: `/drink [beverage]`\n"
                "Example: `/drink beer` or `/drink tea`\n\n"
                "Drink must be in your inventory!\n"
                "Buy from /bar or /foodshop 🛒",
                parse_mode="Markdown")
        return

    item_key = context.args[0].lower()
    inv = get_inventory(chat.id, user.id)

    # Find a matching drink or drinkable food item
    found = None
    for it in inv:
        iid = it.get("item_id", "")
        if iid == f"drink_{item_key}" or iid == f"food_{item_key}" or iid == item_key:
            found = it
            break
    # Also try matching by name
    if not found:
        for it in inv:
            cat = it.get("category", "")
            if cat in ("drink", "food") and item_key in it.get("name", "").lower():
                found = it
                break

    if not found:
        if lang == "fa":
            await update.message.reply_text(
                f"❌ *{item_key}* توی کوله‌پشتیت نیست!\nاز /bar یا /foodshop بخر 🛒",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"❌ *{item_key}* is not in your inventory!\nBuy from /bar or /foodshop 🛒",
                parse_mode="Markdown")
        return

    remove_inventory_item(chat.id, user.id, found["item_id"])
    name = found.get("name", item_key)
    user_name = user.first_name or "User"

    if lang == "fa":
        msg = random.choice(_DRINK_MSGS_FA).format(user=user_name, drink=name)
    else:
        msg = random.choice(_DRINK_MSGS_EN).format(user=user_name, drink=name)

    await update.message.reply_text(msg, parse_mode="Markdown")
