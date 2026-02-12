# ==========================================
# KNTU Bot 25 — Economy & Gambling
# ==========================================

import random
import io
import os
from datetime import date, datetime
from telegram import Update
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
)
from strings import STRINGS

DAILY_AMOUNT = 200
KOLLAR = "کلار $"

WORK_COOLDOWN = 3600  # 1 hour
SPIN_COOLDOWN = 8 * 3600  # 8 hours
JAIL_DURATION = 360  # 6 minutes in seconds

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
    "AAPL":  {"name": "Apple 🍎",          "base": 180},
    "TSLA":  {"name": "Tesla ⚡",          "base": 250},
    "GOOG":  {"name": "Google 🔍",         "base": 140},
    "AMZN":  {"name": "Amazon 📦",         "base": 190},
    "MSFT":  {"name": "Microsoft 💻",      "base": 320},
    "META":  {"name": "Meta 👤",           "base": 120},
    "NVDA":  {"name": "Nvidia 🎮",         "base": 400},
    "BTC":   {"name": "Bitcoin ₿",         "base": 500},
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

    new_bal = add_balance(chat.id, user.id, DAILY_AMOUNT)
    set_daily_claim(chat.id, user.id, today)
    await update.message.reply_text(
        s["daily_claimed"].format(amount=DAILY_AMOUNT, balance=new_bal),
        parse_mode="Markdown",
    )


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
        await update.message.reply_text(
            s["bet_lose"].format(amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )


# --------- /slots (slot machine) ---------
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]

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

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    s1 = random.choice(SLOT_SYMBOLS)
    s2 = random.choice(SLOT_SYMBOLS)
    s3 = random.choice(SLOT_SYMBOLS)
    display = f"[ {s1} | {s2} | {s3} ]"

    if s1 == s2 == s3:
        # Jackpot! 3x
        multiplier = 5 if s1 == "💎" else (3 if s1 == "7️⃣" else 2)
        winnings = amount * multiplier
        new_bal = add_balance(chat.id, user.id, winnings)
        await update.message.reply_text(
            s["slots_jackpot"].format(display=display, winnings=winnings, balance=new_bal),
            parse_mode="Markdown",
        )
    elif s1 == s2 or s2 == s3 or s1 == s3:
        # Two match: win back half
        winnings = amount // 2
        new_bal = add_balance(chat.id, user.id, winnings)
        await update.message.reply_text(
            s["slots_partial"].format(display=display, winnings=winnings, balance=new_bal),
            parse_mode="Markdown",
        )
    else:
        new_bal = add_balance(chat.id, user.id, -amount)
        await update.message.reply_text(
            s["slots_lose"].format(display=display, amount=amount, balance=new_bal),
            parse_mode="Markdown",
        )


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

    success = random.random() < 0.35  # 35% success
    if success:
        stolen = random.randint(10, min(200, target_bal // 3))
        add_balance(chat.id, user.id, stolen)
        add_balance(chat.id, target.id, -stolen)
        await update.message.reply_text(
            s["rob_success"].format(
                amount=stolen, user=target.first_name or "User",
                balance=get_balance(chat.id, user.id)
            ),
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

    bal = get_balance(chat.id, user.id)
    if amount > bal:
        await update.message.reply_text(
            s["bet_no_money"].format(balance=bal), parse_mode="Markdown"
        )
        return

    add_balance(chat.id, user.id, -amount)
    add_balance(chat.id, target.id, amount)
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

    job_name, min_pay, max_pay = random.choice(JOBS[lang])
    earned = random.randint(min_pay, max_pay)
    new_bal = add_balance(chat.id, user.id, earned)
    set_last_work(chat.id, user.id, now.isoformat())

    await update.message.reply_text(
        s["work_done"].format(job=job_name, earned=earned, balance=new_bal),
        parse_mode="Markdown",
    )


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
    """Render a 30-day price chart for a stock ticker."""
    today_ord = date.today().toordinal()
    prices = []
    for i in range(30):
        day_ord = today_ord - 29 + i
        base = COMPANIES[ticker]["base"]
        day_seed = day_ord + hash(ticker) % 9999
        rng = random.Random(day_seed)
        swing = rng.uniform(-0.30, 0.40)
        prices.append(max(10, int(base * (1 + swing))))

    W, H = 600, 320
    PAD_L, PAD_R, PAD_T, PAD_B = 60, 30, 60, 40
    BG = (30, 30, 46)
    GRID = (50, 50, 70)
    TEXT_CLR = (205, 214, 244)
    TITLE_CLR = (137, 180, 250)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = _get_font_econ(14)
    font_title = _get_font_econ(18)

    # Title
    title = f"{COMPANIES[ticker]['name']} ({ticker}) — 30 Day Chart"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((W - tb[2] + tb[0]) // 2, 12), title, fill=TITLE_CLR, font=font_title)

    min_p = min(prices) - 10
    max_p = max(prices) + 10
    chart_w = W - PAD_L - PAD_R
    chart_h = H - PAD_T - PAD_B

    # Grid lines
    for i in range(5):
        y = PAD_T + int(chart_h * i / 4)
        draw.line([(PAD_L, y), (W - PAD_R, y)], fill=GRID, width=1)
        val = max_p - (max_p - min_p) * i / 4
        draw.text((5, y - 7), f"${int(val)}", fill=TEXT_CLR, font=font)

    # Plot points
    points = []
    for i, p in enumerate(prices):
        x = PAD_L + int(chart_w * i / 29)
        y = PAD_T + int(chart_h * (max_p - p) / (max_p - min_p))
        points.append((x, y))

    # Gradient fill under line
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        bottom = PAD_T + chart_h
        draw.polygon([(x1, y1), (x2, y2), (x2, bottom), (x1, bottom)],
                      fill=(137, 180, 250, 30) if prices[-1] >= prices[0] else (243, 139, 168, 30))

    # Line color based on trend
    line_clr = (166, 227, 161) if prices[-1] >= prices[0] else (243, 139, 168)
    draw.line(points, fill=line_clr, width=2)

    # Dots on first and last
    for idx in [0, -1]:
        px, py = points[idx]
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=line_clr)
        draw.text((px - 10, py - 18), f"${prices[idx]}", fill=TEXT_CLR, font=font)

    # Current price label
    cp = prices[-1]
    change = cp - prices[0]
    pct = (change / prices[0] * 100) if prices[0] else 0
    sign = "+" if change >= 0 else ""
    label = f"Now: ${cp} ({sign}{change}, {sign}{pct:.1f}%)"
    draw.text((PAD_L, H - 25), label, fill=line_clr, font=font)

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

    # /invest  → show all companies & prices
    if not context.args:
        lines = []
        for ticker, info in COMPANIES.items():
            price = _get_price(ticker)
            lines.append(f"📊 *{ticker}* — {info['name']} — *{price}$*/share")
        header = s["invest_list"]
        await update.message.reply_text(
            header + "\n".join(lines), parse_mode="Markdown"
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
