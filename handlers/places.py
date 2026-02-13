# ==========================================
# KNTU Bot 25 — Places & Date System
# ==========================================

import random
import io
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    get_inventory, add_inventory_item, remove_inventory_item,
    has_item, get_user_name, set_user_name,
)

# ── Constants ──────────────────────────────────────────────
KOLLAR = "کلار $"

BG_COLOR = (30, 30, 46)
BOX_FILL = (69, 71, 90)
TEXT_COLOR = (205, 214, 244)
TITLE_COLOR = (137, 180, 250)
PRICE_COLOR = (166, 227, 161)
ACCENT_COLOR = (249, 226, 175)
RED_COLOR = (243, 139, 168)

# ── Places catalog ─────────────────────────────────────────
PLACES = {
    "restaurant": {
        "name_fa": "رستوران",
        "name_en": "Restaurant",
        "price": 80,
        "emoji": "🍽",
        "vibe_fa": "شام رمانتیک",
        "vibe_en": "romantic dinner",
    },
    "cafe": {
        "name_fa": "کافه",
        "name_en": "Cafe",
        "price": 40,
        "emoji": "☕",
        "vibe_fa": "یه نشست دوستانه",
        "vibe_en": "chill hangout",
    },
    "park": {
        "name_fa": "پارک",
        "name_en": "Park",
        "price": 20,
        "emoji": "🌳",
        "vibe_fa": "قدم زدن تو طبیعت",
        "vibe_en": "walk in nature",
    },
    "cinema": {
        "name_fa": "سینما",
        "name_en": "Cinema",
        "price": 60,
        "emoji": "🎬",
        "vibe_fa": "تماشای فیلم",
        "vibe_en": "watch a movie",
    },
    "beach": {
        "name_fa": "ساحل",
        "name_en": "Beach",
        "price": 50,
        "emoji": "🏖",
        "vibe_fa": "آفتاب و موج",
        "vibe_en": "sun and waves",
    },
    "arcade": {
        "name_fa": "گیم‌نت",
        "name_en": "Arcade",
        "price": 45,
        "emoji": "🕹",
        "vibe_fa": "بازی کردن",
        "vibe_en": "play games",
    },
    "library": {
        "name_fa": "کتابخانه",
        "name_en": "Library",
        "price": 15,
        "emoji": "📚",
        "vibe_fa": "با هم درس خوندن",
        "vibe_en": "study together",
    },
    "gym": {
        "name_fa": "باشگاه",
        "name_en": "Gym",
        "price": 35,
        "emoji": "💪",
        "vibe_fa": "ورزش دونفره",
        "vibe_en": "workout together",
    },
    "mall": {
        "name_fa": "مرکز خرید",
        "name_en": "Mall",
        "price": 55,
        "emoji": "🛍",
        "vibe_fa": "خرید دونفره",
        "vibe_en": "shopping spree",
    },
    "rooftop": {
        "name_fa": "پشت‌بام",
        "name_en": "Rooftop",
        "price": 70,
        "emoji": "🌃",
        "vibe_fa": "ستاره‌بازی",
        "vibe_en": "stargazing",
    },
}

# ── Date outcomes per place ────────────────────────────────
# Each entry: (message_fa, message_en, bonus)
# bonus = 0 means just a fun message, positive = bonus money
DATE_OUTCOMES = {
    "restaurant": [
        ("{u} و {t} رفتن رستوران. گارسون سوپ ریخت رو هردوتاشون! 🍜😂 ولی کلی خندیدن و خوش گذشت!",
         "{u} and {t} went to the restaurant. The waiter spilled soup on them both! 🍜😂 But they laughed it off and had a great time!", 0),
        ("{u} و {t} رفتن رستوران. غذا اونقدر خوشمزه بود که سرآشپز اومد بهشون تخفیف داد! 🧑‍🍳💰",
         "{u} and {t} went to the restaurant. The food was so good the chef gave them a discount! 🧑‍🍳💰", 15),
        ("{u} و {t} رفتن رستوران لاکچری. یه میز کنار پنجره با شمع! 🕯️✨ شب فوق‌العاده‌ای بود.",
         "{u} and {t} went to a fancy restaurant. A candle-lit window table! 🕯️✨ What a magical evening.", 0),
        ("{u} و {t} رفتن رستوران ولی هردو یه غذا سفارش دادن! 😂🍝 هم‌فکری عجیبی بود!",
         "{u} and {t} went to the restaurant but both ordered the exact same dish! 😂🍝 Great minds think alike!", 0),
        ("{u} برای {t} غذا سفارش داد. {t} گفت: «این بهترین غذایی بود که خوردم!» 🥹💕",
         "{u} ordered food for {t}. {t} said: 'This is the best meal I've ever had!' 🥹💕", 10),
        ("{u} و {t} تو رستوران مسابقه غذاخوری گذاشتن! 🏆🍔 برنده یه دسر مجانی گرفت!",
         "{u} and {t} had an eating contest at the restaurant! 🏆🍔 The winner got a free dessert!", 5),
    ],
    "cafe": [
        ("{u} و {t} رفتن کافه. باریستا اسمشون رو اشتباه نوشت! ☕😅 «بوریستا»!",
         "{u} and {t} went to the cafe. The barista misspelled their names! ☕😅 Classic!", 0),
        ("{u} و {t} انقدر تو کافه حرف زدن که نفهمیدن ۴ ساعت گذشت! ⏰😊",
         "{u} and {t} talked so much at the cafe they didn't realize 4 hours passed! ⏰😊", 0),
        ("{u} و {t} تو کافه لاته‌آرت سفارش دادن. روی قهوه شکل قلب بود! ❤️☕",
         "{u} and {t} ordered latte art at the cafe. It had a heart on top! ❤️☕", 0),
        ("{u} برای {t} کیک شکلاتی سفارش داد. {t} ذوق‌مرگ شد! 🎂🥰",
         "{u} surprised {t} with a chocolate cake. {t} was thrilled! 🎂🥰", 5),
        ("{u} و {t} رفتن کافه و یه مسابقه تریویا بود! جایزه بردن! 🏅🧠",
         "{u} and {t} went to a cafe trivia night and won a prize! 🏅🧠", 10),
    ],
    "park": [
        ("{u} و {t} رفتن پارک قدم بزنن. یه سنجاب اومد نشست رو شونه {t}! 🐿️😱",
         "{u} and {t} went for a walk. A squirrel sat on {t}'s shoulder! 🐿️😱", 0),
        ("{u} و {t} تو پارک بستنی خوردن و تاب بازی کردن! حال داد! 🍦🎢",
         "{u} and {t} ate ice cream and played on swings at the park! 🍦🎢", 0),
        ("{u} و {t} تو پارک گل چیدن! 🌸 یه دسته‌گل قشنگ درست شد.",
         "{u} and {t} picked flowers in the park! 🌸 Made a beautiful bouquet.", 0),
        ("{u} و {t} رفتن پارک و یه سکه تو چمن پیدا کردن! خوش‌شانسی! 🍀💰",
         "{u} and {t} found a lucky coin in the grass! 🍀💰", 8),
        ("{u} و {t} رو نیمکت پارک نشستن و غروب رو تماشا کردن. 🌅 لحظه‌ای بی‌نظیر.",
         "{u} and {t} sat on a park bench and watched the sunset. 🌅 A perfect moment.", 0),
    ],
    "cinema": [
        ("{u} و {t} رفتن سینما. فیلم ترسناک بود و {t} دست {u} رو فشار داد! 😱👫",
         "{u} and {t} went to the movies. It was scary and {t} grabbed {u}'s hand! 😱👫", 0),
        ("{u} و {t} رفتن سینما. پاپ‌کورن تموم شد و سر آخرین مشت دعواشون شد! 🍿😂",
         "{u} and {t} went to the movies. They fought over the last handful of popcorn! 🍿😂", 0),
        ("{u} و {t} رفتن سینما و هردو آخر فیلم گریه کردن! 😢🎬 بعدش خندیدن بهم.",
         "{u} and {t} both cried at the end of the movie! 😢🎬 Then laughed at each other.", 0),
        ("{u} و {t} رفتن سینما ولی فیلم اونقدر بد بود که زودتر رفتن بیرون! 🚪😂 ولی بیرون کلی خندیدن!",
         "{u} and {t} went to the movies but it was so bad they left early! 🚪😂 But had fun laughing outside!", 0),
        ("{u} و {t} تو سینما برنده قرعه‌کشی شدن! بلیط مجانی بعدی مال شماست! 🎫✨",
         "{u} and {t} won a raffle at the cinema! Free tickets next time! 🎫✨", 12),
    ],
    "beach": [
        ("{u} و {t} رفتن ساحل. {u} قلعه شنی ساخت ولی موج خرابش کرد! 🏖️😭🌊",
         "{u} and {t} went to the beach. {u} built a sandcastle but a wave destroyed it! 🏖️😭🌊", 0),
        ("{u} و {t} تو ساحل صدف جمع کردن. یه صدف خیلی خاص پیدا کردن! 🐚✨",
         "{u} and {t} collected shells at the beach. Found a super rare one! 🐚✨", 5),
        ("{u} و {t} تو ساحل آفتاب گرفتن. هردو مثل خرچنگ قرمز شدن! 🦞☀️😂",
         "{u} and {t} sunbathed at the beach. Both turned red like lobsters! 🦞☀️😂", 0),
        ("{u} و {t} مسابقه شنا گذاشتن! {u} برد... ولی فقط چون {t} خوابش برد! 🏊😴",
         "{u} and {t} had a swimming race! {u} won... but only because {t} fell asleep! 🏊😴", 0),
        ("{u} و {t} رفتن ساحل و یه ستاره‌دریایی پیدا کردن! خیلی خوشگل بود! ⭐🌊",
         "{u} and {t} found a starfish at the beach! So beautiful! ⭐🌊", 0),
    ],
    "arcade": [
        ("{u} و {t} رفتن گیم‌نت. {t} تو بازی مسابقه‌ای همه رکوردها رو زد! 🕹️🏆",
         "{u} and {t} went to the arcade. {t} broke all the racing game records! 🕹️🏆", 0),
        ("{u} و {t} مسابقه ایرهاکی گذاشتن! خیلی حساس شد! 🏒🔥",
         "{u} and {t} played air hockey! It got super intense! 🏒🔥", 0),
        ("{u} و {t} تو گیم‌نت جایزه بردن! یه خرس عروسکی بزرگ! 🧸🎯",
         "{u} and {t} won a prize at the arcade! A giant teddy bear! 🧸🎯", 7),
        ("{u} و {t} انقدر بازی کردن که سکه‌هاشون تموم شد! 🪙😅 ولی کلی خوش گذشت!",
         "{u} and {t} played so much they ran out of tokens! 🪙😅 But had a blast!", 0),
        ("{u} و {t} رفتن گیم‌نت و با هم تیمی بازی کردن. بهترین تیم تاریخ! 🎮👊",
         "{u} and {t} went to the arcade and played co-op. Best team ever! 🎮👊", 0),
        ("{u} تو بازی بوکس {t} رو برد! 🥊😤 بعدش بهش بستنی خرید.",
         "{u} beat {t} at the boxing game! 🥊😤 Then bought them ice cream.", 0),
    ],
    "library": [
        ("{u} و {t} رفتن کتابخونه. {t} یه کتاب باز کرد و یه یادداشت عاشقانه قدیمی توش بود! 📖💌",
         "{u} and {t} went to the library. {t} opened a book and found an old love note inside! 📖💌", 0),
        ("{u} و {t} رفتن کتابخونه ولی بجای درس خوندن کلی حرف زدن و کتابدار بهشون تذکر داد! 🤫😂",
         "{u} and {t} went to the library but talked so much the librarian shushed them! 🤫😂", 0),
        ("{u} و {t} باهم مسابقه کتاب‌خوانی گذاشتن! {u} سه صفحه خوند و خوابش برد! 📚😴",
         "{u} and {t} had a reading race! {u} read three pages and fell asleep! 📚😴", 0),
        ("{u} و {t} تو کتابخونه یه کتاب کمیاب پیدا کردن و از کتابدار جایزه گرفتن! 📕🏅",
         "{u} and {t} found a rare book at the library and got a reward from the librarian! 📕🏅", 6),
        ("{u} و {t} تو کتابخونه کنار هم نشستن و آروم درس خوندن. 📖✨ صلح و آرامش.",
         "{u} and {t} sat together in the library and studied peacefully. 📖✨ Pure serenity.", 0),
    ],
    "gym": [
        ("{u} و {t} رفتن باشگاه. {u} خواست خودنمایی کنه ولی وزنه رو نتونست بلند کنه! 🏋️😅",
         "{u} and {t} went to the gym. {u} tried to show off but couldn't lift the weight! 🏋️😅", 0),
        ("{u} و {t} باهم مسابقه دوی تردمیل گذاشتن! {t} برد! 🏃💨",
         "{u} and {t} had a treadmill race! {t} won! 🏃💨", 0),
        ("{u} و {t} رفتن باشگاه و بعدش انقدر گرسنه بودن که دوتا پیتزا خوردن! 🍕💪",
         "{u} and {t} worked out at the gym and were so hungry they ate two whole pizzas after! 🍕💪", 0),
        ("{u} و {t} تو باشگاه با مربی آشنا شدن و یه جلسه رایگان گرفتن! 🎽🆓",
         "{u} and {t} met a trainer at the gym and got a free session! 🎽🆓", 8),
        ("{u} و {t} یوگا کردن. {u} تو حرکت درخت افتاد! 🧘🌳😂",
         "{u} and {t} did yoga. {u} fell over during tree pose! 🧘🌳😂", 0),
    ],
    "mall": [
        ("{u} و {t} رفتن مرکز خرید. {t} ده تا لباس امتحان کرد و هیچکدوم رو نخرید! 🛍️😂",
         "{u} and {t} went to the mall. {t} tried on 10 outfits and bought none! 🛍️😂", 0),
        ("{u} و {t} تو مرکز خرید یه فروشگاه جدید کشف کردن و هردو عاشقش شدن! 🏬✨",
         "{u} and {t} discovered a new store at the mall and both loved it! 🏬✨", 0),
        ("{u} و {t} رفتن مرکز خرید و تو پله‌برقی سلفی گرفتن! 📸🤳 عکس خیلی باحال شد!",
         "{u} and {t} took an escalator selfie at the mall! 📸🤳 The photo turned out great!", 0),
        ("{u} و {t} تو مرکز خرید برنده کارت تخفیف شدن! 🎟️💰",
         "{u} and {t} won a discount card at the mall! 🎟️💰", 10),
        ("{u} برای {t} یه هدیه سورپرایزی خرید! 🎁🥺 {t} خیلی خوشحال شد!",
         "{u} bought {t} a surprise gift! 🎁🥺 {t} was so happy!", 0),
        ("{u} و {t} رفتن فودکورت و از هر رستوران یه چیز سفارش دادن! 🍱🌮🍕 مهمونی شکم!",
         "{u} and {t} hit the food court and ordered from every restaurant! 🍱🌮🍕 Feast mode!", 0),
    ],
    "rooftop": [
        ("{u} و {t} رفتن پشت‌بام ستاره‌بازی. {u} ادعا کرد یه ستاره دنباله‌دار دید! 🌠😏",
         "{u} and {t} went stargazing on the rooftop. {u} claimed they saw a shooting star! 🌠😏", 0),
        ("{u} و {t} رو پشت‌بام نشستن و درباره آینده حرف زدن. 🌃💭 شب خیلی قشنگ بود.",
         "{u} and {t} sat on the rooftop and talked about the future. 🌃💭 Beautiful night.", 0),
        ("{u} و {t} از پشت‌بام شهر رو تماشا کردن. چراغ‌ها مثل ستاره بودن! 🏙️✨",
         "{u} and {t} watched the city lights from the rooftop. Like stars! 🏙️✨", 0),
        ("{u} و {t} رو پشت‌بام چایی خوردن و آسمون پر ستاره بود! ☕🌌 معرکه بود!",
         "{u} and {t} sipped tea on the rooftop under a sky full of stars! ☕🌌 Magical!", 5),
        ("{u} و {t} رو پشت‌بام آرزو کردن! {u} آرزو کرد پولدار بشه و پولی ریخت! 💫💰",
         "{u} and {t} made wishes on the rooftop! {u} wished for money and some appeared! 💫💰", 15),
        ("{u} و {t} رو پشت‌بام موزیک گوش دادن و رقصیدن! 🎶💃🕺 همسایه‌ها هم دست زدن!",
         "{u} and {t} played music and danced on the rooftop! 🎶💃🕺 The neighbors clapped!", 0),
    ],
}


# ── Helpers ────────────────────────────────────────────────
def _remember_user(chat_id, user):
    set_user_name(chat_id, user.id,
                  (user.full_name or user.first_name or "User").strip())


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for p in [
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _find_place(query: str):
    """Resolve a place key from user input (id, English name, or Persian name)."""
    q = query.lower().strip()
    for pid, info in PLACES.items():
        if q in (pid, info["name_en"].lower(), info["name_fa"]):
            return pid, info
    return None, None


# ── Image: places menu ─────────────────────────────────────
def _render_places_image(lang: str) -> io.BytesIO:
    font = _get_font(16)
    font_title = _get_font(22)
    font_price = _get_font(14)
    font_sm = _get_font(12)

    item_h = 58
    pad = 20
    W = 460
    H = 60 + len(PLACES) * (item_h + 8) + 30

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    title = "📍 مکان‌ها و قرار" if lang == "fa" else "📍 Places & Dates"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=TITLE_COLOR, font=font_title)

    y = 58
    for pid, info in PLACES.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        vibe = info["vibe_fa"] if lang == "fa" else info["vibe_en"]
        price = info["price"]
        emoji = info["emoji"]

        draw.rounded_rectangle([pad, y, W - pad, y + item_h], radius=10, fill=BOX_FILL)

        # Emoji + name
        draw.text((pad + 12, y + 6), f"{emoji} {name}", fill=TEXT_COLOR, font=font)
        # Vibe text
        draw.text((pad + 12, y + 30), vibe, fill=(150, 150, 170), font=font_sm)
        # Price on right
        price_txt = f"{price}$"
        ptb = draw.textbbox((0, 0), price_txt, font=font_price)
        draw.text((W - pad - (ptb[2] - ptb[0]) - 12, y + 8), price_txt, fill=PRICE_COLOR, font=font_price)
        # Command hint
        cmd_txt = f"/date {pid}"
        ctb = draw.textbbox((0, 0), cmd_txt, font=font_sm)
        draw.text((W - pad - (ctb[2] - ctb[0]) - 12, y + 32), cmd_txt, fill=(120, 120, 140), font=font_sm)

        y += item_h + 8

    # Footer
    foot = "ریپلای کن روی کسی و /date [مکان] بزن!" if lang == "fa" else "Reply to someone and use /date [place]!"
    fb = draw.textbbox((0, 0), foot, font=font_sm)
    draw.text(((W - fb[2] + fb[0]) // 2, H - 22), foot, fill=(130, 130, 150), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Image: date card ───────────────────────────────────────
def _render_date_card(user_name: str, target_name: str, place_info: dict,
                      outcome_text: str, bonus: int, lang: str) -> io.BytesIO:
    font = _get_font(16)
    font_title = _get_font(22)
    font_sm = _get_font(13)
    font_big = _get_font(18)

    W = 460
    H = 320

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    name = place_info["name_fa"] if lang == "fa" else place_info["name_en"]
    emoji = place_info["emoji"]

    # Title bar
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    title = f"{emoji} Date Card {emoji}" if lang == "en" else f"{emoji} کارت قرار {emoji}"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=ACCENT_COLOR, font=font_title)

    # Users + place box
    draw.rounded_rectangle([16, 60, W - 16, 130], radius=10, fill=BOX_FILL)
    line1 = f"❤️  {user_name}  &  {target_name}"
    l1b = draw.textbbox((0, 0), line1, font=font_big)
    draw.text(((W - l1b[2] + l1b[0]) // 2, 68), line1, fill=TITLE_COLOR, font=font_big)

    loc_label = f"{emoji} {name}"
    l2b = draw.textbbox((0, 0), loc_label, font=font)
    draw.text(((W - l2b[2] + l2b[0]) // 2, 100), loc_label, fill=TEXT_COLOR, font=font)

    # Outcome box
    draw.rounded_rectangle([16, 142, W - 16, 260], radius=10, fill=BOX_FILL)
    # Word-wrap the outcome text
    _draw_wrapped(draw, outcome_text, 28, 152, W - 32, font_sm, TEXT_COLOR)

    # Bonus line
    if bonus > 0:
        bonus_txt = f"💰 +{bonus}$ {KOLLAR}" if lang == "en" else f"💰 +{bonus}$ {KOLLAR}"
        btb = draw.textbbox((0, 0), bonus_txt, font=font)
        draw.text(((W - btb[2] + btb[0]) // 2, 270), bonus_txt, fill=PRICE_COLOR, font=font)
    else:
        fun_txt = "💕 Just vibes!" if lang == "en" else "💕 فقط حال خوب!"
        ftb = draw.textbbox((0, 0), fun_txt, font=font)
        draw.text(((W - ftb[2] + ftb[0]) // 2, 270), fun_txt, fill=ACCENT_COLOR, font=font)

    # Footer
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    tsb = draw.textbbox((0, 0), ts, font=font_sm)
    draw.text(((W - tsb[2] + tsb[0]) // 2, H - 22), ts, fill=(100, 100, 120), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _draw_wrapped(draw, text, x, y, max_w, font, color):
    """Simple word-wrap drawer."""
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        tb = draw.textbbox((0, 0), test, font=font)
        if tb[2] - tb[0] > max_w - x * 2:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    for i, line in enumerate(lines[:6]):
        draw.text((x, y + i * 20), line, fill=color, font=font)


# ════════════════════════════════════════════════════════════
# 1. /places — Show all places
# ════════════════════════════════════════════════════════════
async def places_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    buf = _render_places_image(lang)

    if lang == "fa":
        caption = (
            "📍 *مکان‌ها و قرار*\n\n"
            "با ریپلای روی پیام کسی و `/date [مکان]` باهاش قرار بذار!\n\n"
        )
        for pid, info in PLACES.items():
            caption += f"{info['emoji']} *{info['name_fa']}* — {info['price']}$ — {info['vibe_fa']}\n"
        caption += f"\n💡 مثال: `/date restaurant`"
    else:
        caption = (
            "📍 *Places & Dates*\n\n"
            "Reply to someone's message and use `/date [place]` to go on a date!\n\n"
        )
        for pid, info in PLACES.items():
            caption += f"{info['emoji']} *{info['name_en']}* — {info['price']}$ — {info['vibe_en']}\n"
        caption += f"\n💡 Example: `/date restaurant`"

    await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 2. /date [place] — Go on a date (reply to someone)
# ════════════════════════════════════════════════════════════
async def date_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    # Must reply to someone
    reply = update.message.reply_to_message
    if not reply or not reply.from_user:
        msg = ("❌ باید روی پیام کسی ریپلای بزنی!\nاستفاده: `/date [مکان]`" if lang == "fa"
               else "❌ You must reply to someone's message!\nUsage: `/date [place]`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    target = reply.from_user
    if target.id == user.id:
        msg = "❌ نمی‌تونی با خودت قرار بذاری! 😅" if lang == "fa" else "❌ You can't date yourself! 😅"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    _remember_user(chat.id, target)

    # Parse place
    args = context.args or []
    if not args:
        available = ", ".join(PLACES.keys())
        msg = (f"❌ مکان رو مشخص کن!\nمکان‌ها: {available}\nمثال: `/date cafe`" if lang == "fa"
               else f"❌ Specify a place!\nPlaces: {available}\nExample: `/date cafe`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    pid, info = _find_place(args[0])
    if not info:
        available = ", ".join(PLACES.keys())
        msg = (f"❌ مکان «{args[0]}» پیدا نشد!\nمکان‌ها: {available}" if lang == "fa"
               else f"❌ Place '{args[0]}' not found!\nPlaces: {available}")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    price = info["price"]
    bal = get_balance(chat.id, user.id)
    if price > bal:
        msg = (f"❌ پول کافی نداری! ({bal}$) — هزینه: {price}$" if lang == "fa"
               else f"❌ Not enough money! ({bal}$) — Cost: {price}$")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Deduct cost
    add_balance(chat.id, user.id, -price)

    # Pick a random outcome
    outcome_fa, outcome_en, bonus = random.choice(DATE_OUTCOMES[pid])
    u_name = (user.full_name or user.first_name or "User").strip()
    t_name = (target.full_name or target.first_name or "User").strip()

    outcome_text = (outcome_fa if lang == "fa" else outcome_en).format(u=u_name, t=t_name)

    # Apply bonus
    if bonus > 0:
        add_balance(chat.id, user.id, bonus)

    new_bal = get_balance(chat.id, user.id)
    place_name = info["name_fa"] if lang == "fa" else info["name_en"]

    # Render card
    buf = _render_date_card(u_name, t_name, info, outcome_text, bonus, lang)

    if lang == "fa":
        caption = (
            f"{info['emoji']} *{u_name}* و *{t_name}* رفتن {place_name}!\n\n"
            f"{outcome_text}\n\n"
        )
        if bonus > 0:
            caption += f"💰 بونوس: *+{bonus}$*\n"
        caption += f"💳 هزینه: *{price}$* | 💰 موجودی: *{new_bal}$* {KOLLAR}"
    else:
        caption = (
            f"{info['emoji']} *{u_name}* and *{t_name}* went to the {place_name}!\n\n"
            f"{outcome_text}\n\n"
        )
        if bonus > 0:
            caption += f"💰 Bonus: *+{bonus}$*\n"
        caption += f"💳 Cost: *{price}$* | 💰 Balance: *{new_bal}$* {KOLLAR}"

    await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 3. /giftpet [pet_name] — Gift a pet to someone (reply)
# ════════════════════════════════════════════════════════════
async def giftpet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    reply = update.message.reply_to_message
    if not reply or not reply.from_user:
        msg = ("❌ باید روی پیام کسی ریپلای بزنی!\nاستفاده: `/giftpet [نام حیوان]`" if lang == "fa"
               else "❌ Reply to someone's message!\nUsage: `/giftpet [pet_name]`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    target = reply.from_user
    if target.id == user.id:
        msg = "❌ نمی‌تونی به خودت هدیه بدی! 😅" if lang == "fa" else "❌ You can't gift yourself! 😅"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    _remember_user(chat.id, target)

    args = context.args or []
    if not args:
        msg = ("❌ اسم حیوان رو بنویس!\nمثال: `/giftpet cat`" if lang == "fa"
               else "❌ Specify the pet name!\nExample: `/giftpet cat`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    pet_id = args[0].lower()
    item_id = f"pet_{pet_id}"

    # Check giver has this pet
    if not has_item(chat.id, user.id, item_id):
        msg = ("❌ تو این حیوان رو نداری! 🐾" if lang == "fa"
               else "❌ You don't have this pet! 🐾")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Find the item in inventory to get its name
    inv = get_inventory(chat.id, user.id)
    item_data = None
    for it in inv:
        if it.get("item_id") == item_id:
            item_data = it
            break

    if not item_data:
        msg = "❌ خطا!" if lang == "fa" else "❌ Error!"
        await update.message.reply_text(msg)
        return

    pet_name = item_data.get("name", pet_id)

    # Transfer: remove from giver, add to receiver
    remove_inventory_item(chat.id, user.id, item_id)
    add_inventory_item(chat.id, target.id, {
        "item_id": item_id,
        "category": "pet",
        "name": pet_name,
    })

    u_name = (user.full_name or user.first_name or "User").strip()
    t_name = (target.full_name or target.first_name or "User").strip()

    gift_msgs_fa = [
        f"🎁🐾 *{u_name}* حیوان *{pet_name}* رو به *{t_name}* هدیه داد! چه مهربون! 💕",
        f"🐾✨ *{u_name}* با عشق *{pet_name}* رو داد به *{t_name}*! مراقبش باش! 🥰",
        f"🎀🐾 *{t_name}* یه دوست جدید داره! *{u_name}* بهش *{pet_name}* داد! 🎉",
        f"💝🐾 *{u_name}* → *{pet_name}* → *{t_name}*! انتقال عشق! 💫",
    ]
    gift_msgs_en = [
        f"🎁🐾 *{u_name}* gifted *{pet_name}* to *{t_name}*! How sweet! 💕",
        f"🐾✨ *{u_name}* lovingly gave *{pet_name}* to *{t_name}*! Take care of it! 🥰",
        f"🎀🐾 *{t_name}* has a new friend! *{u_name}* gave them *{pet_name}*! 🎉",
        f"💝🐾 *{u_name}* → *{pet_name}* → *{t_name}*! Love transfer! 💫",
    ]

    msg = random.choice(gift_msgs_fa if lang == "fa" else gift_msgs_en)
    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 4. /giftfood [food_name] — Gift food to someone (reply)
# ════════════════════════════════════════════════════════════
async def giftfood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    reply = update.message.reply_to_message
    if not reply or not reply.from_user:
        msg = ("❌ باید روی پیام کسی ریپلای بزنی!\nاستفاده: `/giftfood [نام غذا]`" if lang == "fa"
               else "❌ Reply to someone's message!\nUsage: `/giftfood [food_name]`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    target = reply.from_user
    if target.id == user.id:
        msg = "❌ نمی‌تونی به خودت هدیه بدی! 😅" if lang == "fa" else "❌ You can't gift yourself! 😅"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    _remember_user(chat.id, target)

    args = context.args or []
    if not args:
        msg = ("❌ اسم غذا رو بنویس!\nمثال: `/giftfood pizza`" if lang == "fa"
               else "❌ Specify the food name!\nExample: `/giftfood pizza`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    food_id = args[0].lower()
    item_id = f"food_{food_id}"

    if not has_item(chat.id, user.id, item_id):
        msg = ("❌ تو این غذا رو نداری! 🍽" if lang == "fa"
               else "❌ You don't have this food! 🍽")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    inv = get_inventory(chat.id, user.id)
    item_data = None
    for it in inv:
        if it.get("item_id") == item_id:
            item_data = it
            break

    if not item_data:
        msg = "❌ خطا!" if lang == "fa" else "❌ Error!"
        await update.message.reply_text(msg)
        return

    food_name = item_data.get("name", food_id)

    remove_inventory_item(chat.id, user.id, item_id)
    add_inventory_item(chat.id, target.id, {
        "item_id": item_id,
        "category": "food",
        "name": food_name,
    })

    u_name = (user.full_name or user.first_name or "User").strip()
    t_name = (target.full_name or target.first_name or "User").strip()

    gift_msgs_fa = [
        f"🎁🍽 *{u_name}* غذای *{food_name}* رو به *{t_name}* هدیه داد! نوش جان! 😋",
        f"🍕✨ *{u_name}* با مهربونی *{food_name}* رو داد به *{t_name}*! بخور جون بگیر! 💪",
        f"🎀🍽 *{t_name}* شکمش رو زد! *{u_name}* بهش *{food_name}* داد! 🎉🤤",
        f"💝🍴 *{u_name}* → *{food_name}* → *{t_name}*! تحویل عشق خوراکی! 💫",
    ]
    gift_msgs_en = [
        f"🎁🍽 *{u_name}* gifted *{food_name}* to *{t_name}*! Bon appétit! 😋",
        f"🍕✨ *{u_name}* kindly gave *{food_name}* to *{t_name}*! Eat up! 💪",
        f"🎀🍽 *{t_name}* got a treat! *{u_name}* gave them *{food_name}*! 🎉🤤",
        f"💝🍴 *{u_name}* → *{food_name}* → *{t_name}*! Edible love delivery! 💫",
    ]

    msg = random.choice(gift_msgs_fa if lang == "fa" else gift_msgs_en)
    await update.message.reply_text(msg, parse_mode="Markdown")
