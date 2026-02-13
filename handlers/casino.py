# ==========================================
# KNTU Bot 25 — Casino & Bar System
# ==========================================

import random
import io
import os
from collections import Counter

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance,
    load_data, save_data, get_user_name, set_user_name,
    add_inventory_item, track_member,
)

# ── Constants ──────────────────────────────────────────────
KOLLAR = "کلار $"
MIN_BET = 20
MAX_BET = 1000

MEGA_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🔔", "⭐"]
CARD_SUITS = ["♠", "♥", "♦", "♣"]
CARD_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

# ── Image palette ──────────────────────────────────────────
BG_COLOR = (30, 30, 46)
BOX_FILL = (69, 71, 90)
TEXT_COLOR = (205, 214, 244)
TITLE_COLOR = (137, 180, 250)
PRICE_COLOR = (166, 227, 161)
RED_COLOR = (243, 139, 168)
GOLD_COLOR = (249, 226, 175)
GREEN_COLOR = (166, 227, 161)

# ── Bar drinks ─────────────────────────────────────────────
BAR_DRINKS = {
    "beer": {
        "price": 15,
        "emoji": "🍺",
        "name_fa": "آبجو",
        "name_en": "Beer",
        "messages_fa": [
            "🍺 یه قلپ زدی و دنیا شروع کرد چرخیدن... هیک! 🌀",
            "🍺 بعد از نوشیدن آبجو، سعی کردی با صندلی رقص تانگو کنی 💃",
            "🍺 الان فکر می‌کنی فلسفه زندگی رو فهمیدی... ولی فقط خوابت میاد 😴",
            "🍺 آبجو نوشیدی و شروع کردی برای گربه آواز خوندن 🐱🎤",
            "🍺 یه لیوان نوشیدی و الان داری به دیوار سلام می‌کنی! سلااام دیوار! 👋",
            "🍺 ریختی تو خودت و حالا هر چیزی بامزه‌ست... حتی مالیات 😂",
        ],
        "messages_en": [
            "🍺 One sip and the world started spinning... *hic!* 🌀",
            "🍺 After the beer, you tried to tango with a chair 💃",
            "🍺 You think you've figured out the meaning of life... but you're just sleepy 😴",
            "🍺 You drank it and started singing karaoke to a cat 🐱🎤",
            "🍺 One glass in and you're waving at a wall! Hello wall! 👋",
            "🍺 Chugged it and now everything is funny... even taxes 😂",
        ],
    },
    "wine": {
        "price": 30,
        "emoji": "🍷",
        "name_fa": "شراب",
        "name_en": "Wine",
        "messages_fa": [
            "🍷 شراب نوشیدی و حالا با لهجه فرانسوی حرف می‌زنی... بُنژور! 🇫🇷",
            "🍷 یک جرعه... و ناگهان احساس کردی شاعر قرن هستی ✨",
            "🍷 شراب رو چرخوندی توی لیوان، بو کردی، و بعد یه نفس سر کشیدی 🤣",
            "🍷 الان داری درباره هنر مدرن نظر می‌دی... تو که تا دیروز نقاشی بلد نبودی! 🎨",
            "🍷 شمع روشن کردی، شراب نوشیدی... ولی تنهایی 🕯️😢",
            "🍷 با یه جرعه شراب، رومانتیک‌ترین آدم گروه شدی 💕",
        ],
        "messages_en": [
            "🍷 You sipped wine and now you're speaking with a French accent... Bonjour! 🇫🇷",
            "🍷 One sip... and suddenly you feel like a 19th century poet ✨",
            "🍷 Swirled it, sniffed it, then chugged the whole glass 🤣",
            "🍷 Now you're commenting on modern art... you couldn't draw a stick figure yesterday! 🎨",
            "🍷 Lit a candle, poured some wine... but you're alone 🕯️😢",
            "🍷 One sip of wine and you became the most romantic person in the group 💕",
        ],
    },
    "whiskey": {
        "price": 50,
        "emoji": "🥃",
        "name_fa": "ویسکی",
        "name_en": "Whiskey",
        "messages_fa": [
            "🥃 ویسکی خوردی و حالا فکر می‌کنی جان ویک هستی 🔫😎",
            "🥃 یه شات زدی و مشت کوبیدی رو میز: «من از هیچکس نمی‌ترسم!» 💪",
            "🥃 ویسکی نوشیدی و شروع کردی داستان جنگ‌هایی که نرفتی رو تعریف کردن ⚔️",
            "🥃 چشماتو ریز کردی، ویسکی رو آروم خوردی... بعد عطسه کردی و همه‌چیز خراب شد 🤧",
            "🥃 الان فکر می‌کنی می‌تونی با خرس کشتی بگیری! (نمی‌تونی) 🐻",
            "🥃 یه لیوان ویسکی و حالا صدات دو اکتاو پایین‌تر شده 🗿",
        ],
        "messages_en": [
            "🥃 You drank whiskey and now you think you're John Wick 🔫😎",
            "🥃 One shot and you slammed the table: 'I FEAR NO ONE!' 💪",
            "🥃 Drank whiskey and started telling war stories from wars you never went to ⚔️",
            "🥃 Squinted your eyes, sipped slowly... then sneezed and ruined everything 🤧",
            "🥃 Now you think you can wrestle a bear! (You can't) 🐻",
            "🥃 One glass of whiskey and your voice dropped two octaves 🗿",
        ],
    },
    "cocktail": {
        "price": 40,
        "emoji": "🍹",
        "name_fa": "کوکتل",
        "name_en": "Cocktail",
        "messages_fa": [
            "🍹 کوکتل رنگی خوردی و حالا رنگین‌کمون می‌بینی 🌈",
            "🍹 چتر کوچیک نوشیدنی رو برداشتی و داری باهاش سلفی می‌گیری 📸",
            "🍹 یه جرعه خوردی و احساس کردی توی ساحل هاوایی هستی 🏝️",
            "🍹 طعم آناناس و... یه چیز دیگه... الان همه‌چیز بنفشه! 💜",
            "🍹 کوکتل نوشیدی و شروع کردی رقص سالسا! آله آله! 💃🕺",
            "🍹 نوشیدی تمومش کردی و گفتی: «یه دونه دیگه بیار!» 🔄",
        ],
        "messages_en": [
            "🍹 Drank a colorful cocktail and now you're seeing rainbows 🌈",
            "🍹 You took the tiny umbrella and started taking selfies with it 📸",
            "🍹 One sip and you feel like you're on a beach in Hawaii 🏝️",
            "🍹 Tastes like pineapple and... something else... everything is purple now! 💜",
            "🍹 Drank the cocktail and started salsa dancing! Olé! 💃🕺",
            "🍹 Finished it and said: 'Bring me another one!' 🔄",
        ],
    },
    "juice": {
        "price": 10,
        "emoji": "🧃",
        "name_fa": "آبمیوه",
        "name_en": "Juice",
        "messages_fa": [
            "🧃 آبمیوه خوردی! حالا من مطمئنم مامانت بهت افتخار می‌کنه 😊",
            "🧃 انتخاب سالم! بدنت داره ازت تشکر می‌کنه 💪🥰",
            "🧃 آبمیوه پرتقال با ویتامین C! حالا سرما نمی‌خوری 🍊",
            "🧃 بقیه مست کردن ولی تو آبمیوه می‌خوری... چه بچه خوبی! ⭐",
            "🧃 آبمیوه نوشیدی و احساس می‌کنی ۱۰ سال جوون‌تر شدی! 🌟",
            "🧃 با آبمیوه خودت نشستی گوشه بار و لبخند می‌زنی... خوشحالِ خوشحال 😄",
        ],
        "messages_en": [
            "🧃 You drank juice! Your mom would be so proud of you 😊",
            "🧃 Healthy choice! Your body is thanking you right now 💪🥰",
            "🧃 Orange juice with vitamin C! No cold for you 🍊",
            "🧃 Everyone else is wasted but you're sipping juice... good kid! ⭐",
            "🧃 Drank juice and you feel 10 years younger! 🌟",
            "🧃 Sitting in the corner of the bar with your juice, smiling... pure happiness 😄",
        ],
    },
}


# ── Helpers ────────────────────────────────────────────────
def _remember_user(chat_id, user):
    set_user_name(chat_id, user.id,
                  (user.full_name or user.first_name or "User").strip())
    track_member(chat_id, user.id)


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for p in [
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ── Blackjack helpers ──────────────────────────────────────
def _new_deck() -> list:
    deck = []
    for suit in CARD_SUITS:
        for rank in CARD_RANKS:
            deck.append(f"{rank}{suit}")
    random.shuffle(deck)
    return deck


def _card_value(card: str) -> int:
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def _hand_value(cards: list) -> int:
    total = sum(_card_value(c) for c in cards)
    aces = sum(1 for c in cards if c.startswith("A"))
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def _hand_str(cards: list) -> str:
    return "  ".join(cards)


def _hand_display(cards: list, hide_second: bool = False) -> str:
    if hide_second and len(cards) >= 2:
        return f"{cards[0]}  🂠"
    return _hand_str(cards)


# ── Image renderers ───────────────────────────────────────

def _render_casino_menu(lang: str) -> io.BytesIO:
    W, H = 480, 420
    font = _get_font(16)
    font_title = _get_font(22)
    font_sm = _get_font(13)
    font_big = _get_font(11)

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── Pixel art casino building ──
    bx, by = W // 2 - 60, 8
    # Main building body
    draw.rectangle([bx, by + 20, bx + 120, by + 65], fill=(80, 82, 105))
    # Roof
    draw.polygon([(bx - 5, by + 20), (bx + 60, by), (bx + 125, by + 20)],
                 fill=(137, 180, 250))
    # Door
    draw.rectangle([bx + 48, by + 40, bx + 72, by + 65], fill=(49, 50, 68))
    # Windows
    for wx in [bx + 12, bx + 30, bx + 90, bx + 105]:
        draw.rectangle([wx, by + 28, wx + 12, by + 38], fill=(249, 226, 175))
    # Sign
    sign = "🎰 CASINO" if lang == "en" else "🎰 کازینو"
    sb = draw.textbbox((0, 0), sign, font=font)
    draw.text(((W - sb[2] + sb[0]) // 2, by + 68), sign, fill=GOLD_COLOR, font=font)

    # ── Title bar ──
    ty = 95
    draw.rounded_rectangle([0, ty, W, ty + 44], radius=12, fill=(49, 50, 68))
    title = "🎰 منوی کازینو و بار" if lang == "fa" else "🎰 Casino & Bar Menu"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, ty + 8), title, fill=TITLE_COLOR, font=font_title)

    # ── Menu items ──
    menu_items = [
        ("🎰", "/megaslots [amount]",
         "اسلات ۵ ریل — شانست رو امتحان کن!" if lang == "fa" else "5-Reel Mega Slots — Try your luck!"),
        ("🃏", "/blackjack [amount]",
         "بلک‌جک — ۲۱ بزن تا ببری!" if lang == "fa" else "Blackjack — Hit 21 to win!"),
        ("🪙", "/coinflip [amount]",
         "شیر یا خط — ۵۰/۵۰ شانس!" if lang == "fa" else "Coinflip — 50/50 chance!"),
        ("🍺", "/bar",
         "بار — یه نوشیدنی بزن حال کن!" if lang == "fa" else "Bar — Grab a drink and chill!"),
    ]

    y = ty + 54
    for emoji, cmd, desc in menu_items:
        draw.rounded_rectangle([16, y, W - 16, y + 60], radius=10, fill=BOX_FILL)
        draw.text((30, y + 6), f"{emoji}  {cmd}", fill=TITLE_COLOR, font=font)
        draw.text((30, y + 30), desc, fill=TEXT_COLOR, font=font_sm)
        y += 68

    # ── Footer ──
    foot = "حداقل شرط: 20$ | حداکثر: 1000$" if lang == "fa" else "Min bet: 20$ | Max bet: 1000$"
    fb = draw.textbbox((0, 0), foot, font=font_sm)
    draw.text(((W - fb[2] + fb[0]) // 2, H - 22), foot, fill=(150, 150, 170), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _render_megaslots(reels: list, bet: int, payout: int, won: bool, lang: str) -> io.BytesIO:
    W, H = 500, 300
    font = _get_font(16)
    font_title = _get_font(22)
    font_big = _get_font(32)
    font_sm = _get_font(13)

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    draw.rounded_rectangle([0, 0, W, 48], radius=12, fill=(49, 50, 68))
    title = "🎰 مگا اسلات" if lang == "fa" else "🎰 MEGA SLOTS"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 10), title, fill=GOLD_COLOR, font=font_title)

    # Slot machine frame
    frame_y = 60
    draw.rounded_rectangle([30, frame_y, W - 30, frame_y + 100], radius=14, fill=(49, 50, 68))
    draw.rounded_rectangle([36, frame_y + 6, W - 36, frame_y + 94], radius=10, fill=(20, 20, 34))

    # Reel boxes and symbols
    reel_w = 76
    start_x = 50
    for i, symbol in enumerate(reels):
        rx = start_x + i * (reel_w + 10)
        draw.rounded_rectangle([rx, frame_y + 14, rx + reel_w, frame_y + 86],
                               radius=8, fill=BOX_FILL)
        # We render the symbol text centered
        stb = draw.textbbox((0, 0), symbol, font=font_big)
        sw = stb[2] - stb[0]
        sh = stb[3] - stb[1]
        draw.text((rx + (reel_w - sw) // 2, frame_y + 14 + (72 - sh) // 2),
                  symbol, fill=TEXT_COLOR, font=font_big)

    # Connecting line through matching symbols
    if won:
        line_y = frame_y + 50
        draw.line([(40, line_y), (W - 40, line_y)], fill=GOLD_COLOR, width=2)

    # Result box
    ry = frame_y + 112
    result_color = GREEN_COLOR if won else RED_COLOR
    draw.rounded_rectangle([30, ry, W - 30, ry + 50], radius=10, fill=BOX_FILL)

    if won:
        if lang == "fa":
            result = f"🎉 بردی! +{payout}$ {KOLLAR}"
        else:
            result = f"🎉 YOU WIN! +{payout}$ {KOLLAR}"
    else:
        if lang == "fa":
            result = f"💀 باختی! -{bet}$ {KOLLAR}"
        else:
            result = f"💀 YOU LOSE! -{bet}$ {KOLLAR}"

    rb = draw.textbbox((0, 0), result, font=font)
    draw.text(((W - rb[2] + rb[0]) // 2, ry + 14), result, fill=result_color, font=font)

    # Bet / Balance line
    info_y = ry + 60
    bet_text = f"Bet: {bet}$" if lang == "en" else f"شرط: {bet}$"
    draw.text((30, info_y), bet_text, fill=TEXT_COLOR, font=font_sm)

    # Decorative stars
    star_positions = [(10, 55), (W - 28, 55), (10, ry + 50), (W - 28, ry + 50)]
    for sx, sy in star_positions:
        draw.text((sx, sy), "✦", fill=GOLD_COLOR, font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Mega Slots payout calculation ──────────────────────────
def _calc_megaslots_payout(reels: list, bet: int) -> tuple[int, str]:
    """Returns (net_gain_or_loss, description_key).
    Positive = profit added, Negative = loss."""
    counts = Counter(reels)
    best_count = counts.most_common(1)[0][1]
    best_symbol = counts.most_common(1)[0][0]

    if best_count == 5:
        if best_symbol == "💎":
            mult = 100
        elif best_symbol == "7️⃣":
            mult = 50
        else:
            mult = 20
        return bet * mult, "jackpot_5"

    if best_count == 4:
        return bet * 8, "match_4"

    if best_count == 3:
        return bet * 3, "match_3"

    if best_count == 2:
        # Check if there are two separate pairs
        pairs = [s for s, c in counts.items() if c >= 2]
        if len(pairs) >= 2:
            return bet * 1, "two_pair"
        return -bet // 2, "match_2"

    return -bet, "lose"


# ════════════════════════════════════════════════════════════
# 1. /casino — Show casino menu
# ════════════════════════════════════════════════════════════
async def casino_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    buf = _render_casino_menu(lang)

    if lang == "fa":
        caption = (
            "🎰 *به کازینو خوش اومدی!*\n\n"
            "🎲 بازی‌ها:\n"
            "  🎰 `/megaslots [مبلغ]` — مگا اسلات ۵ ریل\n"
            "  🃏 `/blackjack [مبلغ]` — بلک‌جک\n"
            "  🪙 `/coinflip [مبلغ]` — شیر یا خط\n\n"
            "🍺 نوشیدنی:\n"
            "  🍻 `/bar` — منوی بار\n"
            "  🛒 `/bar buy [نوشیدنی]` — خرید نوشیدنی\n\n"
            f"💰 حداقل شرط: *{MIN_BET}$* | حداکثر: *{MAX_BET}$*"
        )
    else:
        caption = (
            "🎰 *Welcome to the Casino!*\n\n"
            "🎲 Games:\n"
            "  🎰 `/megaslots [amount]` — 5-Reel Mega Slots\n"
            "  🃏 `/blackjack [amount]` — Blackjack\n"
            "  🪙 `/coinflip [amount]` — Coin Flip\n\n"
            "🍺 Drinks:\n"
            "  🍻 `/bar` — Bar menu\n"
            "  🛒 `/bar buy [drink]` — Buy a drink\n\n"
            f"💰 Min bet: *{MIN_BET}$* | Max bet: *{MAX_BET}$*"
        )

    await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 2. /megaslots — 5-Reel Slot Machine
# ════════════════════════════════════════════════════════════
async def megaslots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []
    if not args or not args[0].isdigit():
        if lang == "fa":
            await update.message.reply_text(
                f"🎰 *مگا اسلات*\n\nاستفاده: `/megaslots [مبلغ]`\n"
                f"حداقل: *{MIN_BET}$* | حداکثر: *{MAX_BET}$*",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"🎰 *Mega Slots*\n\nUsage: `/megaslots [amount]`\n"
                f"Min: *{MIN_BET}$* | Max: *{MAX_BET}$*",
                parse_mode="Markdown")
        return

    bet = int(args[0])
    if bet < MIN_BET:
        msg = (f"❌ حداقل شرط *{MIN_BET}$* است!" if lang == "fa"
               else f"❌ Minimum bet is *{MIN_BET}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    if bet > MAX_BET:
        msg = (f"❌ حداکثر شرط *{MAX_BET}$* است!" if lang == "fa"
               else f"❌ Maximum bet is *{MAX_BET}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if bet > bal:
        msg = (f"❌ موجودی کافی نیست! ({bal}$)" if lang == "fa"
               else f"❌ Not enough balance! ({bal}$)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Spin the 5 reels
    reels = [random.choice(MEGA_SYMBOLS) for _ in range(5)]
    payout, result_key = _calc_megaslots_payout(reels, bet)

    won = payout > 0

    # Apply balance change
    if won:
        new_bal = add_balance(chat.id, user.id, payout)
    elif payout == 0:
        new_bal = bal
    else:
        new_bal = add_balance(chat.id, user.id, payout)  # payout is negative

    # Render image
    display_payout = payout if won else bet
    buf = _render_megaslots(reels, bet, abs(payout), won, lang)

    # Build result text
    reel_display = " | ".join(reels)

    if lang == "fa":
        result_msgs = {
            "jackpot_5": f"🏆🏆🏆 *جک‌پات ۵ تایی!* 🏆🏆🏆\n💰 *{payout}$* بردی!!! 🤑🤑🤑",
            "match_4":   f"🎉🎉 *۴ تا یکی!* عالی بود!\n💰 *{payout}$* بردی! 🤩",
            "match_3":   f"🎊 *۳ تا یکی!* خوب بود!\n💰 *{payout}$* بردی! 😎",
            "two_pair":  f"✨ *دو جفت!* بد نبود!\n💰 *{payout}$* بردی! 💫",
            "match_2":   f"😐 *فقط ۲ تا یکی...* نصف شرطت برگشت.\n💸 *{abs(payout)}$* از دست دادی.",
            "lose":      f"💀 *باختی!* هیچی نیومد...\n💸 *{bet}$* از دست دادی! 😵",
        }
        msg = (
            f"🎰 *مگا اسلات*\n\n"
            f"╔══════════════════╗\n"
            f"║  {reel_display}  ║\n"
            f"╚══════════════════╝\n\n"
            f"{result_msgs.get(result_key, '')}\n\n"
            f"💰 موجودی: *{new_bal}$* {KOLLAR}"
        )
    else:
        result_msgs = {
            "jackpot_5": f"🏆🏆🏆 *5-OF-A-KIND JACKPOT!* 🏆🏆🏆\n💰 You won *{payout}$*!!! 🤑🤑🤑",
            "match_4":   f"🎉🎉 *4 of a kind!* Amazing!\n💰 You won *{payout}$*! 🤩",
            "match_3":   f"🎊 *3 of a kind!* Nice!\n💰 You won *{payout}$*! 😎",
            "two_pair":  f"✨ *Two pairs!* Not bad!\n💰 You won *{payout}$*! 💫",
            "match_2":   f"😐 *Only 2 matching...* Got half back.\n💸 Lost *{abs(payout)}$*.",
            "lose":      f"💀 *YOU LOSE!* Nothing matched...\n💸 Lost *{bet}$*! 😵",
        }
        msg = (
            f"🎰 *MEGA SLOTS*\n\n"
            f"╔══════════════════╗\n"
            f"║  {reel_display}  ║\n"
            f"╚══════════════════╝\n\n"
            f"{result_msgs.get(result_key, '')}\n\n"
            f"💰 Balance: *{new_bal}$* {KOLLAR}"
        )

    await update.message.reply_photo(photo=buf, caption=msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 3. /blackjack — Blackjack (21)
# ════════════════════════════════════════════════════════════
def _get_bj_games(data: dict, cid: str) -> dict:
    return data.setdefault("blackjack", {}).setdefault(cid, {})


def _set_bj_game(data: dict, cid: str, uid: str, game: dict):
    data.setdefault("blackjack", {}).setdefault(cid, {})[uid] = game


def _del_bj_game(data: dict, cid: str, uid: str):
    data.setdefault("blackjack", {}).setdefault(cid, {}).pop(uid, None)


def _bj_keyboard(lang: str, cid: str, uid: str) -> InlineKeyboardMarkup:
    if lang == "fa":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🃏 کارت بکش", callback_data=f"bj:hit:{cid}:{uid}"),
                InlineKeyboardButton("🛑 بسه", callback_data=f"bj:stand:{cid}:{uid}"),
            ]
        ])
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🃏 Hit", callback_data=f"bj:hit:{cid}:{uid}"),
            InlineKeyboardButton("🛑 Stand", callback_data=f"bj:stand:{cid}:{uid}"),
        ]
    ])


def _bj_game_text(game: dict, lang: str, phase: str = "playing",
                   result: str = "", final_balance: int = 0) -> str:
    player_cards = game["player_cards"]
    dealer_cards = game["dealer_cards"]
    bet = game["bet"]

    p_val = _hand_value(player_cards)

    if phase == "playing":
        d_display = _hand_display(dealer_cards, hide_second=True)
        d_val_str = "?"
    else:
        d_display = _hand_display(dealer_cards)
        d_val_str = str(_hand_value(dealer_cards))

    p_display = _hand_display(player_cards)

    if lang == "fa":
        text = (
            f"🃏 *بلک‌جک*\n\n"
            f"🎰 شرط: *{bet}$*\n\n"
            f"👤 دست تو: {p_display}\n"
            f"📊 مجموع: *{p_val}*\n\n"
            f"🤖 دست دیلر: {d_display}\n"
            f"📊 مجموع: *{d_val_str}*"
        )
        if result:
            text += f"\n\n{result}"
        if final_balance:
            text += f"\n💰 موجودی: *{final_balance}$*"
    else:
        text = (
            f"🃏 *Blackjack*\n\n"
            f"🎰 Bet: *{bet}$*\n\n"
            f"👤 Your hand: {p_display}\n"
            f"📊 Total: *{p_val}*\n\n"
            f"🤖 Dealer: {d_display}\n"
            f"📊 Total: *{d_val_str}*"
        )
        if result:
            text += f"\n\n{result}"
        if final_balance:
            text += f"\n💰 Balance: *{final_balance}$*"

    return text


async def blackjack_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    cid, uid = str(chat.id), str(user.id)
    args = context.args or []

    # Check for existing game
    data = load_data()
    existing = _get_bj_games(data, cid).get(uid)
    if existing and existing.get("phase") == "playing":
        if lang == "fa":
            msg = "❌ تو الان یه بازی فعال داری! اول اون رو تموم کن."
        else:
            msg = "❌ You have an active game! Finish it first."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if not args or not args[0].isdigit():
        if lang == "fa":
            await update.message.reply_text(
                f"🃏 *بلک‌جک*\n\nاستفاده: `/blackjack [مبلغ]`\n"
                f"حداقل: *{MIN_BET}$* | حداکثر: *{MAX_BET}$*",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"🃏 *Blackjack*\n\nUsage: `/blackjack [amount]`\n"
                f"Min: *{MIN_BET}$* | Max: *{MAX_BET}$*",
                parse_mode="Markdown")
        return

    bet = int(args[0])
    if bet < MIN_BET:
        msg = (f"❌ حداقل شرط *{MIN_BET}$* است!" if lang == "fa"
               else f"❌ Minimum bet is *{MIN_BET}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    if bet > MAX_BET:
        msg = (f"❌ حداکثر شرط *{MAX_BET}$* است!" if lang == "fa"
               else f"❌ Maximum bet is *{MAX_BET}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if bet > bal:
        msg = (f"❌ موجودی کافی نیست! ({bal}$)" if lang == "fa"
               else f"❌ Not enough balance! ({bal}$)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Deduct bet
    add_balance(chat.id, user.id, -bet)

    # Deal cards
    deck = _new_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]

    game = {
        "player_cards": player_cards,
        "dealer_cards": dealer_cards,
        "deck": deck,
        "bet": bet,
        "phase": "playing",
    }

    # Check natural blackjack
    p_val = _hand_value(player_cards)
    d_val = _hand_value(dealer_cards)

    if p_val == 21 and d_val == 21:
        # Push — both natural blackjack
        game["phase"] = "done"
        data = load_data()
        _del_bj_game(data, cid, uid)
        save_data(data)
        new_bal = add_balance(chat.id, user.id, bet)  # return bet
        if lang == "fa":
            result = "🤝 *مساوی!* هر دو بلک‌جک دارید!"
        else:
            result = "🤝 *Push!* Both have Blackjack!"
        text = _bj_game_text(game, lang, phase="done", result=result, final_balance=new_bal)
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    if p_val == 21:
        # Natural blackjack — pays 2.5x
        game["phase"] = "done"
        data = load_data()
        _del_bj_game(data, cid, uid)
        save_data(data)
        winnings = int(bet * 2.5)
        new_bal = add_balance(chat.id, user.id, winnings)
        if lang == "fa":
            result = f"🎉🃏 *بلک‌جک طبیعی!* 🔥\n💰 *{winnings}$* بردی! (2.5x)"
        else:
            result = f"🎉🃏 *NATURAL BLACKJACK!* 🔥\n💰 Won *{winnings}$*! (2.5x)"
        text = _bj_game_text(game, lang, phase="done", result=result, final_balance=new_bal)
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    # Save game state
    data = load_data()
    _set_bj_game(data, cid, uid, game)
    save_data(data)

    text = _bj_game_text(game, lang, phase="playing")
    keyboard = _bj_keyboard(lang, cid, uid)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def bj_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 4:
        return
    _, action, cid, uid = parts

    # Only the player who started the game can interact
    if str(query.from_user.id) != uid:
        if get_lang(int(cid)) == "fa":
            await query.answer("❌ این بازی مال تو نیست!", show_alert=True)
        else:
            await query.answer("❌ This is not your game!", show_alert=True)
        return

    lang = get_lang(int(cid))
    data = load_data()
    games = _get_bj_games(data, cid)
    game = games.get(uid)

    if not game or game.get("phase") != "playing":
        await query.edit_message_text(
            "❌ بازی فعالی وجود ندارد." if lang == "fa" else "❌ No active game.",
            parse_mode="Markdown")
        return

    deck = game["deck"]
    player_cards = game["player_cards"]
    dealer_cards = game["dealer_cards"]
    bet = game["bet"]

    if action == "hit":
        # Draw a card
        if not deck:
            deck = _new_deck()
        player_cards.append(deck.pop())
        p_val = _hand_value(player_cards)

        if p_val > 21:
            # Bust
            game["phase"] = "done"
            _del_bj_game(data, cid, uid)
            save_data(data)
            new_bal = get_balance(int(cid), int(uid))
            if lang == "fa":
                result = f"💥 *سوختی!* مجموع: {p_val}\n💸 *{bet}$* از دست دادی!"
            else:
                result = f"💥 *BUST!* Total: {p_val}\n💸 Lost *{bet}$*!"
            text = _bj_game_text(game, lang, phase="done", result=result, final_balance=new_bal)
            await query.edit_message_text(text, parse_mode="Markdown")
            return

        if p_val == 21:
            # Auto-stand on 21
            action = "stand"
        else:
            # Continue playing
            game["deck"] = deck
            game["player_cards"] = player_cards
            _set_bj_game(data, cid, uid, game)
            save_data(data)
            text = _bj_game_text(game, lang, phase="playing")
            keyboard = _bj_keyboard(lang, cid, uid)
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
            return

    if action == "stand":
        # Dealer plays
        d_val = _hand_value(dealer_cards)
        while d_val < 17:
            if not deck:
                deck = _new_deck()
            dealer_cards.append(deck.pop())
            d_val = _hand_value(dealer_cards)

        p_val = _hand_value(player_cards)
        game["player_cards"] = player_cards
        game["dealer_cards"] = dealer_cards
        game["phase"] = "done"
        _del_bj_game(data, cid, uid)
        save_data(data)

        # Determine winner
        if d_val > 21:
            # Dealer bust
            winnings = bet * 2
            new_bal = add_balance(int(cid), int(uid), winnings)
            if lang == "fa":
                result = f"🎉 *دیلر سوخت!* ({d_val})\n💰 *{winnings}$* بردی!"
            else:
                result = f"🎉 *Dealer BUSTS!* ({d_val})\n💰 Won *{winnings}$*!"
        elif p_val > d_val:
            winnings = bet * 2
            new_bal = add_balance(int(cid), int(uid), winnings)
            if lang == "fa":
                result = f"🎉 *بردی!* {p_val} > {d_val}\n💰 *{winnings}$* بردی!"
            else:
                result = f"🎉 *YOU WIN!* {p_val} > {d_val}\n💰 Won *{winnings}$*!"
        elif p_val == d_val:
            new_bal = add_balance(int(cid), int(uid), bet)
            if lang == "fa":
                result = f"🤝 *مساوی!* {p_val} = {d_val}\n↩️ شرطت (*{bet}$*) برگشت."
            else:
                result = f"🤝 *Push!* {p_val} = {d_val}\n↩️ Bet (*{bet}$*) returned."
        else:
            new_bal = get_balance(int(cid), int(uid))
            if lang == "fa":
                result = f"💀 *باختی!* {p_val} < {d_val}\n💸 *{bet}$* از دست دادی!"
            else:
                result = f"💀 *YOU LOSE!* {p_val} < {d_val}\n💸 Lost *{bet}$*!"

        text = _bj_game_text(game, lang, phase="done", result=result, final_balance=new_bal)
        await query.edit_message_text(text, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 4. /bar — Bar & Drinks
# ════════════════════════════════════════════════════════════
async def bar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []

    # /bar buy [drink]
    if len(args) >= 2 and args[0].lower() == "buy":
        drink_id = args[1].lower()
        if drink_id not in BAR_DRINKS:
            # Try to match by name
            for did, dinfo in BAR_DRINKS.items():
                if drink_id in (did, dinfo["name_en"].lower(), dinfo["name_fa"]):
                    drink_id = did
                    break
            else:
                available = ", ".join(BAR_DRINKS.keys())
                if lang == "fa":
                    msg = f"❌ نوشیدنی نامعتبر!\n🍹 موجود: {available}"
                else:
                    msg = f"❌ Invalid drink!\n🍹 Available: {available}"
                await update.message.reply_text(msg, parse_mode="Markdown")
                return

        drink = BAR_DRINKS[drink_id]
        price = drink["price"]
        bal = get_balance(chat.id, user.id)

        if price > bal:
            msg = (f"❌ پول کافی نیست! ({bal}$) — قیمت: {price}$" if lang == "fa"
                   else f"❌ Not enough money! ({bal}$) — Price: {price}$")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        new_bal = add_balance(chat.id, user.id, -price)
        name = drink["name_fa"] if lang == "fa" else drink["name_en"]

        # Add drink to inventory so it can be gifted or consumed via /drink
        add_inventory_item(chat.id, user.id, {
            "item_id": f"drink_{drink_id}",
            "category": "drink",
            "name": name,
        })

        if lang == "fa":
            effect = random.choice(drink["messages_fa"])
        else:
            effect = random.choice(drink["messages_en"])

        if lang == "fa":
            msg = (
                f"{drink['emoji']} *{user.first_name}* یه {name} سفارش داد! ({price}$)\n\n"
                f"{effect}\n\n"
                f"💰 موجودی: *{new_bal}$*"
            )
        else:
            msg = (
                f"{drink['emoji']} *{user.first_name}* ordered a {name}! ({price}$)\n\n"
                f"{effect}\n\n"
                f"💰 Balance: *{new_bal}$*"
            )

        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # /bar — show menu
    if lang == "fa":
        text = "🍻 *منوی بار*\n\n"
        for did, drink in BAR_DRINKS.items():
            text += f"{drink['emoji']} *{drink['name_fa']}* — {drink['price']}$\n"
            text += f"    `/bar buy {did}`\n\n"
        text += "🍹 یه نوشیدنی بزن و حال کن!"
    else:
        text = "🍻 *Bar Menu*\n\n"
        for did, drink in BAR_DRINKS.items():
            text += f"{drink['emoji']} *{drink['name_en']}* — {drink['price']}$\n"
            text += f"    `/bar buy {did}`\n\n"
        text += "🍹 Grab a drink and have fun!"

    await update.message.reply_text(text, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# 5. /coinflip — Coin Flip with animation
# ════════════════════════════════════════════════════════════
async def coinflip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []
    if not args or not args[0].isdigit():
        if lang == "fa":
            await update.message.reply_text(
                f"🪙 *شیر یا خط*\n\nاستفاده: `/coinflip [مبلغ]`\n"
                f"حداقل: *{MIN_BET}$* | حداکثر: *{MAX_BET}$*",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"🪙 *Coin Flip*\n\nUsage: `/coinflip [amount]`\n"
                f"Min: *{MIN_BET}$* | Max: *{MAX_BET}$*",
                parse_mode="Markdown")
        return

    bet = int(args[0])
    if bet < MIN_BET:
        msg = (f"❌ حداقل شرط *{MIN_BET}$* است!" if lang == "fa"
               else f"❌ Minimum bet is *{MIN_BET}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    if bet > MAX_BET:
        msg = (f"❌ حداکثر شرط *{MAX_BET}$* است!" if lang == "fa"
               else f"❌ Maximum bet is *{MAX_BET}$*!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if bet > bal:
        msg = (f"❌ موجودی کافی نیست! ({bal}$)" if lang == "fa"
               else f"❌ Not enough balance! ({bal}$)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Coin flip animation frames
    frames = ["🪙 ...", "💫 .", "🪙 ..", "💫 ...", "🪙 💫"]
    if lang == "fa":
        spin_text = "🪙 سکه داره می‌چرخه"
    else:
        spin_text = "🪙 Coin is spinning"

    msg = await update.message.reply_text(
        f"{spin_text}\n\n{frames[0]}",
        parse_mode="Markdown")

    import asyncio
    for frame in frames[1:]:
        await asyncio.sleep(0.5)
        try:
            await msg.edit_text(f"{spin_text}\n\n{frame}", parse_mode="Markdown")
        except Exception:
            pass

    # Determine result (50/50)
    won = random.random() < 0.50
    if lang == "fa":
        side = "🦁 شیر" if won else "🌙 خط"
    else:
        side = "👑 Heads" if won else "🌙 Tails"

    if won:
        new_bal = add_balance(chat.id, user.id, bet)
        if lang == "fa":
            result = (
                f"🪙 *شیر یا خط*\n\n"
                f"سکه افتاد روی: *{side}*\n\n"
                f"🎉 *بردی!* +*{bet}$*\n"
                f"💰 موجودی: *{new_bal}$* {KOLLAR}"
            )
        else:
            result = (
                f"🪙 *Coin Flip*\n\n"
                f"The coin landed on: *{side}*\n\n"
                f"🎉 *YOU WIN!* +*{bet}$*\n"
                f"💰 Balance: *{new_bal}$* {KOLLAR}"
            )
    else:
        new_bal = add_balance(chat.id, user.id, -bet)
        if lang == "fa":
            result = (
                f"🪙 *شیر یا خط*\n\n"
                f"سکه افتاد روی: *{side}*\n\n"
                f"💀 *باختی!* -*{bet}$*\n"
                f"💰 موجودی: *{new_bal}$* {KOLLAR}"
            )
        else:
            result = (
                f"🪙 *Coin Flip*\n\n"
                f"The coin landed on: *{side}*\n\n"
                f"💀 *YOU LOSE!* -*{bet}$*\n"
                f"💰 Balance: *{new_bal}$* {KOLLAR}"
            )

    # Final dramatic messages
    if won:
        dramatic = random.choice([
            "🔥🔥🔥" if lang == "en" else "🔥🔥🔥",
            "Lady luck smiles upon you! ✨" if lang == "en" else "خوش‌شانسی باهاته! ✨",
            "The casino weeps! 😭" if lang == "en" else "کازینو گریه می‌کنه! 😭",
            "You're on fire! 🌟" if lang == "en" else "داری آتیش می‌زنی! 🌟",
        ])
    else:
        dramatic = random.choice([
            "💨 Better luck next time..." if lang == "en" else "💨 دفعه بعد شانست بهتره...",
            "The house always wins! 🏠" if lang == "en" else "کازینو همیشه برنده‌ست! 🏠",
            "Ouch! That hurts! 😬" if lang == "en" else "آخ! سوخت! 😬",
            "Gone with the wind... 🍂" if lang == "en" else "رفت که رفت... 🍂",
        ])

    try:
        await msg.edit_text(f"{result}\n\n{dramatic}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(f"{result}\n\n{dramatic}", parse_mode="Markdown")
