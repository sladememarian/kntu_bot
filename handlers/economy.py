# ==========================================
# KNTU Bot 25 — Economy & Gambling
# ==========================================

import random
import io
import os
import math
import time
from datetime import date, datetime, timedelta
from telegram import Update
from handlers.casino import _process_casino_loss
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw, ImageFont

from storage import (
    get_lang, get_balance, add_balance, get_all_balances,
    get_daily_claim, set_daily_claim,
    get_last_work, set_last_work, get_last_spin, set_last_spin,
    get_jail_time, set_jail_time, clear_jail, get_all_jailed,
    get_stocks, set_stocks,
    get_daily_event, set_daily_event,
    set_user_name, get_user_name,
    get_stock_costs, set_stock_costs,
    load_data, save_data,
    add_donation, get_donations,
    get_properties, add_property, remove_property, get_all_properties,
    get_daily_streak, set_daily_streak,
    get_work_xp, add_work_xp,
    has_item, remove_inventory_item,
    get_bounties, set_bounty, remove_bounty,
)
from strings import STRINGS
from config import ADMIN_IDS

DAILY_AMOUNT = 200
KOLLAR = "کلار $"

WORK_COOLDOWN = 3600  # 1 hour
SPIN_COOLDOWN = 8 * 3600  # 8 hours
JAIL_DURATION = 360  # 6 minutes in seconds

# ── Economy realism constants ──────────────────────────────
TRANSFER_TAX_RATE = 0.02      # 2% fee on transfers > 500$
TRANSFER_TAX_THRESHOLD = 500  # Below this = no tax
DAILY_STREAK_BONUS = 25       # +25$ per consecutive day (max 10 streak)
MAX_STREAK = 10
WEALTH_TAX_BRACKETS = [       # (threshold, rate)
    (50000, 0.01),             # 1% on wealth > 50k
    (100000, 0.02),            # 2% on wealth > 100k
    (250000, 0.03),            # 3% on wealth > 250k
    (500000, 0.05),            # 5% on wealth > 500k
]
WORK_XP_PER_JOB = 1           # +1 XP per work
WORK_BONUS_PER_LEVEL = 0.10   # +10% pay per level
WORK_XP_PER_LEVEL = 10        # 10 jobs = 1 level

JOBS = {
    "fa": [
        ("👨‍💻 برنامه‌نویسی", 100, 300),
        ("🎨 طراحی", 80, 250),
        ("📦 تحویل بسته", 50, 150),
        ("🍳 آشپزی", 60, 200),
        ("🎸 نوازندگی", 70, 220),
        ("📚 تدریس", 90, 280),
        ("🔧 تعمیرات", 75, 230),
        ("🌾 کشاورزی", 40, 180),
    ],
    "en": [
        ("👨‍💻 Programming", 100, 300),
        ("🎨 Designing", 80, 250),
        ("📦 Delivery", 50, 150),
        ("🍳 Cooking", 60, 200),
        ("🎸 Playing Music", 70, 220),
        ("📚 Teaching", 90, 280),
        ("🔧 Repairing", 75, 230),
        ("🌾 Farming", 40, 180),
    ],
}

# (amount, emoji, weight)
SPIN_REWARDS = [
    (500, "💎", 2),
    (300, "🎉", 5),
    (200, "⭐", 8),
    (100, "🪙", 15),
    (75, "🍀", 20),
    (50, "📦", 25),
    (0, "💨", 15),
    (-50, "💀", 10),
]

# --- Stock Companies ---
COMPANIES = {
    "AAPL":  {"name": "Apple 🍎",          "base": 180, "sector": "tech"},
    "TSLA":  {"name": "Tesla ⚡",          "base": 250, "sector": "auto"},
    "GOOG":  {"name": "Google 🔍",         "base": 140, "sector": "tech"},
    "AMZN":  {"name": "Amazon 📦",         "base": 190, "sector": "retail"},
    "MSFT":  {"name": "Microsoft 💻",      "base": 320, "sector": "tech"},
    "META":  {"name": "Meta 👤",           "base": 120, "sector": "social"},
    "NVDA":  {"name": "Nvidia 🎮",         "base": 400, "sector": "tech"},
    "BTC":   {"name": "Bitcoin ₿",         "base": 500, "sector": "crypto"},
    "ETH":   {"name": "Ethereum ◆",        "base": 200, "sector": "crypto"},
    "DOGE":  {"name": "Dogecoin 🐕",       "base": 30,  "sector": "crypto"},
    "NFLX":  {"name": "Netflix 🎬",        "base": 160, "sector": "media"},
    "SPOT":  {"name": "Spotify 🎵",        "base": 100, "sector": "media"},
    "DIS":   {"name": "Disney 🏰",         "base": 110, "sector": "media"},
    "SONY":  {"name": "Sony 🎮",           "base": 130, "sector": "tech"},
    "AMD":   {"name": "AMD 📡",            "base": 220, "sector": "tech"},
    "ARMIN": {"name": "Armin 👑",           "base": 175, "sector": "imaginary"},
}

# --- Jail mock messages ---
JAIL_MOCKS = {
    "fa": [
        "🚨 پلیس اومد دنبالت! حالا ۶ دقیقه بشین فکر کن به کارات! 😂",
        "🔒 گرفتنت رفیق! ۶ دقیقه حبس! بشین آدم شو! 🤡",
        "👮 آقا دستگیر شدی! بشین تو سلول ۶ دقیقه فکر کن! 😤",
        "🚔 دزد گرفتیم بچه‌ها! ببرینش بازداشتگاه! ۶ دقیقه! 🤣",
        "⛓️ رفتی تو زندان! ۶ دقیقه بشین به گناهات فکر کن! 😈",
        "🏛️ قاضی حکم داد: ۶ دقیقه زندان برای دزد کوچولو! 💀",
        "🐀 موش گرفتیم! ۶ دقیقه حبس عزیزم! 🧀",
        "🤦 دزد بدبخت! گرفتنت! ۶ دقیقه فکر کن چجوری بهتر بدزدی! 😂",
        "🔐 درب سلول بسته شد! ۶ دقیقه وقت داری آهنگ غمگین بخونی! 🎶",
        "🧱 خوش اومدی به هتل ۵ ستاره زندان! ۶ دقیقه اقامت رایگان! ⭐",
        "🐔 مرغ دزد بودی، حالا زندانی شدی! ۶ دقیقه! 🍗",
        "👻 حتی ارواح زندان ازت میترسن! ۶ دقیقه بشین! 😱",
    ],
    "en": [
        "🚨 Police got you! Now sit in jail for 6 minutes and think! 😂",
        "🔒 Busted! 6 minutes in the slammer! Time to rethink life! 🤡",
        "👮 Arrested! Sit in your cell for 6 mins and reflect! 😤",
        "🚔 Caught a thief! Take them away! 6 minutes of jail time! 🤣",
        "⛓️ You're in custody! 6 minutes to reflect on your sins! 😈",
        "🏛️ Judge says: 6 minutes jail for the tiny thief! 💀",
        "🐀 Caught a rat! 6 minutes behind bars! 🧀",
        "🤦 Poor thief! 6 mins to figure out a better heist! 😂",
        "🔐 Cell door locked! You have 6 mins to sing sad songs! 🎶",
        "🧱 Welcome to 5-star jail hotel! 6 mins free stay! ⭐",
        "🐔 You were a chicken thief, now you're a prisoner! 6 mins! 🍗",
        "👻 Even the jail ghosts are scared of you! Sit for 6 mins! 😱",
    ],
}

# --- Special dungeon messages for robbing user 1556793586 ---
DUNGEON_VICTIM_ID = 1556793586
DUNGEON_JAIL_DURATION = 900  # 15 minutes in seconds
DUNGEON_FINE = 200

DUNGEON_MOCKS = {
    "fa": [
        "🔥👹 به جهنم خوش اومدی احمق! فکر کردی میتونی از این یارو بدزدی؟! 💀",
        "⚰️ تبریک میگم! افتادی تو سیاه‌چال هیولاها! ۱۵ دقیقه با شیاطین زندگی کن! 👿",
        "🕳️ زمین زیر پات باز شد و رفتی ته دوزخ! دزد بدبخت! 😈🔥",
        "💀 هاهاهاها! تو رو فرستادیم طبقه هفتم جهنم! ۱۵ دقیقه بسوز! 🤡🔥",
        "👹 مگه مغز نداری؟! این آدمو میخوای بزنی؟ حالا ۱۵ دقیقه با ابلیس هم‌سلولی! 😂💀",
        "🐍 مارهای زندان منتظرت بودن! خوش اومدی به سیاه‌چال! ۱۵ دقیقه بپوس! 🪱",
        "☠️ دزد ابله! اینجا قبرستان دزداست! ۱۵ دقیقه با مرده‌ها بمون! 💀👻",
        "🌋 آتیش‌فشان زندان فوران کرد رو سرت! ۱۵ دقیقه بسوز کباب شی! 🥩🔥",
        "🦇 خفاش‌های زندان دارن بهت میخندن! احمق‌ترین دزد تاریخ! ۱۵ دقیقه! 😂🦇",
        "💩 افتادی تو چاه فاضلاب زندان! ۱۵ دقیقه بو بکش! دزد گند! 🤮",
    ],
    "en": [
        "🔥👹 WELCOME TO HELL, FOOL! You thought you could rob THEM?! 💀",
        "⚰️ Congratulations! You fell into the DUNGEON OF MONSTERS! 15 mins with demons! 👿",
        "🕳️ The ground opened and swallowed you to the abyss! Pathetic thief! 😈🔥",
        "💀 HAHAHAHA! You've been sent to the 7th circle of hell! Burn for 15 mins! 🤡🔥",
        "👹 ARE YOU BRAINLESS?! Trying to rob THAT person?! 15 mins with Satan! 😂💀",
        "🐍 The dungeon snakes were waiting for you! 15 mins rotting in the pit! 🪱",
        "☠️ STUPID THIEF! This is the graveyard of thieves! 15 mins with the dead! 💀👻",
        "🌋 The prison volcano erupted on your head! 15 mins to get roasted! 🥩🔥",
        "🦇 Prison bats are laughing at you! Dumbest thief in history! 15 mins! 😂🦇",
        "💩 You fell into the prison sewer! 15 mins of stink! You filthy thief! 🤮",
    ],
}

DUNGEON_STICKERS = [
    "CAACAgIAAxkBAAEBAgRnzKp2AAHxX-kqw7hW8jWB_r86xfMAAhIAA8A2TxP-a6cLV28HDDcE",  # devil
    "CAACAgIAAxkBAAEBAgZnzKqaRVMYGS_eFW2DRFkYJuVJDQACGQADwDZPEwjPLN9TnWJRNwQ",  # skull
]

# --- Random Daily Events ---
DAILY_EVENTS = {
    "fa": [
        {"name": "🌍 زلزله!", "desc": "زلزله اومد! همه ۱۰% ضرر کردن!", "effect": -0.10},
        {"name": "🇮🇱➡️🇺🇸 اسرائیل به آمریکا حمله کرد!", "desc": "بازار آشفته شد! همه ۱۵% ضرر!", "effect": -0.15},
        {"name": "🇺🇸➡️🇮🇱 آمریکا به اسرائیل حمله کرد!", "desc": "بازار داغ شد! همه ۱۰% سود!", "effect": 0.10},
        {"name": "🇺🇸🇮🇱➡️🇮🇷 حمله مشترک به ایران!", "desc": "اقتصاد ریخت! همه ۲۰% ضرر!", "effect": -0.20},
        {"name": "💥 دارن میزنن!", "desc": "یه جایی دارن میزنن! بازار متلاطم شد! ۱۲% ضرر!", "effect": -0.12},
        {"name": "🚢 ناوگان اعزام شد!", "desc": "نیروی دریایی اعزام شد! تنش بالا رفت! ۸% ضرر!", "effect": -0.08},
        {"name": "🌧️ بارون شدید!", "desc": "بارون شدید باعث سیل شد! ۵% ضرر!", "effect": -0.05},
        {"name": "☀️ هوای عالی!", "desc": "هوا خوبه و مردم خوشحالن! ۱۰% سود!", "effect": 0.10},
        {"name": "❄️ برف سنگین!", "desc": "برف سنگین اومد! ۷% ضرر!", "effect": -0.07},
        {"name": "📈 رونق اقتصادی!", "desc": "اقتصاد بوم خورد! همه ۱۵% سود!", "effect": 0.15},
        {"name": "🎉 جشن ملی!", "desc": "جشن ملیه! دولت به همه ۲۰۰$ هدیه داد!", "effect": 200},
    ],
    "en": [
        {"name": "🌍 Earthquake!", "desc": "An earthquake hit! Everyone loses 10%!", "effect": -0.10},
        {"name": "🇮🇱➡️🇺🇸 Israel attacks USA!", "desc": "Markets crashed! Everyone loses 15%!", "effect": -0.15},
        {"name": "🇺🇸➡️🇮🇱 USA attacks Israel!", "desc": "Markets surged! Everyone gains 10%!", "effect": 0.10},
        {"name": "🇺🇸🇮🇱➡️🇮🇷 Joint attack on Iran!", "desc": "Economy collapsed! Everyone loses 20%!", "effect": -0.20},
        {"name": "💥 They are bombing!", "desc": "Somewhere is getting bombed! Markets volatile! 12% loss!", "effect": -0.12},
        {"name": "🚢 Navy deployed!", "desc": "Naval forces deployed! Tension rises! 8% loss!", "effect": -0.08},
        {"name": "🌧️ Heavy Rain!", "desc": "Heavy rain caused flooding! 5% loss!", "effect": -0.05},
        {"name": "☀️ Sunny Day!", "desc": "Beautiful weather! People are happy! 10% gain!", "effect": 0.10},
        {"name": "❄️ Heavy Snow!", "desc": "Heavy snowfall! 7% loss!", "effect": -0.07},
        {"name": "📈 Economic Boom!", "desc": "Economy is booming! Everyone gains 15%!", "effect": 0.15},
        {"name": "🎉 National Holiday!", "desc": "It's a holiday! Government gives everyone 200$!", "effect": 200},
    ],
}


# --------- /wallet ---------
def _display_name(user) -> str:
    return (user.full_name or user.first_name or "User").strip()


def _remember_user(chat_id: int, user):
    set_user_name(chat_id, user.id, _display_name(user))


async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    _remember_user(chat.id, user)
    bal = get_balance(chat.id, user.id)
    name = user.first_name or "User"
    await update.message.reply_text(
        s["wallet_balance"].format(user=name, balance=bal),
        parse_mode="Markdown",
    )


# --------- /daily ---------
async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    today = date.today().isoformat()
    last = get_daily_claim(chat.id, user.id)

    if last == today:
        await update.message.reply_text(s["daily_already"], parse_mode="Markdown")
        return

    # ── Streak system ──
    streak_data = get_daily_streak(chat.id, user.id)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if streak_data.get("last") == yesterday:
        streak = min(streak_data.get("count", 0) + 1, MAX_STREAK)
    else:
        streak = 1
    set_daily_streak(chat.id, user.id, {"count": streak, "last": today})
    streak_bonus = DAILY_STREAK_BONUS * (streak - 1)

    # ── Wealth tax (applied on daily claim) ──
    total_wealth = get_balance(chat.id, user.id)
    tax = 0
    for threshold, rate in reversed(WEALTH_TAX_BRACKETS):
        if total_wealth >= threshold:
            tax = int(total_wealth * rate)
            break

    total_reward = DAILY_AMOUNT + streak_bonus - tax
    new_bal = add_balance(chat.id, user.id, total_reward)
    set_daily_claim(chat.id, user.id, today)

    if lang == "fa":
        msg = (f"✅ *پاداش روزانه دریافت شد!*\n"
               f"💰 پایه: *{DAILY_AMOUNT}$*\n")
        if streak > 1:
            msg += f"🔥 استریک {streak} روزه: *+{streak_bonus}$*\n"
        if tax > 0:
            msg += f"🏛️ مالیات ثروت: *-{tax}$*\n"
        msg += f"💳 موجودی: *{new_bal}$*"
        if streak >= 3:
            msg += f"\n🔥 ادامه بده! {streak}/{MAX_STREAK}"
    else:
        msg = (f"✅ *Daily reward claimed!*\n"
               f"💰 Base: *{DAILY_AMOUNT}$*\n")
        if streak > 1:
            msg += f"🔥 {streak}-day streak: *+{streak_bonus}$*\n"
        if tax > 0:
            msg += f"🏛️ Wealth tax: *-{tax}$*\n"
        msg += f"💳 Balance: *{new_bal}$*"
        if streak >= 3:
            msg += f"\n🔥 Keep going! {streak}/{MAX_STREAK}"

    await update.message.reply_text(msg, parse_mode="Markdown")


# --------- /leaderboard ---------
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    balances = get_all_balances(chat.id)
    if not balances:
        await update.message.reply_text(s["lb_empty"], parse_mode="Markdown")
        return

    sorted_users = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, bal) in enumerate(sorted_users):
        uid_int = int(uid)
        name = get_user_name(chat.id, uid_int)
        try:
            member = await context.bot.get_chat_member(chat.id, uid_int)
            name = _display_name(member.user)
            set_user_name(chat.id, uid_int, name)
        except Exception:
            if not name:
                name = f"User {uid}"
        medal = medals[i] if i < 3 else f"*{i+1}.*"
        lines.append(f"{medal} {name} — *{bal}* $")

    header = s["lb_header"]
    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")


# --------- /bet (coin flip) ---------
async def bet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(s["bet_usage"], parse_mode="Markdown")
        return

    amount = int(context.args[0])
    if amount <= 0:
        await update.message.reply_text(s["bet_usage"], parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    won = random.random() < 0.45  # 45% win chance
    if won:
        winnings = amount
        new_bal = add_balance(chat.id, user.id, winnings)
        await update.message.reply_text(
            s["bet_win"].format(amount=winnings, balance=new_bal),
            parse_mode="Markdown",
        )
    else:
        new_bal = add_balance(chat.id, user.id, -amount)
        _process_casino_loss(chat.id, amount)
        await update.message.reply_text(
            s["bet_lose"].format(amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )


# --------- /slots (slot machine) — PIXEL ART MEGA UPGRADE ---------
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🔔", "⭐", "🍀"]

# Symbol weights (lower = rarer), payouts (3-match multiplier, 2-match multiplier)
SLOT_TABLE = {
    "💎": {"weight": 2,  "x3": 25, "x2": 3},
    "7️⃣": {"weight": 3,  "x3": 15, "x2": 2},
    "⭐": {"weight": 5,  "x3": 10, "x2": 2},
    "🔔": {"weight": 8,  "x3": 7,  "x2": 1.5},
    "🍇": {"weight": 12, "x3": 5,  "x2": 1},
    "🍊": {"weight": 15, "x3": 4,  "x2": 1},
    "🍒": {"weight": 18, "x3": 3,  "x2": 0.5},
    "🍋": {"weight": 20, "x3": 2,  "x2": 0.5},
    "🍀": {"weight": 10, "x3": 8,  "x2": 1.5},
}

# Build weighted pool
_SLOT_POOL = []
for sym, info in SLOT_TABLE.items():
    _SLOT_POOL.extend([sym] * info["weight"])


def _render_slot_machine(reels: list[str], bet: int, win: int, balance: int,
                         user_name: str, lang: str, jackpot: bool = False) -> io.BytesIO:
    """Render a pixel-art slot machine image."""
    W, H = 480, 360
    BG = (24, 24, 37)
    SURFACE = (30, 30, 46)
    OVERLAY = (49, 50, 68)
    GOLD = (249, 226, 175)
    RED = (243, 139, 168)
    GREEN = (166, 227, 161)
    BLUE = (137, 180, 250)
    PURPLE = (203, 166, 247)
    WHITE = (205, 214, 244)
    DARK = (17, 17, 27)
    PINK = (245, 194, 231)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = _get_font_econ(16)
    font_lg = _get_font_econ(22)
    font_sm = _get_font_econ(12)
    font_xl = _get_font_econ(36)

    # Starfield background
    rng = random.Random(42)
    for _ in range(80):
        sx, sy = rng.randint(0, W-1), rng.randint(0, H-1)
        b = rng.randint(60, 160)
        draw.point((sx, sy), fill=(b, b, b))

    # Machine body
    draw.rectangle([30, 20, W-30, H-40], fill=OVERLAY)
    draw.rectangle([32, 22, W-32, H-42], fill=SURFACE)
    # Top decorative bar
    draw.rectangle([30, 20, W-30, 50], fill=PURPLE)
    draw.rectangle([32, 22, W-32, 48], fill=(180, 140, 220))
    # Flashing lights on top
    colors = [RED, GOLD, GREEN, BLUE, PINK, RED, GOLD, GREEN, BLUE, PINK]
    for i, lx in enumerate(range(42, W-42, 40)):
        c = colors[i % len(colors)]
        draw.rectangle([lx, 24, lx+8, 32], fill=c)
        draw.rectangle([lx+1, 25, lx+7, 31], fill=tuple(min(255, v+60) for v in c))

    # Title
    title = "🎰 MEGA SLOTS 🎰" if lang == "en" else "🎰 مگا اسلات 🎰"
    tb = draw.textbbox((0, 0), title, font=font_lg)
    draw.text(((W - tb[2] + tb[0]) // 2, 54), title, fill=GOLD, font=font_lg)

    # Reel display area
    reel_y = 90
    reel_h = 100
    reel_w = 100
    gap = 20
    total_w = len(reels) * reel_w + (len(reels)-1) * gap
    start_x = (W - total_w) // 2

    # Reel background
    draw.rectangle([start_x - 10, reel_y - 10, start_x + total_w + 10, reel_y + reel_h + 10],
                    fill=DARK)
    draw.rectangle([start_x - 8, reel_y - 8, start_x + total_w + 8, reel_y + reel_h + 8],
                    fill=(40, 40, 55))

    # Draw each reel
    for i, sym in enumerate(reels):
        rx = start_x + i * (reel_w + gap)
        # Reel slot background
        draw.rectangle([rx, reel_y, rx + reel_w, reel_y + reel_h], fill=(20, 20, 30))
        draw.rectangle([rx+2, reel_y+2, rx+reel_w-2, reel_y+reel_h-2], fill=(35, 35, 50))
        # Inner highlight
        draw.line([rx+2, reel_y+2, rx+reel_w-2, reel_y+2], fill=(50, 50, 70))
        # Symbol text (centered)
        stb = draw.textbbox((0, 0), sym, font=font_xl)
        sw, sh = stb[2]-stb[0], stb[3]-stb[1]
        draw.text((rx + (reel_w - sw) // 2, reel_y + (reel_h - sh) // 2),
                  sym, fill=WHITE, font=font_xl)
        # Separator line
        if i < len(reels) - 1:
            draw.rectangle([rx + reel_w + gap//2 - 1, reel_y, rx + reel_w + gap//2 + 1, reel_y + reel_h],
                           fill=OVERLAY)

    # Pay line arrow
    arrow_y = reel_y + reel_h // 2
    draw.polygon([(start_x - 18, arrow_y - 6), (start_x - 8, arrow_y),
                  (start_x - 18, arrow_y + 6)], fill=RED)
    draw.polygon([(start_x + total_w + 18, arrow_y - 6), (start_x + total_w + 8, arrow_y),
                  (start_x + total_w + 18, arrow_y + 6)], fill=RED)

    # Result area
    result_y = reel_y + reel_h + 20
    if jackpot:
        # Jackpot celebration
        draw.rectangle([40, result_y, W-40, result_y + 40], fill=GOLD)
        draw.rectangle([42, result_y+2, W-42, result_y+38], fill=(200, 170, 80))
        jt = "💎 JACKPOT! 💎" if lang == "en" else "💎 جکپات! 💎"
        jtb = draw.textbbox((0, 0), jt, font=font_lg)
        draw.text(((W - jtb[2] + jtb[0]) // 2, result_y + 8), jt, fill=DARK, font=font_lg)
        # Explosion effect around jackpot
        for angle in range(0, 360, 20):
            rad = math.radians(angle)
            for r in range(50, 90, 8):
                px = int(W//2 + r * math.cos(rad))
                py = int(result_y + 20 + r * 0.4 * math.sin(rad))
                c = random.choice([GOLD, RED, PINK, GREEN])
                draw.rectangle([px, py, px+3, py+3], fill=c)
    elif win > 0:
        draw.rectangle([60, result_y, W-60, result_y + 35], fill=GREEN)
        draw.rectangle([62, result_y+2, W-62, result_y+33], fill=(120, 200, 120))
        wt = f"WIN +{win}$" if lang == "en" else f"برد +{win}$"
        wtb = draw.textbbox((0, 0), wt, font=font_lg)
        draw.text(((W - wtb[2] + wtb[0]) // 2, result_y + 5), wt, fill=DARK, font=font_lg)
    else:
        draw.rectangle([80, result_y, W-80, result_y + 30], fill=RED)
        draw.rectangle([82, result_y+2, W-82, result_y+28], fill=(180, 100, 100))
        lt = f"LOST -{bet}$" if lang == "en" else f"باخت -{bet}$"
        ltb = draw.textbbox((0, 0), lt, font=font)
        draw.text(((W - ltb[2] + ltb[0]) // 2, result_y + 5), lt, fill=WHITE, font=font)

    # Info bar at bottom
    info_y = H - 60
    draw.rectangle([30, info_y, W-30, H-20], fill=OVERLAY)
    draw.rectangle([32, info_y+2, W-32, H-22], fill=SURFACE)

    name_short = user_name[:16] if len(user_name) > 16 else user_name
    if lang == "fa":
        info = f"👤 {name_short}  |  🎲 شرط: {bet}$  |  💰 موجودی: {balance}$"
    else:
        info = f"👤 {name_short}  |  🎲 Bet: {bet}$  |  💰 Balance: {balance}$"
    draw.text((44, info_y + 8), info, fill=WHITE, font=font_sm)

    # Machine decorative bolts
    for bx, by in [(36, 26), (W-44, 26), (36, H-48), (W-44, H-48)]:
        draw.ellipse([bx, by, bx+6, by+6], fill=(100, 100, 110))
        draw.point((bx+3, by+2), fill=(160, 160, 170))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    amount = 50  # default bet
    if context.args and context.args[0].isdigit():
        amount = int(context.args[0])

    if amount <= 0:
        await update.message.reply_text(s["bet_usage"], parse_mode="Markdown")
        return

    if amount > 5000:
        msg = "❌ حداکثر شرط *5000$* است." if lang == "fa" else "❌ Max bet is *5000$*."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    # Spin 3 reels from weighted pool
    s1 = random.choice(_SLOT_POOL)
    s2 = random.choice(_SLOT_POOL)
    s3 = random.choice(_SLOT_POOL)
    reels = [s1, s2, s3]

    is_jackpot = False
    if s1 == s2 == s3:
        # JACKPOT — all 3 match!
        mult = SLOT_TABLE[s1]["x3"]
        winnings = amount * mult
        is_jackpot = (s1 in ("💎", "7️⃣", "⭐"))
        new_bal = add_balance(chat.id, user.id, winnings)
        u_name = (user.first_name or "User")

        buf = _render_slot_machine(reels, amount, winnings, new_bal, u_name, lang, jackpot=is_jackpot)
        if lang == "fa":
            caption = f"🎰 *{'💎 جکپات!' if is_jackpot else 'سه‌تایی!'}* +{winnings}$ ({mult}x)\n💰 موجودی: *{new_bal}$*"
        else:
            caption = f"🎰 *{'💎 JACKPOT!' if is_jackpot else 'Triple Match!'}* +{winnings}$ ({mult}x)\n💰 Balance: *{new_bal}$*"
        await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")

    elif s1 == s2 or s2 == s3 or s1 == s3:
        # Two match
        matched = s1 if s1 == s2 else (s2 if s2 == s3 else s1)
        mult = SLOT_TABLE[matched]["x2"]
        winnings = int(amount * mult)
        new_bal = add_balance(chat.id, user.id, winnings)
        u_name = (user.first_name or "User")

        buf = _render_slot_machine(reels, amount, winnings, new_bal, u_name, lang)
        if lang == "fa":
            caption = f"🎰 دوتایی! +{winnings}$ ({mult}x)\n💰 موجودی: *{new_bal}$*"
        else:
            caption = f"🎰 Two match! +{winnings}$ ({mult}x)\n💰 Balance: *{new_bal}$*"
        await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")

    else:
        # Loss
        new_bal = add_balance(chat.id, user.id, -amount)
        _process_casino_loss(chat.id, amount)
        u_name = (user.first_name or "User")

        buf = _render_slot_machine(reels, amount, 0, new_bal, u_name, lang)
        if lang == "fa":
            caption = f"🎰 باختی! -{amount}$\n💰 موجودی: *{new_bal}$*"
        else:
            caption = f"🎰 You lost! -{amount}$\n💰 Balance: *{new_bal}$*"
        await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# --------- /dice (roll 1-6, bet odd/even or number) ---------
async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    if len(context.args) < 2:
        await update.message.reply_text(s["dice_usage"], parse_mode="Markdown")
        return

    guess = context.args[0].lower()
    if not context.args[1].isdigit():
        await update.message.reply_text(s["dice_usage"], parse_mode="Markdown")
        return

    amount = int(context.args[1])
    if amount <= 0:
        await update.message.reply_text(s["dice_usage"], parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    roll = random.randint(1, 6)
    # roll=6
    dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    dice_display = dice_faces[roll]

    won = False
    multiplier = 1

    odd_words = ("odd", "فرد", "tek")
    even_words = ("even", "زوج", "juft")

    if guess in odd_words:
        won = roll % 2 == 1
        multiplier = 1
    elif guess in even_words:
        won = roll % 2 == 0
        multiplier = 1
    elif guess.isdigit() and 1 <= int(guess) <= 6:
        won = roll == int(guess)
        multiplier = 4
    else:
        await update.message.reply_text(s["dice_usage"], parse_mode="Markdown")
        return

    if won:
        winnings = amount * multiplier
        new_bal = add_balance(chat.id, user.id, winnings)
        await update.message.reply_text(
            s["dice_win"].format(dice=dice_display, roll=roll, winnings=winnings, balance=new_bal),
            parse_mode="Markdown",
        )
    else:
        new_bal = add_balance(chat.id, user.id, -amount)
        _process_casino_loss(chat.id, amount)
        await update.message.reply_text(
            s["dice_lose"].format(dice=dice_display, roll=roll, amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )


# --------- Jail check helper ---------
def _check_jail(chat_id: int, user_id: int) -> int | None:
    """Returns remaining seconds in jail, or None if free.
    Supports extended format 'ISO|duration_secs' for special jail durations.
    """
    jt = get_jail_time(chat_id, user_id)
    if not jt:
        return None
    # Parse optional duration suffix  e.g. "2026-02-12T21:28:44|900"
    duration = JAIL_DURATION
    ts = jt
    if "|" in jt:
        ts, dur_str = jt.rsplit("|", 1)
        try:
            duration = int(dur_str)
        except ValueError:
            pass
    try:
        jail_dt = datetime.fromisoformat(ts)
    except ValueError:
        clear_jail(chat_id, user_id)
        return None
    diff = (datetime.utcnow() - jail_dt).total_seconds()
    if diff >= duration:
        clear_jail(chat_id, user_id)
        return None
    return int(duration - diff)


# --------- /rob (steal from someone) ---------
async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    # Check jail
    remaining = _check_jail(chat.id, user.id)
    if remaining is not None:
        mins = remaining // 60
        secs = remaining % 60
        await update.message.reply_text(
            s["jail_still_jailed"].format(mins=mins, secs=secs),
            parse_mode="Markdown",
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(s["rob_usage"], parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    _remember_user(chat.id, target)
    if target.id == user.id or target.is_bot:
        await update.message.reply_text(s["rob_usage"], parse_mode="Markdown")
        return

    my_bal = get_balance(chat.id, user.id)
    target_bal = get_balance(chat.id, target.id)

    if target_bal < 50:
        await update.message.reply_text(
            s["rob_poor"].format(user=target.first_name or "User"), parse_mode="Markdown"
        )
        return

    # --- Special punishment: robbing the protected user ---
    if target.id == DUNGEON_VICTIM_ID:
        add_balance(chat.id, user.id, -DUNGEON_FINE)
        set_jail_time(chat.id, user.id, f"{datetime.utcnow().isoformat()}|{DUNGEON_JAIL_DURATION}")
        mock = random.choice(DUNGEON_MOCKS[lang])
        bal_now = get_balance(chat.id, user.id)
        txt = (
            f"{mock}\n\n"
            f"💸 جریمه ویژه: *{DUNGEON_FINE}$*\n"
            f"⏳ زندان: *۱۵ دقیقه*\n"
            f"💰 موجودی: *{bal_now}* $"
        ) if lang == "fa" else (
            f"{mock}\n\n"
            f"💸 Special fine: *{DUNGEON_FINE}$*\n"
            f"⏳ Jail: *15 minutes*\n"
            f"💰 Balance: *{bal_now}* $"
        )
        await update.message.reply_text(txt, parse_mode="Markdown")
        try:
            sticker = random.choice(DUNGEON_STICKERS)
            await update.message.reply_sticker(sticker)
        except Exception:
            pass
        return

    # --- Protection items ---
    if has_item(chat.id, target.id, "landmine"):
        remove_inventory_item(chat.id, target.id, "landmine")
        fine = random.randint(100, 300)
        add_balance(chat.id, user.id, -fine)
        set_jail_time(chat.id, user.id, datetime.utcnow().isoformat())
        bal_now = get_balance(chat.id, user.id)
        if lang == "fa":
            txt = (
                f"💥 *بووووم!* {target.first_name} مین کار گذاشته بود!\n\n"
                f"💸 جریمه: *{fine}$*\n"
                f"⛓️ زندانی شدی!\n"
                f"💰 موجودی: *{bal_now}$*"
            )
        else:
            txt = (
                f"💥 *BOOM!* {target.first_name} had a landmine!\n\n"
                f"💸 Fine: *{fine}$*\n"
                f"⛓️ You're jailed!\n"
                f"💰 Balance: *{bal_now}$*"
            )
        await update.message.reply_text(txt, parse_mode="Markdown")
        return

    if has_item(chat.id, target.id, "shield"):
        remove_inventory_item(chat.id, target.id, "shield")
        if lang == "fa":
            txt = (
                f"🛡️ *{target.first_name}* سپر داشت!\n\n"
                f"🚫 سرقت ناموفق بود! سپر مصرف شد."
            )
        else:
            txt = (
                f"🛡️ *{target.first_name}* had a shield!\n\n"
                f"🚫 Rob blocked! Shield consumed."
            )
        await update.message.reply_text(txt, parse_mode="Markdown")
        return

    success = random.random() < 0.35  # 35% success
    if success:
        stolen = random.randint(10, min(200, target_bal // 3))
        add_balance(chat.id, user.id, stolen)
        add_balance(chat.id, target.id, -stolen)
        bounty = remove_bounty(chat.id, target.id)
        bounty_text = ""
        if bounty:
            bounty_amt = bounty["amount"]
            add_balance(chat.id, user.id, bounty_amt)
            bounty_text = (f"\n🎯 *بانتی {bounty_amt}$ هم گرفتی!*" if lang == "fa"
                           else f"\n🎯 *Bounty {bounty_amt}$ collected!*")
        await update.message.reply_text(
            s["rob_success"].format(
                amount=stolen, user=target.first_name or "User",
                balance=get_balance(chat.id, user.id)
            ) + bounty_text,
            parse_mode="Markdown",
        )
    else:
        # Go to jail!
        fine = random.randint(20, min(100, my_bal // 4)) if my_bal > 20 else 0
        if fine > 0:
            add_balance(chat.id, user.id, -fine)
        set_jail_time(chat.id, user.id, datetime.utcnow().isoformat())
        mock = random.choice(JAIL_MOCKS[lang])
        await update.message.reply_text(
            f"{mock}\n\n💸 جریمه: *{fine}$*\n💰 موجودی: *{get_balance(chat.id, user.id)}* $"
            if lang == "fa" else
            f"{mock}\n\n💸 Fine: *{fine}$*\n💰 Balance: *{get_balance(chat.id, user.id)}* $",
            parse_mode="Markdown",
        )


# --------- /give (transfer money) ---------
async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    if not update.message.reply_to_message or not context.args or not context.args[0].isdigit():
        await update.message.reply_text(s["give_usage"], parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    _remember_user(chat.id, target)
    if target.id == user.id or target.is_bot:
        return

    amount = int(context.args[0])
    if amount <= 0:
        return

    # Calculate transfer tax
    tax = 0
    if amount > TRANSFER_TAX_THRESHOLD:
        tax = int(amount * TRANSFER_TAX_RATE)
    total_cost = amount + tax

    bal = get_balance(chat.id, user.id)
    if total_cost > bal:
        if lang == "fa":
            msg = f"❌ موجودی کافی نیست! نیاز: *{total_cost}$* (مبلغ + {tax}$ مالیات)\nموجودی: *{bal}$*"
        else:
            msg = f"❌ Not enough balance! Need: *{total_cost}$* (amount + {tax}$ tax)\nBalance: *{bal}$*"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -total_cost)
    add_balance(chat.id, target.id, amount)

    if tax > 0:
        if lang == "fa":
            msg = (f"✅ *{amount}$* به *{target.first_name or 'User'}* ارسال شد.\n"
                   f"🏛️ مالیات انتقال: *{tax}$*\n"
                   f"💳 موجودی: *{get_balance(chat.id, user.id)}$*")
        else:
            msg = (f"✅ Sent *{amount}$* to *{target.first_name or 'User'}*.\n"
                   f"🏛️ Transfer tax: *{tax}$*\n"
                   f"💳 Balance: *{get_balance(chat.id, user.id)}$*")
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            s["give_done"].format(
                amount=amount,
                user=target.first_name or "User",
                balance=get_balance(chat.id, user.id),
            ),
            parse_mode="Markdown",
        )


# --------- /rps (rock paper scissors) ---------
async def rps_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    if len(context.args) < 2:
        await update.message.reply_text(s["rps_usage"], parse_mode="Markdown")
        return

    choice = context.args[0].lower()
    if not context.args[1].isdigit():
        await update.message.reply_text(s["rps_usage"], parse_mode="Markdown")
        return

    amount = int(context.args[1])
    if amount <= 0:
        await update.message.reply_text(s["rps_usage"], parse_mode="Markdown")
        return

    # Normalize choice
    rps_map = {
        "rock": "rock", "سنگ": "rock", "r": "rock", "🪨": "rock",
        "paper": "paper", "کاغذ": "paper", "p": "paper", "📄": "paper",
        "scissors": "scissors", "قیچی": "scissors", "s": "scissors", "✂️": "scissors",
    }
    player = rps_map.get(choice)
    if not player:
        await update.message.reply_text(s["rps_usage"], parse_mode="Markdown")
        return

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    bot_choice = random.choice(["rock", "paper", "scissors"])
    emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    pe = emojis[player]
    be = emojis[bot_choice]

    if player == bot_choice:
        await update.message.reply_text(
            s["rps_draw"].format(you=pe, bot=be, balance=bal),
            parse_mode="Markdown",
        )
    elif (player == "rock" and bot_choice == "scissors") or \
         (player == "paper" and bot_choice == "rock") or \
         (player == "scissors" and bot_choice == "paper"):
        new_bal = add_balance(chat.id, user.id, amount)
        await update.message.reply_text(
            s["rps_win"].format(you=pe, bot=be, amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )
    else:
        new_bal = add_balance(chat.id, user.id, -amount)
        _process_casino_loss(chat.id, amount)
        await update.message.reply_text(
            s["rps_lose"].format(you=pe, bot=be, amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )


# --------- /work (earn money, 1-hour cooldown) ---------
async def work_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    last = get_last_work(chat.id, user.id)
    now = datetime.utcnow()

    if last:
        last_dt = datetime.fromisoformat(last)
        diff = (now - last_dt).total_seconds()
        if diff < WORK_COOLDOWN:
            remaining = int(WORK_COOLDOWN - diff)
            mins = remaining // 60
            secs = remaining % 60
            await update.message.reply_text(
                s["work_cooldown"].format(mins=mins, secs=secs),
                parse_mode="Markdown",
            )
            return

    # Work XP & level
    xp = get_work_xp(chat.id, user.id)
    level = xp // WORK_XP_PER_LEVEL
    bonus_mult = 1.0 + (level * WORK_BONUS_PER_LEVEL)

    job_name, min_pay, max_pay = random.choice(JOBS[lang])
    base_earned = random.randint(min_pay, max_pay)
    earned = int(base_earned * bonus_mult)
    new_bal = add_balance(chat.id, user.id, earned)
    set_last_work(chat.id, user.id, now.isoformat())
    new_xp = add_work_xp(chat.id, user.id, WORK_XP_PER_JOB)
    new_level = new_xp // WORK_XP_PER_LEVEL

    if lang == "fa":
        msg = (f"💼 *{job_name}*\n"
               f"💰 درآمد: *{earned}$*")
        if level > 0:
            msg += f" (x{bonus_mult:.1f} سطح {level})"
        msg += f"\n💳 موجودی: *{new_bal}$*"
        msg += f"\n⭐ XP: *{new_xp}* (سطح {new_level})"
        if new_level > level:
            msg += f"\n🎉 *ارتقا به سطح {new_level}!* درآمد +{int(WORK_BONUS_PER_LEVEL*100)}%"
    else:
        msg = (f"💼 *{job_name}*\n"
               f"💰 Earned: *{earned}$*")
        if level > 0:
            msg += f" (x{bonus_mult:.1f} Lv.{level})"
        msg += f"\n💳 Balance: *{new_bal}$*"
        msg += f"\n⭐ XP: *{new_xp}* (Level {new_level})"
        if new_level > level:
            msg += f"\n🎉 *Level up to {new_level}!* Pay +{int(WORK_BONUS_PER_LEVEL*100)}%"

    await update.message.reply_text(msg, parse_mode="Markdown")


# --------- /spin (wheel, 8-hour cooldown) ---------
async def spin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    last = get_last_spin(chat.id, user.id)
    now = datetime.utcnow()

    if last:
        last_dt = datetime.fromisoformat(last)
        diff = (now - last_dt).total_seconds()
        if diff < SPIN_COOLDOWN:
            remaining = int(SPIN_COOLDOWN - diff)
            hours = remaining // 3600
            mins = (remaining % 3600) // 60
            await update.message.reply_text(
                s["spin_cooldown"].format(hours=hours, mins=mins),
                parse_mode="Markdown",
            )
            return

    amounts, emojis, weights = zip(*SPIN_REWARDS)
    idx = random.choices(range(len(SPIN_REWARDS)), weights=weights, k=1)[0]
    amount = amounts[idx]
    emoji = emojis[idx]

    new_bal = add_balance(chat.id, user.id, amount)
    set_last_spin(chat.id, user.id, now.isoformat())

    if amount > 0:
        await update.message.reply_text(
            s["spin_win"].format(emoji=emoji, amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )
    elif amount == 0:
        await update.message.reply_text(
            s["spin_nothing"].format(emoji=emoji, balance=new_bal),
            parse_mode="Markdown",
        )
    else:
        _process_casino_loss(chat.id, abs(amount))
        await update.message.reply_text(
            s["spin_lose"].format(emoji=emoji, amount=abs(amount), balance=new_bal),
            parse_mode="Markdown",
        )


# --------- Stock price helper ---------
def _get_price(ticker: str) -> int:
    """Deterministic-ish daily price with random swing."""
    base = COMPANIES[ticker]["base"]
    day_seed = date.today().toordinal() + hash(ticker) % 9999
    rng = random.Random(day_seed)
    swing = rng.uniform(-0.30, 0.40)
    return max(10, int(base * (1 + swing)))


def _get_font_econ(size: int) -> ImageFont.FreeTypeFont:
    for p in ["C:\\Windows\\Fonts\\tahoma.ttf",
              "C:\\Windows\\Fonts\\arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _render_stock_chart(ticker: str) -> io.BytesIO:
    """Render an enhanced 30-day price chart for a stock ticker with pixel art style."""
    today_ord = date.today().toordinal()
    prices = []
    for i in range(30):
        day_ord = today_ord - 29 + i
        base = COMPANIES[ticker]["base"]
        day_seed = day_ord + hash(ticker) % 9999
        rng = random.Random(day_seed)
        swing = rng.uniform(-0.30, 0.40)
        prices.append(max(10, int(base * (1 + swing))))

    W, H = 640, 380
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 30, 70, 55
    BG = (24, 24, 37)
    SURFACE = (30, 30, 46)
    GRID = (45, 45, 62)
    TEXT_CLR = (205, 214, 244)
    TITLE_CLR = (137, 180, 250)
    GOLD = (249, 226, 175)
    GREEN = (166, 227, 161)
    RED = (243, 139, 168)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = _get_font_econ(13)
    font_title = _get_font_econ(18)
    font_sm = _get_font_econ(11)
    font_lg = _get_font_econ(16)

    # Background panel
    draw.rectangle([5, 5, W-5, H-5], fill=SURFACE)

    # Starfield
    rng_stars = random.Random(hash(ticker))
    for _ in range(50):
        sx, sy = rng_stars.randint(0, W), rng_stars.randint(0, 50)
        draw.point((sx, sy), fill=(80, 80, 100))

    # Title bar
    draw.rectangle([5, 5, W-5, 55], fill=(49, 50, 68))
    sector = COMPANIES[ticker].get("sector", "")
    title = f"{COMPANIES[ticker]['name']} ({ticker})"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text((15, 12), title, fill=TITLE_CLR, font=font_title)

    # Sector badge
    if sector:
        badge_colors = {"tech": (137, 180, 250), "crypto": (249, 226, 175),
                        "auto": (166, 227, 161), "retail": (203, 166, 247),
                        "social": (245, 194, 231), "media": (148, 226, 213)}
        bc = badge_colors.get(sector, TEXT_CLR)
        draw.rounded_rectangle([W - 100, 15, W - 15, 35], radius=6, fill=bc)
        draw.text((W - 95, 17), sector.upper(), fill=(17, 17, 27), font=font_sm)

    # Price + change in title
    cp = prices[-1]
    change = cp - prices[0]
    pct = (change / prices[0] * 100) if prices[0] else 0
    sign = "+" if change >= 0 else ""
    trend_clr = GREEN if change >= 0 else RED
    price_text = f"${cp} ({sign}{change}, {sign}{pct:.1f}%)"
    draw.text((15, 36), price_text, fill=trend_clr, font=font_lg)

    min_p = min(prices) - 10
    max_p = max(prices) + 10
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    # Grid lines
    for i in range(5):
        y = PAD_T + int(chart_h * i / 4)
        draw.line([(PAD_L, y), (W - PAD_R, y)], fill=GRID, width=1)
        val = max_p - (max_p - min_p) * i / 4
        draw.text((5, y - 7), f"${int(val)}", fill=TEXT_CLR, font=font_sm)

    # Plot points
    points = []
    for i, p in enumerate(prices):
        x = PAD_L + int(chart_w * i / 29)
        y = PAD_T + int(chart_h * (max_p - p) / (max_p - min_p))
        points.append((x, y))

    # Gradient fill under line
    bottom = PAD_T + chart_h
    fill_clr = (40, 70, 50) if change >= 0 else (70, 40, 45)
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        draw.polygon([(x1, y1), (x2, y2), (x2, bottom), (x1, bottom)], fill=fill_clr)

    # Line
    draw.line(points, fill=trend_clr, width=2)

    # Day bars along bottom (mini candlestick feel)
    bar_w = max(2, chart_w // 35)
    for i in range(1, len(prices)):
        x = PAD_L + int(chart_w * i / 29)
        prev_p = prices[i - 1]
        cur_p = prices[i]
        bar_clr = GREEN if cur_p >= prev_p else RED
        bar_h = min(abs(cur_p - prev_p) * chart_h // max(max_p - min_p, 1), 20)
        draw.rectangle([x - bar_w//2, bottom + 3, x + bar_w//2, bottom + 3 + max(bar_h, 2)],
                       fill=bar_clr)

    # Highlight dots  
    for idx in [0, len(points) - 1]:
        px, py = points[idx]
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=trend_clr)
        draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 255, 255))

    # High/Low markers
    max_idx = prices.index(max(prices))
    min_idx = prices.index(min(prices))
    if max_idx < len(points):
        hx, hy = points[max_idx]
        draw.text((hx - 8, hy - 16), f"H${max(prices)}", fill=GREEN, font=font_sm)
    if min_idx < len(points):
        lx, ly = points[min_idx]
        draw.text((lx - 8, ly + 6), f"L${min(prices)}", fill=RED, font=font_sm)

    # Bottom info bar
    draw.rectangle([5, H - 30, W - 5, H - 5], fill=(49, 50, 68))
    info = f"30D Range: ${min(prices)}-${max(prices)} | Avg: ${sum(prices)//len(prices)} | Vol: {sector}"
    draw.text((12, H - 25), info, fill=TEXT_CLR, font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# --------- /invest (buy stock) ---------
async def invest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    # /invest  → show all companies & prices grouped by sector
    if not context.args:
        sectors = {}
        for ticker, info in COMPANIES.items():
            sec = info.get("sector", "other")
            sectors.setdefault(sec, []).append((ticker, info))

        sector_emojis = {"tech": "💻", "crypto": "₿", "auto": "🚗", "retail": "📦",
                         "social": "👥", "media": "🎬"}
        lines = []
        for sec, items in sectors.items():
            emoji = sector_emojis.get(sec, "📊")
            lines.append(f"\n{emoji} *{sec.upper()}:*")
            for ticker, info in items:
                price = _get_price(ticker)
                lines.append(f"  📊 *{ticker}* — {info['name']} — *{price}$*/share")

        header = s["invest_list"]
        footer = "\n\n💡 `/invest TSLA chart` — نمودار" if lang == "fa" else "\n\n💡 `/invest TSLA chart` — Show chart"
        await update.message.reply_text(
            header + "\n".join(lines) + footer, parse_mode="Markdown"
        )
        return

    # /invest <ticker> chart → show chart image
    if len(context.args) == 2 and context.args[1].lower() in ("tree", "chart"):
        ticker = context.args[0].upper()
        if ticker not in COMPANIES:
            await update.message.reply_text(s["invest_usage"], parse_mode="Markdown")
            return
        buf = _render_stock_chart(ticker)
        await update.message.reply_photo(photo=buf, caption=f"📊 {COMPANIES[ticker]['name']} — 30 Day Chart")
        return

    # /invest <ticker> <shares>
    if len(context.args) < 2 or not context.args[1].isdigit():
        await update.message.reply_text(s["invest_usage"], parse_mode="Markdown")
        return

    ticker = context.args[0].upper()
    shares = int(context.args[1])

    if ticker not in COMPANIES or shares <= 0:
        await update.message.reply_text(s["invest_usage"], parse_mode="Markdown")
        return

    price = _get_price(ticker)
    cost = price * shares
    bal = get_balance(chat.id, user.id)

    if cost > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    add_balance(chat.id, user.id, -cost)
    stocks = get_stocks(chat.id, user.id)
    stocks[ticker] = stocks.get(ticker, 0) + shares
    set_stocks(chat.id, user.id, stocks)

    # Track cost basis
    costs = get_stock_costs(chat.id, user.id)
    costs[ticker] = costs.get(ticker, 0) + cost
    set_stock_costs(chat.id, user.id, costs)

    await update.message.reply_text(
        s["invest_bought"].format(
            shares=shares, company=COMPANIES[ticker]["name"],
            cost=cost, balance=get_balance(chat.id, user.id)
        ),
        parse_mode="Markdown",
    )


# --------- /sell (sell stock) ---------
async def sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    if len(context.args) < 2 or not context.args[1].isdigit():
        await update.message.reply_text(s["sell_usage"], parse_mode="Markdown")
        return

    ticker = context.args[0].upper()
    shares = int(context.args[1])

    if ticker not in COMPANIES or shares <= 0:
        await update.message.reply_text(s["sell_usage"], parse_mode="Markdown")
        return

    stocks = get_stocks(chat.id, user.id)
    owned = stocks.get(ticker, 0)

    if shares > owned:
        await update.message.reply_text(
            s["sell_not_enough"].format(owned=owned, ticker=ticker),
            parse_mode="Markdown",
        )
        return

    price = _get_price(ticker)
    revenue = price * shares
    add_balance(chat.id, user.id, revenue)
    stocks[ticker] = owned - shares
    if stocks[ticker] == 0:
        del stocks[ticker]
    set_stocks(chat.id, user.id, stocks)

    # Reduce cost basis proportionally
    costs = get_stock_costs(chat.id, user.id)
    if ticker in costs and owned > 0:
        cost_per_share = costs[ticker] / owned
        costs[ticker] = max(0, int(costs[ticker] - cost_per_share * shares))
        if stocks.get(ticker, 0) == 0:
            costs.pop(ticker, None)
        set_stock_costs(chat.id, user.id, costs)

    await update.message.reply_text(
        s["sell_done"].format(
            shares=shares, company=COMPANIES[ticker]["name"],
            revenue=revenue, balance=get_balance(chat.id, user.id)
        ),
        parse_mode="Markdown",
    )


# --------- /portfolio ---------
async def portfolio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    stocks = get_stocks(chat.id, user.id)
    if not stocks:
        await update.message.reply_text(s["portfolio_empty"], parse_mode="Markdown")
        return

    lines = []
    total_value = 0
    for ticker, shares in stocks.items():
        if ticker not in COMPANIES:
            continue
        price = _get_price(ticker)
        value = price * shares
        total_value += value
        lines.append(
            f"📊 *{ticker}* — {shares} shares × {price}$ = *{value}$*"
        )

    bal = get_balance(chat.id, user.id)
    header = s["portfolio_header"]
    footer = s["portfolio_footer"].format(total=total_value, balance=bal, net=total_value + bal)
    await update.message.reply_text(
        header + "\n".join(lines) + "\n\n" + footer,
        parse_mode="Markdown",
    )


# --------- /event (daily random event) ---------
async def event_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    today = date.today().isoformat()
    evt = get_daily_event(chat.id)

    # Already rolled today
    if evt and evt.get("date") == today:
        if evt.get("happened"):
            await update.message.reply_text(
                s["event_today"].format(name=evt["name"], desc=evt["desc"]),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(s["event_none_today"], parse_mode="Markdown")
        return

    # Roll for today (20% chance)
    if random.random() < 0.20:
        events = DAILY_EVENTS[lang]
        chosen = random.choice(events)
        effect = chosen["effect"]

        # Apply effect to all wallets
        all_bals = get_all_balances(chat.id)
        affected = 0
        for uid, bal in all_bals.items():
            if isinstance(effect, float):
                change = int(bal * effect)
            else:
                change = int(effect)
            add_balance(chat.id, int(uid), change)
            affected += 1

        set_daily_event(chat.id, {
            "date": today, "happened": True,
            "name": chosen["name"], "desc": chosen["desc"],
            "effect": effect,
        })

        await update.message.reply_text(
            s["event_happened"].format(
                name=chosen["name"], desc=chosen["desc"], affected=affected
            ),
            parse_mode="Markdown",
        )
    else:
        set_daily_event(chat.id, {"date": today, "happened": False, "name": "", "desc": ""})
        await update.message.reply_text(s["event_none_today"], parse_mode="Markdown")


# --------- /jail (list jailed users) ---------
async def jail_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    jailed = get_all_jailed(chat.id)
    if not jailed:
        await update.message.reply_text(s["jail_empty"], parse_mode="Markdown")
        return

    lines = []
    now = datetime.utcnow()
    for uid_str, ts in jailed.items():
        # Parse optional duration suffix
        duration = JAIL_DURATION
        raw_ts = ts
        if "|" in ts:
            raw_ts, dur_str = ts.rsplit("|", 1)
            try:
                duration = int(dur_str)
            except ValueError:
                pass
        try:
            jail_dt = datetime.fromisoformat(raw_ts)
        except ValueError:
            continue
        diff = (now - jail_dt).total_seconds()
        remaining = duration - diff
        if remaining <= 0:
            continue
        mins = int(remaining) // 60
        secs = int(remaining) % 60
        uid_int = int(uid_str)
        name = get_user_name(chat.id, uid_int)
        if not name:
            try:
                member = await context.bot.get_chat_member(chat.id, uid_int)
                name = _display_name(member.user)
            except Exception:
                name = f"User {uid_str}"
        lines.append(f"⛓️ *{name}* — {mins}m {secs}s")

    if not lines:
        await update.message.reply_text(s["jail_empty"], parse_mode="Markdown")
        return

    header = s["jail_header"]
    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")


# --------- /profit (investment profit/loss) ---------
async def profit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    stocks = get_stocks(chat.id, user.id)
    costs = get_stock_costs(chat.id, user.id)

    if not stocks:
        await update.message.reply_text(s["portfolio_empty"], parse_mode="Markdown")
        return

    lines = []
    total_cost = 0
    total_value = 0
    for ticker, shares in stocks.items():
        if ticker not in COMPANIES:
            continue
        price = _get_price(ticker)
        value = price * shares
        cost = costs.get(ticker, 0)
        pnl = value - cost
        total_cost += cost
        total_value += value
        emoji = "📈" if pnl >= 0 else "📉"
        sign = "+" if pnl >= 0 else ""
        lines.append(f"{emoji} *{ticker}* — {shares} shares | Cost: {cost}$ | Value: {value}$ | P/L: *{sign}{pnl}$*")

    total_pnl = total_value - total_cost
    sign = "+" if total_pnl >= 0 else ""
    emoji = "🟢" if total_pnl >= 0 else "🔴"

    header = s["profit_header"]
    footer = s["profit_footer"].format(cost=total_cost, value=total_value, pnl=f"{sign}{total_pnl}", emoji=emoji)
    await update.message.reply_text(
        header + "\n".join(lines) + "\n\n" + footer,
        parse_mode="Markdown",
    )


# ═══════════════════════════════════════════════════
# /fish — Fishing mini-game (cooldown: 30 min)
# ═══════════════════════════════════════════════════
FISH_COOLDOWN = 1800  # 30 minutes

FISH_CATCHES = {
    "fa": [
        ("🐟 ماهی کوچک", 20, 35),
        ("🐠 ماهی استوایی", 40, 20),
        ("🐡 بادکنک‌ماهی", 60, 15),
        ("🦐 میگو", 30, 25),
        ("🦀 خرچنگ", 80, 10),
        ("🐙 اختاپوس", 120, 5),
        ("🦈 کوسه!", 250, 3),
        ("👢 کفش کهنه", 0, 15),
        ("🗑️ زباله", -10, 10),
        ("💎 گنج دریایی!", 500, 2),
        ("🐋 نهنگ!", 400, 3),
        ("🪸 مرجان زیبا", 50, 12),
    ],
    "en": [
        ("🐟 Small Fish", 20, 35),
        ("🐠 Tropical Fish", 40, 20),
        ("🐡 Pufferfish", 60, 15),
        ("🦐 Shrimp", 30, 25),
        ("🦀 Crab", 80, 10),
        ("🐙 Octopus", 120, 5),
        ("🦈 Shark!", 250, 3),
        ("👢 Old Boot", 0, 15),
        ("🗑️ Trash", -10, 10),
        ("💎 Sea Treasure!", 500, 2),
        ("🐋 Whale!", 400, 3),
        ("🪸 Coral", 50, 12),
    ],
}


def _render_fish_scene(catch_name: str, reward: int, user_name: str, balance: int, lang: str) -> io.BytesIO:
    W, H = 400, 280
    img = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    font = _get_font_econ(14)
    font_lg = _get_font_econ(20)
    font_sm = _get_font_econ(11)

    # Sky gradient
    for y in range(80):
        r = int(15 + y * 0.4)
        g = int(23 + y * 0.8)
        b = int(42 + y * 1.2)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Stars
    rng = random.Random(42)
    for _ in range(30):
        sx, sy = rng.randint(0, W), rng.randint(0, 60)
        draw.point((sx, sy), fill=(200, 200, 220))

    # Water
    for y in range(80, H):
        r = int(20 + (y - 80) * 0.15)
        g = int(50 + (y - 80) * 0.4)
        b = int(120 + min((y - 80) * 0.3, 60))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Waves
    for x in range(0, W, 20):
        draw.arc([x, 75, x + 20, 88], start=0, end=180, fill=(100, 180, 240), width=2)

    # Fishing rod
    draw.line([(50, 10), (50, 75)], fill=(139, 90, 43), width=3)
    draw.line([(50, 10), (180, 10)], fill=(139, 90, 43), width=2)
    draw.line([(180, 10), (180, 140)], fill=(180, 180, 180), width=1)
    draw.ellipse([176, 138, 184, 146], fill=(200, 200, 200))

    # Catch display
    ctb = draw.textbbox((0, 0), catch_name, font=font_lg)
    draw.text(((W - ctb[2] + ctb[0]) // 2, 160), catch_name, fill=(249, 226, 175), font=font_lg)

    # Reward
    if reward > 0:
        rt = f"+{reward}$" if lang == "en" else f"+{reward}$"
        draw.text(((W - draw.textbbox((0,0), rt, font=font_lg)[2]) // 2, 190),
                  rt, fill=(166, 227, 161), font=font_lg)
    elif reward < 0:
        rt = f"{reward}$"
        draw.text(((W - draw.textbbox((0,0), rt, font=font_lg)[2]) // 2, 190),
                  rt, fill=(243, 139, 168), font=font_lg)

    # Info bar
    draw.rectangle([0, H - 35, W, H], fill=(30, 30, 46))
    info = f"🎣 {user_name[:16]}  |  💰 {balance}$"
    draw.text((10, H - 28), info, fill=(205, 214, 244), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def fish_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    # Cooldown
    data = load_data()
    last_fish = data.get("last_fish", {}).get(str(chat.id), {}).get(str(user.id), 0)
    now = time.time()
    if now - last_fish < FISH_COOLDOWN:
        remaining = int(FISH_COOLDOWN - (now - last_fish))
        mins = remaining // 60
        if lang == "fa":
            await update.message.reply_text(f"🎣 باید *{mins}* دقیقه صبر کنی تا دوباره ماهیگیری کنی!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"🎣 Wait *{mins}* minutes before fishing again!", parse_mode="Markdown")
        return

    # Set cooldown
    data.setdefault("last_fish", {}).setdefault(str(chat.id), {})[str(user.id)] = now
    save_data(data)

    # Catch a fish based on weighted random
    catches = FISH_CATCHES.get(lang, FISH_CATCHES["en"])
    names = [c[0] for c in catches]
    rewards = [c[1] for c in catches]
    weights = [c[2] for c in catches]

    idx = random.choices(range(len(catches)), weights=weights, k=1)[0]
    catch_name = names[idx]
    reward = rewards[idx]

    new_bal = add_balance(chat.id, user.id, reward) if reward != 0 else get_balance(chat.id, user.id)
    u_name = user.first_name or "User"

    buf = _render_fish_scene(catch_name, reward, u_name, new_bal, lang)
    if lang == "fa":
        caption = f"🎣 *{u_name}* ماهیگیری کرد!\n\nگرفت: {catch_name}"
        if reward > 0:
            caption += f"\n💰 +{reward}$ — موجودی: *{new_bal}$*"
        elif reward < 0:
            caption += f"\n💸 {reward}$ — موجودی: *{new_bal}$*"
        else:
            caption += f"\n😅 چیز بدرد بخوری نبود!"
    else:
        caption = f"🎣 *{u_name}* went fishing!\n\nCaught: {catch_name}"
        if reward > 0:
            caption += f"\n💰 +{reward}$ — Balance: *{new_bal}$*"
        elif reward < 0:
            caption += f"\n💸 {reward}$ — Balance: *{new_bal}$*"
        else:
            caption += f"\n😅 Nothing useful!"
    await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# /mine — Mining mini-game (cooldown: 45 min)
# ═══════════════════════════════════════════════════
MINE_COOLDOWN = 2700  # 45 minutes

MINE_FINDS = {
    "fa": [
        ("🪨 سنگ معمولی", 10, 30),
        ("🥉 برنز", 30, 22),
        ("🥈 نقره", 60, 15),
        ("🥇 طلا", 120, 8),
        ("💎 الماس!", 300, 4),
        ("🔥 یاقوت!", 200, 6),
        ("🪨 ریزش معدن!", -50, 8),
        ("💀 گاز سمی!", -80, 3),
        ("🏺 گنجینه باستانی!", 600, 2),
        ("⚒️ معدن خالی", 5, 15),
        ("🌋 سنگ آتشفشانی", 50, 12),
    ],
    "en": [
        ("🪨 Common Rock", 10, 30),
        ("🥉 Bronze Ore", 30, 22),
        ("🥈 Silver Ore", 60, 15),
        ("🥇 Gold Nugget", 120, 8),
        ("💎 Diamond!", 300, 4),
        ("🔥 Ruby!", 200, 6),
        ("🪨 Cave-in!", -50, 8),
        ("💀 Toxic Gas!", -80, 3),
        ("🏺 Ancient Treasure!", 600, 2),
        ("⚒️ Empty Mine", 5, 15),
        ("🌋 Volcanic Rock", 50, 12),
    ],
}


def _render_mine_scene(find_name: str, reward: int, user_name: str, balance: int, lang: str) -> io.BytesIO:
    W, H = 400, 280
    img = Image.new("RGB", (W, H), (30, 20, 15))
    draw = ImageDraw.Draw(img)
    font = _get_font_econ(14)
    font_lg = _get_font_econ(20)
    font_sm = _get_font_econ(11)

    # Cave walls
    for y in range(H - 35):
        r = int(30 + (y % 40) * 0.5)
        g = int(20 + (y % 30) * 0.3)
        b = int(15 + (y % 20) * 0.2)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Rock texture
    rng = random.Random(99)
    for _ in range(200):
        rx, ry = rng.randint(0, W), rng.randint(0, H-40)
        shade = rng.randint(25, 55)
        draw.point((rx, ry), fill=(shade, shade - 5, shade - 10))

    # Cave pillars
    for px in [40, W - 40]:
        for py in range(0, H - 40, 4):
            draw.rectangle([px - 8, py, px + 8, py + 3], fill=(50, 35, 25))

    # Torch on left
    draw.rectangle([80, 60, 86, 100], fill=(100, 70, 30))
    for i in range(10):
        draw.ellipse([76 - i, 50 - i, 90 + i, 64], fill=(255 - i*10, 150 - i*5, 50))
    draw.ellipse([80, 48, 86, 56], fill=(255, 220, 100))

    # Crystal sparkles
    for _ in range(8):
        cx, cy = rng.randint(100, W-100), rng.randint(30, 150)
        c = rng.choice([(100, 200, 255), (200, 100, 255), (255, 255, 100), (100, 255, 200)])
        draw.rectangle([cx, cy, cx + 3, cy + 3], fill=c)

    # Find display
    ftb = draw.textbbox((0, 0), find_name, font=font_lg)
    draw.text(((W - ftb[2] + ftb[0]) // 2, 170), find_name, fill=(249, 226, 175), font=font_lg)

    if reward > 0:
        rt = f"+{reward}$"
        draw.text(((W - draw.textbbox((0,0), rt, font=font_lg)[2]) // 2, 200),
                  rt, fill=(166, 227, 161), font=font_lg)
    elif reward < 0:
        rt = f"{reward}$"
        draw.text(((W - draw.textbbox((0,0), rt, font=font_lg)[2]) // 2, 200),
                  rt, fill=(243, 139, 168), font=font_lg)

    # Info bar
    draw.rectangle([0, H - 35, W, H], fill=(30, 30, 46))
    info = f"⛏️ {user_name[:16]}  |  💰 {balance}$"
    draw.text((10, H - 28), info, fill=(205, 214, 244), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def mine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    # Cooldown
    data = load_data()
    last_mine = data.get("last_mine", {}).get(str(chat.id), {}).get(str(user.id), 0)
    now = time.time()
    if now - last_mine < MINE_COOLDOWN:
        remaining = int(MINE_COOLDOWN - (now - last_mine))
        mins = remaining // 60
        if lang == "fa":
            await update.message.reply_text(f"⛏️ باید *{mins}* دقیقه صبر کنی تا دوباره معدن بزنی!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⛏️ Wait *{mins}* minutes before mining again!", parse_mode="Markdown")
        return

    data.setdefault("last_mine", {}).setdefault(str(chat.id), {})[str(user.id)] = now
    save_data(data)

    finds = MINE_FINDS.get(lang, MINE_FINDS["en"])
    names = [f[0] for f in finds]
    rewards = [f[1] for f in finds]
    weights = [f[2] for f in finds]

    idx = random.choices(range(len(finds)), weights=weights, k=1)[0]
    find_name = names[idx]
    reward = rewards[idx]

    new_bal = add_balance(chat.id, user.id, reward) if reward != 0 else get_balance(chat.id, user.id)
    u_name = user.first_name or "User"

    buf = _render_mine_scene(find_name, reward, u_name, new_bal, lang)
    if lang == "fa":
        caption = f"⛏️ *{u_name}* رفت معدن!\n\nپیدا کرد: {find_name}"
        if reward > 0:
            caption += f"\n💰 +{reward}$ — موجودی: *{new_bal}$*"
        elif reward < 0:
            caption += f"\n💸 {reward}$ — موجودی: *{new_bal}$*"
        else:
            caption += f"\n😐 چیز خاصی نبود."
    else:
        caption = f"⛏️ *{u_name}* went mining!\n\nFound: {find_name}"
        if reward > 0:
            caption += f"\n💰 +{reward}$ — Balance: *{new_bal}$*"
        elif reward < 0:
            caption += f"\n💸 {reward}$ — Balance: *{new_bal}$*"
        else:
            caption += f"\n😐 Nothing special."
    await update.message.reply_photo(photo=buf, caption=caption, parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# /quest — Daily quest for bonus rewards
# ═══════════════════════════════════════════════════
QUESTS = {
    "fa": [
        {"name": "🗡️ شکست اژدها", "desc": "اژدها رو شکست دادی!", "reward": 300, "chance": 50},
        {"name": "🏰 نجات شاهزاده", "desc": "شاهزاده رو نجات دادی!", "reward": 250, "chance": 45},
        {"name": "🗺️ کشف گنج", "desc": "گنجینه پیدا کردی!", "reward": 400, "chance": 35},
        {"name": "🧙 شکست جادوگر تاریک", "desc": "جادوگر تاریک رو نابود کردی!", "reward": 350, "chance": 40},
        {"name": "🐉 شکار هیولا", "desc": "هیولا رو شکار کردی!", "reward": 200, "chance": 55},
        {"name": "🏴‍☠️ جنگ با دزدان دریایی", "desc": "دزدان دریایی رو شکست دادی!", "reward": 280, "chance": 45},
        {"name": "🌋 عبور از آتشفشان", "desc": "از آتشفشان رد شدی!", "reward": 320, "chance": 40},
        {"name": "👻 پاکسازی خانه متروکه", "desc": "ارواح رو دور کردی!", "reward": 180, "chance": 60},
    ],
    "en": [
        {"name": "🗡️ Slay the Dragon", "desc": "You defeated the dragon!", "reward": 300, "chance": 50},
        {"name": "🏰 Rescue the Princess", "desc": "You rescued the princess!", "reward": 250, "chance": 45},
        {"name": "🗺️ Find the Treasure", "desc": "You found the treasure!", "reward": 400, "chance": 35},
        {"name": "🧙 Defeat the Dark Wizard", "desc": "You destroyed the dark wizard!", "reward": 350, "chance": 40},
        {"name": "🐉 Monster Hunt", "desc": "You hunted the monster!", "reward": 200, "chance": 55},
        {"name": "🏴‍☠️ Pirate Battle", "desc": "You defeated the pirates!", "reward": 280, "chance": 45},
        {"name": "🌋 Volcano Crossing", "desc": "You crossed the volcano!", "reward": 320, "chance": 40},
        {"name": "👻 Haunted House", "desc": "You banished the ghosts!", "reward": 180, "chance": 60},
    ],
}


async def quest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user
    _remember_user(chat.id, user)

    # One quest per day
    data = load_data()
    today = date.today().isoformat()
    last_quest = data.get("last_quest", {}).get(str(chat.id), {}).get(str(user.id), "")
    if last_quest == today:
        if lang == "fa":
            await update.message.reply_text("⚔️ تو امروز یه کوئست انجام دادی! فردا دوباره بیا.", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚔️ You've already done a quest today! Come back tomorrow.", parse_mode="Markdown")
        return

    data.setdefault("last_quest", {}).setdefault(str(chat.id), {})[str(user.id)] = today
    save_data(data)

    quests = QUESTS.get(lang, QUESTS["en"])
    quest = random.choice(quests)
    u_name = user.first_name or "User"

    success = random.randint(1, 100) <= quest["chance"]
    if success:
        reward = quest["reward"]
        new_bal = add_balance(chat.id, user.id, reward)
        if lang == "fa":
            text = (
                f"⚔️ *کوئست: {quest['name']}*\n\n"
                f"✅ {quest['desc']}\n\n"
                f"💰 جایزه: *+{reward}$*\n"
                f"💳 موجودی: *{new_bal}$*"
            )
        else:
            text = (
                f"⚔️ *Quest: {quest['name']}*\n\n"
                f"✅ {quest['desc']}\n\n"
                f"💰 Reward: *+{reward}$*\n"
                f"💳 Balance: *{new_bal}$*"
            )
    else:
        # Fail — small consolation
        consolation = 20
        new_bal = add_balance(chat.id, user.id, consolation)
        if lang == "fa":
            text = (
                f"⚔️ *کوئست: {quest['name']}*\n\n"
                f"❌ شکست خوردی! ولی *{consolation}$* تلاش‌بها گرفتی.\n"
                f"💳 موجودی: *{new_bal}$*"
            )
        else:
            text = (
                f"⚔️ *Quest: {quest['name']}*\n\n"
                f"❌ Quest failed! But you got *{consolation}$* for trying.\n"
                f"💳 Balance: *{new_bal}$*"
            )
    await update.message.reply_text(text, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# /bail (وثیقه) — Admin pays to free someone from jail
# ════════════════════════════════════════════════════════════
BAIL_COST_PER_MINUTE = 10  # 10$ per remaining minute

async def bail_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    # Must reply to a jailed user
    reply = update.message.reply_to_message
    if not reply or not reply.from_user:
        msg = ("❌ روی پیام یک زندانی ریپلای کن و /bail بزن!" if lang == "fa"
               else "❌ Reply to a jailed user's message and use /bail!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    target = reply.from_user
    _remember_user(chat.id, target)

    if target.id == user.id:
        msg = ("❌ نمی‌تونی خودتو آزاد کنی!" if lang == "fa"
               else "❌ You can't bail yourself out!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    remaining = _check_jail(chat.id, target.id)
    if remaining is None:
        msg = (f"✅ *{target.first_name}* زندانی نیست!" if lang == "fa"
               else f"✅ *{target.first_name}* is not in jail!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    cost = max(50, (remaining // 60 + 1) * BAIL_COST_PER_MINUTE)
    bal = get_balance(chat.id, user.id)

    if cost > bal:
        msg = (f"❌ هزینه وثیقه *{cost}$* — موجودی تو: *{bal}$*" if lang == "fa"
               else f"❌ Bail costs *{cost}$* — Your balance: *{bal}$*")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -cost)
    clear_jail(chat.id, target.id)

    u_name = (user.first_name or "User")
    t_name = (target.first_name or "User")

    if lang == "fa":
        msg = (f"⚖️ *وثیقه پرداخت شد!*\n\n"
               f"👤 *{u_name}* مبلغ *{cost}$* وثیقه پرداخت کرد.\n"
               f"🔓 *{t_name}* از زندان آزاد شد!\n"
               f"💰 موجودی {u_name}: *{get_balance(chat.id, user.id)}$*")
    else:
        msg = (f"⚖️ *Bail Paid!*\n\n"
               f"👤 *{u_name}* paid *{cost}$* bail.\n"
               f"🔓 *{t_name}* has been freed from jail!\n"
               f"💰 {u_name}'s balance: *{get_balance(chat.id, user.id)}$*")

    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# /jailbreak — Collaborative jail escape (3+ people)
# ════════════════════════════════════════════════════════════
JAILBREAK_COOLDOWN = 600  # 10 min cooldown per attempt
JAILBREAK_FAIL_PENALTY = 180  # +3 min added on failure

async def jailbreak_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    # Must reply to jailed user
    reply = update.message.reply_to_message
    if not reply or not reply.from_user:
        msg = ("❌ روی پیام یک زندانی ریپلای کن!\nبرای فرار حداقل ۳ نفر باید /jailbreak بزنن." if lang == "fa"
               else "❌ Reply to a jailed user's message!\nAt least 3 people need to use /jailbreak to escape.")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    target = reply.from_user
    _remember_user(chat.id, target)

    remaining = _check_jail(chat.id, target.id)
    if remaining is None:
        msg = (f"✅ *{target.first_name}* زندانی نیست!" if lang == "fa"
               else f"✅ *{target.first_name}* is not in jail!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Can't break yourself out
    if target.id == user.id:
        msg = ("❌ نمی‌تونی خودتو نجات بدی! بقیه باید کمکت کنن!" if lang == "fa"
               else "❌ You can't break yourself out! Others must help!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Track jailbreak attempts in data
    data = load_data()
    cid = str(chat.id)
    tid = str(target.id)
    uid = str(user.id)

    attempts = data.setdefault("jailbreak_attempts", {}).setdefault(cid, {})
    attempt = attempts.get(tid, {"helpers": [], "last_attempt": ""})

    # Check cooldown
    now = datetime.utcnow()
    if attempt.get("last_attempt"):
        try:
            last_dt = datetime.fromisoformat(attempt["last_attempt"])
            if (now - last_dt).total_seconds() < JAILBREAK_COOLDOWN:
                cd_left = int(JAILBREAK_COOLDOWN - (now - last_dt).total_seconds())
                mins = cd_left // 60
                secs = cd_left % 60
                msg = (f"⏳ باید *{mins} دقیقه و {secs} ثانیه* صبر کنید تا دوباره تلاش کنید!" if lang == "fa"
                       else f"⏳ Wait *{mins}m {secs}s* before trying again!")
                await update.message.reply_text(msg, parse_mode="Markdown")
                return
        except ValueError:
            pass

    # Add helper if not already in list
    if user.id not in attempt.get("helpers", []):
        attempt.setdefault("helpers", []).append(user.id)

    helpers = attempt["helpers"]
    helper_count = len(helpers)
    attempts[tid] = attempt
    data["jailbreak_attempts"][cid] = attempts
    save_data(data)

    t_name = target.first_name or "User"
    u_name = user.first_name or "User"

    if helper_count < 3:
        needed = 3 - helper_count
        if lang == "fa":
            msg = (f"🔓 *{u_name}* میخواد به *{t_name}* کمک کنه فرار کنه!\n\n"
                   f"👥 کمک‌کننده‌ها: *{helper_count}/3*\n"
                   f"⏳ هنوز *{needed}* نفر دیگه لازمه!\n"
                   f"بقیه هم روی همین پیام /jailbreak بزنن!")
        else:
            msg = (f"🔓 *{u_name}* wants to help *{t_name}* escape!\n\n"
                   f"👥 Helpers: *{helper_count}/3*\n"
                   f"⏳ Need *{needed}* more people!\n"
                   f"Others reply to the same message with /jailbreak!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Enough helpers — attempt the break!
    # Success chance: 30% base + 10% per extra helper (max 80%)
    success_chance = min(0.80, 0.30 + (helper_count - 3) * 0.10)

    # Reset attempt data
    attempt["helpers"] = []
    attempt["last_attempt"] = now.isoformat()
    attempts[tid] = attempt
    data["jailbreak_attempts"][cid] = attempts
    save_data(data)

    if random.random() < success_chance:
        # Success!
        clear_jail(chat.id, target.id)
        if lang == "fa":
            msg = (f"🔓💥 *فرار از زندان موفقیت‌آمیز بود!*\n\n"
                   f"👥 {helper_count} نفر کمک کردن و *{t_name}* از زندان فرار کرد!\n"
                   f"🏃 *{t_name}* آزاده! 🎉\n"
                   f"📊 شانس موفقیت: *{int(success_chance*100)}%*")
        else:
            msg = (f"🔓💥 *Jailbreak SUCCESSFUL!*\n\n"
                   f"👥 {helper_count} people helped and *{t_name}* escaped!\n"
                   f"🏃 *{t_name}* is FREE! 🎉\n"
                   f"📊 Success chance was: *{int(success_chance*100)}%*")
    else:
        # Failure — add penalty time to prisoner
        jt = get_jail_time(chat.id, target.id)
        if jt and "|" in jt:
            ts, dur_str = jt.rsplit("|", 1)
            try:
                old_dur = int(dur_str)
                new_dur = old_dur + JAILBREAK_FAIL_PENALTY
                set_jail_time(chat.id, target.id, f"{ts}|{new_dur}")
            except ValueError:
                pass
        else:
            # Standard jail — add penalty
            if jt:
                new_dur = JAIL_DURATION + JAILBREAK_FAIL_PENALTY
                set_jail_time(chat.id, target.id, f"{jt}|{new_dur}")

        if lang == "fa":
            msg = (f"🚨 *فرار ناموفق!*\n\n"
                   f"👮 نگهبان‌ها همه رو گرفتن!\n"
                   f"⏳ *{JAILBREAK_FAIL_PENALTY // 60} دقیقه* به مدت زندان *{t_name}* اضافه شد!\n"
                   f"📊 شانس موفقیت: *{int(success_chance*100)}%* بود")
        else:
            msg = (f"🚨 *Jailbreak FAILED!*\n\n"
                   f"👮 Guards caught everyone!\n"
                   f"⏳ *{JAILBREAK_FAIL_PENALTY // 60} minutes* added to *{t_name}*'s sentence!\n"
                   f"📊 Success chance was: *{int(success_chance*100)}%*")

    await update.message.reply_text(msg, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# /donate — Donate money to charity
# ════════════════════════════════════════════════════════════
async def donate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []
    if not args or not args[0].isdigit():
        if lang == "fa":
            await update.message.reply_text(
                "💝 *خیریه*\n\nاستفاده: `/donate [مبلغ]`\n"
                "پولت رو به خیریه اهدا کن و توی تابلو خیریه بدرخش! ✨\n\n"
                "📊 `/charity` — تابلوی خیرین",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "💝 *Charity*\n\nUsage: `/donate [amount]`\n"
                "Donate your Kollars to charity and shine on the leaderboard! ✨\n\n"
                "📊 `/charity` — Donor leaderboard",
                parse_mode="Markdown")
        return

    amount = int(args[0])
    if amount <= 0:
        return

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        msg = (f"❌ موجودی کافی نیست! ({bal}$)" if lang == "fa"
               else f"❌ Not enough balance! ({bal}$)")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -amount)
    add_donation(chat.id, user.id, amount)
    new_bal = get_balance(chat.id, user.id)

    u_name = user.first_name or "User"
    if lang == "fa":
        text = (
            f"💝 *{u_name}* مبلغ *{amount}$* به خیریه اهدا کرد! 🌟\n\n"
            f"ممنون از سخاوتت! 🙏\n"
            f"💰 موجودی: *{new_bal}$*\n\n"
            f"📊 `/charity` — تابلوی خیرین"
        )
    else:
        text = (
            f"💝 *{u_name}* donated *{amount}$* to charity! 🌟\n\n"
            f"Thank you for your generosity! 🙏\n"
            f"💰 Balance: *{new_bal}$*\n\n"
            f"📊 `/charity` — Donor leaderboard"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# /charity — Charity donation leaderboard
# ════════════════════════════════════════════════════════════
async def charity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    donations = get_donations(chat.id)
    if not donations:
        if lang == "fa":
            await update.message.reply_text("💝 هنوز کسی کمکی نکرده! `/donate [مبلغ]` بزن.", parse_mode="Markdown")
        else:
            await update.message.reply_text("💝 No donations yet! Use `/donate [amount]`.", parse_mode="Markdown")
        return

    sorted_donors = sorted(donations.items(), key=lambda x: x[1], reverse=True)[:15]
    medals = ["🥇", "🥈", "🥉"]
    titles_fa = ["👑 پادشاه خیرین", "💎 خیر برتر", "⭐ خیر سخاوتمند"]
    titles_en = ["👑 King of Charity", "💎 Top Donor", "⭐ Generous Donor"]
    lines = []
    total = 0
    for i, (uid_str, donated) in enumerate(sorted_donors):
        name = get_user_name(chat.id, int(uid_str))
        if not name:
            try:
                member = await context.bot.get_chat_member(chat.id, int(uid_str))
                name = (member.user.full_name or member.user.first_name or f"User {uid_str}").strip()
                set_user_name(chat.id, int(uid_str), name)
            except Exception:
                name = f"User {uid_str}"
        medal = medals[i] if i < 3 else f"*{i+1}.*"
        title = (titles_fa[i] if lang == "fa" else titles_en[i]) if i < 3 else ""
        line = f"{medal} {name} — *{donated}$*"
        if title:
            line += f" {title}"
        lines.append(line)
        total += donated

    if lang == "fa":
        header = "💝 *تابلوی خیرین* 💝\n\n"
        footer = f"\n\n💰 مجموع کمک‌ها: *{total}$*\n💝 `/donate [مبلغ]` — اهدا کن!"
    else:
        header = "💝 *Charity Leaderboard* 💝\n\n"
        footer = f"\n\n💰 Total donated: *{total}$*\n💝 `/donate [amount]` — Make a donation!"

    await update.message.reply_text(header + "\n".join(lines) + footer, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════
# Real Estate Investment System
# ════════════════════════════════════════════════════════════
REAL_ESTATE = {
    "shack": {
        "name_en": "🏚️ Old Shack", "name_fa": "🏚️ کلبه قدیمی",
        "base_price": 500, "daily_rent": 15, "tier": 1,
    },
    "apartment": {
        "name_en": "🏢 Apartment", "name_fa": "🏢 آپارتمان",
        "base_price": 2000, "daily_rent": 60, "tier": 2,
    },
    "house": {
        "name_en": "🏠 House", "name_fa": "🏠 خانه",
        "base_price": 5000, "daily_rent": 150, "tier": 3,
    },
    "villa": {
        "name_en": "🏡 Villa", "name_fa": "🏡 ویلا",
        "base_price": 15000, "daily_rent": 450, "tier": 4,
    },
    "penthouse": {
        "name_en": "🏙️ Penthouse", "name_fa": "🏙️ پنت‌هاوس",
        "base_price": 40000, "daily_rent": 1200, "tier": 5,
    },
    "mansion": {
        "name_en": "🏰 Mansion", "name_fa": "🏰 عمارت",
        "base_price": 100000, "daily_rent": 3000, "tier": 6,
    },
}


def _property_price(prop_id: str, chat_id: int) -> int:
    """Dynamic property price based on total purchases."""
    base = REAL_ESTATE[prop_id]["base_price"]
    data = load_data()
    owned_count = 0
    all_props = data.get("properties", {}).get(str(chat_id), {})
    for uid, props in all_props.items():
        for p in props:
            if p.get("type") == prop_id:
                owned_count += 1
    return int(base * (1 + owned_count * 0.05))


async def realestate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available properties or user's portfolio."""
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []

    # /realestate collect
    if args and args[0].lower() in ("collect", "rent", "جمع"):
        props = get_properties(chat.id, user.id)
        if not props:
            msg = ("❌ تو ملکی نداری!" if lang == "fa" else "❌ You don't own any properties!")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        today = date.today().isoformat()
        total_rent = 0
        data = load_data()
        cid = str(chat.id)
        uid = str(user.id)
        user_props = data.get("properties", {}).get(cid, {}).get(uid, [])

        for p in user_props:
            last_rent = p.get("last_rent", "")
            if last_rent == today:
                continue
            prop_info = REAL_ESTATE.get(p.get("type", ""))
            if not prop_info:
                continue
            rent = prop_info["daily_rent"]
            total_rent += rent
            p["last_rent"] = today

        if total_rent == 0:
            msg = ("✅ اجاره امروز رو قبلاً جمع کردی!" if lang == "fa"
                   else "✅ You already collected today's rent!")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        save_data(data)
        new_bal = add_balance(chat.id, user.id, total_rent)
        if lang == "fa":
            text = (f"🏠 *اجاره جمع شد!*\n\n"
                    f"💰 درآمد اجاره: *+{total_rent}$*\n"
                    f"💳 موجودی: *{new_bal}$*")
        else:
            text = (f"🏠 *Rent Collected!*\n\n"
                    f"💰 Rental income: *+{total_rent}$*\n"
                    f"💳 Balance: *{new_bal}$*")
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    # /realestate my
    if args and args[0].lower() in ("my", "من", "list"):
        props = get_properties(chat.id, user.id)
        if not props:
            msg = ("❌ تو ملکی نداری! `/realestate` بزن برای خرید." if lang == "fa"
                   else "❌ You don't own any properties! Use `/realestate` to buy.")
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        lines = []
        total_rent = 0
        total_value = 0
        for p in props:
            info = REAL_ESTATE.get(p.get("type", ""))
            if not info:
                continue
            name = info["name_fa"] if lang == "fa" else info["name_en"]
            rent = info["daily_rent"]
            price = _property_price(p["type"], chat.id)
            sell_price = int(price * 0.8)
            total_rent += rent
            total_value += sell_price
            lines.append(f"  {name} — {rent}$/day  (sell: {sell_price}$)")

        if lang == "fa":
            header = "🏠 *ملک‌های تو*\n\n"
            footer = (f"\n\n💰 درآمد روزانه: *{total_rent}$*\n"
                      f"💎 ارزش کل: *~{total_value}$*\n"
                      f"📥 `/realestate collect` — جمع اجاره\n"
                      f"📤 `/sellproperty [نوع]` — فروش")
        else:
            header = "🏠 *Your Properties*\n\n"
            footer = (f"\n\n💰 Daily income: *{total_rent}$*\n"
                      f"💎 Total value: *~{total_value}$*\n"
                      f"📥 `/realestate collect` — Collect rent\n"
                      f"📤 `/sellproperty [type]` — Sell property")
        await update.message.reply_text(header + "\n".join(lines) + footer, parse_mode="Markdown")
        return

    # Default: show market
    lines = []
    for pid, info in REAL_ESTATE.items():
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        price = _property_price(pid, chat.id)
        rent = info["daily_rent"]
        roi_days = price // rent if rent else 999
        lines.append(f"{name}\n   💰 {price}$ | 📥 {rent}$/day | 📊 ROI: {roi_days} days\n   `/buyproperty {pid}`")

    if lang == "fa":
        header = "🏠 *بازار املاک*\n\n"
        footer = ("\n\n🏠 `/realestate my` — ملک‌های تو\n"
                  "📥 `/realestate collect` — جمع اجاره")
    else:
        header = "🏠 *Real Estate Market*\n\n"
        footer = ("\n\n🏠 `/realestate my` — Your properties\n"
                  "📥 `/realestate collect` — Collect rent")
    await update.message.reply_text(header + "\n".join(lines) + footer, parse_mode="Markdown")


async def buyproperty_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buy a property."""
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []
    if not args:
        available = ", ".join(REAL_ESTATE.keys())
        msg = (f"❌ استفاده: `/buyproperty [نوع]`\nموجود: {available}" if lang == "fa"
               else f"❌ Usage: `/buyproperty [type]`\nAvailable: {available}")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    prop_id = args[0].lower()
    if prop_id not in REAL_ESTATE:
        available = ", ".join(REAL_ESTATE.keys())
        msg = (f"❌ ملک نامعتبر! موجود: {available}" if lang == "fa"
               else f"❌ Invalid property! Available: {available}")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    info = REAL_ESTATE[prop_id]
    price = _property_price(prop_id, chat.id)
    bal = get_balance(chat.id, user.id)

    if price > bal:
        msg = (f"❌ موجودی کافی نیست! نیاز: *{price}$* | موجودی: *{bal}$*" if lang == "fa"
               else f"❌ Not enough money! Need: *{price}$* | Balance: *{bal}$*")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    existing = get_properties(chat.id, user.id)
    if len(existing) >= 10:
        msg = ("❌ حداکثر ۱۰ ملک می‌تونی داشته باشی!" if lang == "fa"
               else "❌ Maximum 10 properties allowed!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -price)
    prop = {
        "id": f"{prop_id}_{int(time.time())}",
        "type": prop_id,
        "bought_at": date.today().isoformat(),
        "bought_price": price,
        "last_rent": "",
    }
    add_property(chat.id, user.id, prop)

    name = info["name_fa"] if lang == "fa" else info["name_en"]
    new_bal = get_balance(chat.id, user.id)
    if lang == "fa":
        text = (f"🏠 *ملک خریداری شد!*\n\n"
                f"🏷️ {name}\n"
                f"💰 قیمت: *{price}$*\n"
                f"📥 اجاره روزانه: *{info['daily_rent']}$*\n"
                f"💳 موجودی: *{new_bal}$*\n\n"
                f"📥 `/realestate collect` — جمع اجاره")
    else:
        text = (f"🏠 *Property Purchased!*\n\n"
                f"🏷️ {name}\n"
                f"💰 Price: *{price}$*\n"
                f"📥 Daily rent: *{info['daily_rent']}$*\n"
                f"💳 Balance: *{new_bal}$*\n\n"
                f"📥 `/realestate collect` — Collect rent")
    await update.message.reply_text(text, parse_mode="Markdown")


async def sellproperty_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sell a property (80% of current market price)."""
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    args = context.args or []
    if not args:
        msg = ("❌ استفاده: `/sellproperty [نوع]`" if lang == "fa"
               else "❌ Usage: `/sellproperty [type]`")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    prop_type = args[0].lower()
    props = get_properties(chat.id, user.id)

    target = None
    for p in props:
        if p.get("type") == prop_type:
            target = p
            break

    if not target:
        msg = (f"❌ تو ملکی از نوع *{prop_type}* نداری!" if lang == "fa"
               else f"❌ You don't own a *{prop_type}* property!")
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    price = _property_price(prop_type, chat.id)
    sell_price = int(price * 0.8)
    remove_property(chat.id, user.id, target["id"])
    new_bal = add_balance(chat.id, user.id, sell_price)

    info = REAL_ESTATE.get(prop_type, {})
    name = info.get("name_fa", prop_type) if lang == "fa" else info.get("name_en", prop_type)

    if lang == "fa":
        text = (f"🏠 *ملک فروخته شد!*\n\n"
                f"🏷️ {name}\n"
                f"💰 قیمت فروش: *{sell_price}$* (80%)\n"
                f"💳 موجودی: *{new_bal}$*")
    else:
        text = (f"🏠 *Property Sold!*\n\n"
                f"🏷️ {name}\n"
                f"💰 Sale price: *{sell_price}$* (80%)\n"
                f"💳 Balance: *{new_bal}$*")
    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /economy (economic stats & tax info) ---------
async def economy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)
    _remember_user(chat.id, user)

    bal = get_balance(chat.id, user.id)
    xp = get_work_xp(chat.id, user.id)
    level = xp // WORK_XP_PER_LEVEL
    streak = get_daily_streak(chat.id, user.id).get("count", 0)

    # Wealth tax bracket
    tax_rate = 0
    for threshold, rate in reversed(WEALTH_TAX_BRACKETS):
        if bal >= threshold:
            tax_rate = rate
            break
    tax_amount = int(bal * tax_rate) if tax_rate else 0

    # Total money supply in chat
    all_bals = get_all_balances(chat.id)
    total_supply = sum(all_bals.values()) if all_bals else 0

    # Properties
    props = get_properties(chat.id, user.id)
    daily_rent = sum(REAL_ESTATE.get(p.get("type", ""), {}).get("daily_rent", 0) for p in props)
    prop_value = sum(
        _property_price(p.get("type", ""), chat.id) for p in props
    )

    if lang == "fa":
        msg = (
            f"📊 *وضعیت اقتصادی {user.first_name}*\n\n"
            f"💰 موجودی: *{bal}$*\n"
            f"🏠 ارزش املاک: *{prop_value}$*\n"
            f"📥 اجاره روزانه: *{daily_rent}$*\n"
            f"💎 ثروت کل: *{bal + prop_value}$*\n\n"
            f"⭐ سطح کار: *{level}* ({xp} XP)\n"
            f"💼 بونوس درآمد: *+{int(level * WORK_BONUS_PER_LEVEL * 100)}%*\n"
            f"🔥 استریک روزانه: *{streak}/{MAX_STREAK}*\n\n"
            f"🏛️ *براکت مالیات:*\n"
        )
        if tax_rate > 0:
            msg += f"   📌 نرخ: *{int(tax_rate*100)}%* = *{tax_amount}$*/روز\n"
        else:
            msg += f"   ✅ معاف (زیر {WEALTH_TAX_BRACKETS[0][0]}$)\n"
        msg += (
            f"💸 مالیات انتقال: *{int(TRANSFER_TAX_RATE*100)}%* (بالای {TRANSFER_TAX_THRESHOLD}$)\n\n"
            f"🏦 عرضه پول گروه: *{total_supply}$*"
        )
    else:
        msg = (
            f"📊 *{user.first_name}'s Economy Status*\n\n"
            f"💰 Balance: *{bal}$*\n"
            f"🏠 Property value: *{prop_value}$*\n"
            f"📥 Daily rent income: *{daily_rent}$*\n"
            f"💎 Net worth: *{bal + prop_value}$*\n\n"
            f"⭐ Work level: *{level}* ({xp} XP)\n"
            f"💼 Pay bonus: *+{int(level * WORK_BONUS_PER_LEVEL * 100)}%*\n"
            f"🔥 Daily streak: *{streak}/{MAX_STREAK}*\n\n"
            f"🏛️ *Tax Bracket:*\n"
        )
        if tax_rate > 0:
            msg += f"   📌 Rate: *{int(tax_rate*100)}%* = *{tax_amount}$*/day\n"
        else:
            msg += f"   ✅ Exempt (below {WEALTH_TAX_BRACKETS[0][0]}$)\n"
        msg += (
            f"💸 Transfer tax: *{int(TRANSFER_TAX_RATE*100)}%* (above {TRANSFER_TAX_THRESHOLD}$)\n\n"
            f"🏦 Group money supply: *{total_supply}$*"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")


# --------- /bounty (place a bounty on someone) ---------
async def bounty_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    user = update.effective_user
    _remember_user(chat.id, user)

    if not update.message.reply_to_message or not context.args or not context.args[0].isdigit():
        if lang == "fa":
            await update.message.reply_text(
                "📝 به پیام کسی ریپلای کن و بنویس: /bounty <مبلغ>\n"
                "🎯 وقتی کسی اون فرد رو /rob کنه، بانتی رو هم میگیره!",
                parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "📝 Reply to someone: /bounty <amount>\n"
                "🎯 When someone robs that person, they collect the bounty!",
                parse_mode="Markdown")
        return

    target = update.message.reply_to_message.from_user
    _remember_user(chat.id, target)
    if target.id == user.id or target.is_bot:
        msg = "❌ نمیتونی روی خودت یا ربات بانتی بذاری!" if lang == "fa" else "❌ Can't bounty yourself or a bot!"
        await update.message.reply_text(msg)
        return

    amount = int(context.args[0])
    if amount < 50:
        msg = "❌ حداقل بانتی: 50$" if lang == "fa" else "❌ Minimum bounty: 50$"
        await update.message.reply_text(msg)
        return

    bal = get_balance(chat.id, user.id)
    if bal < amount:
        msg = f"❌ پول کافی نداری! موجودی: *{bal}$*" if lang == "fa" else f"❌ Not enough! Balance: *{bal}$*"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    add_balance(chat.id, user.id, -amount)
    # Stack bounties
    existing = get_bounties(chat.id)
    old_amount = existing.get(str(target.id), {}).get("amount", 0)
    set_bounty(chat.id, target.id, old_amount + amount, user.id)

    total = old_amount + amount
    if lang == "fa":
        await update.message.reply_text(
            f"🎯 *بانتی روی {target.first_name} گذاشته شد!*\n\n"
            f"💰 مبلغ: *{amount}$*\n"
            f"💎 کل بانتی: *{total}$*\n\n"
            f"_هرکسی که اون رو /rob کنه، بانتی رو هم میگیره!_",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"🎯 *Bounty placed on {target.first_name}!*\n\n"
            f"💰 Amount: *{amount}$*\n"
            f"💎 Total bounty: *{total}$*\n\n"
            f"_Anyone who /rob's them collects the bounty!_",
            parse_mode="Markdown")


# --------- /bounties (list active bounties) ---------
async def bounties_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    bounties = get_bounties(chat.id)
    if not bounties:
        msg = "🎯 هیچ بانتی فعالی نیست!" if lang == "fa" else "🎯 No active bounties!"
        await update.message.reply_text(msg)
        return

    sorted_b = sorted(bounties.items(), key=lambda x: x[1].get("amount", 0), reverse=True)
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, info) in enumerate(sorted_b[:10]):
        name = get_user_name(chat.id, int(uid)) or f"User {uid}"
        prefix = medals[i] if i < 3 else f"*{i + 1}.*"
        lines.append(f"{prefix} {name} — 💰 *{info['amount']:,}$*")

    header = "🎯 *بانتی‌های فعال*\n" + "═" * 24 + "\n\n" if lang == "fa" else "🎯 *Active Bounties*\n" + "═" * 24 + "\n\n"
    await update.message.reply_text(header + "\n".join(lines), parse_mode="Markdown")
