# ==========================================
# KNTU Bot 25 — HowAllBot-style Fun Features
# ==========================================

import random
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, get_members
from strings import STRINGS


# --------- /howmuch (rate anything %) ---------
async def howmuch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if not context.args:
        if lang == "fa":
            await update.message.reply_text("❌ استفاده: /howmuch چقدر خوشگلم؟")
        else:
            await update.message.reply_text("❌ Usage: /howmuch am I smart?")
        return

    question = " ".join(context.args)
    percent = random.randint(0, 100)
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)

    if lang == "fa":
        text = f"📊 *سوال:* {question}\n\n*{percent}%* {bar}"
    else:
        text = f"📊 *Question:* {question}\n\n*{percent}%* {bar}"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /8ball (magic 8-ball) ---------
EIGHT_BALL = {
    "fa": [
        "بله، قطعاً! ✅",
        "بدون شک 💯",
        "مطمئناً بله 👍",
        "احتمالش زیاده 🤔",
        "نشانه‌ها میگن بله 🔮",
        "بعداً دوباره بپرس 🔄",
        "الان نمی‌تونم بگم 😶",
        "بهتره نگم 🤐",
        "نه! ❌",
        "شک دارم 😅",
        "احتمالاً نه 👎",
        "اصلاً! 🚫",
        "توی رویاهات 💭",
        "صد در صد! 🎯",
        "هیچوقت! 😂",
    ],
    "en": [
        "It is certain! ✅",
        "Without a doubt 💯",
        "Yes, definitely 👍",
        "Most likely 🤔",
        "Signs point to yes 🔮",
        "Ask again later 🔄",
        "Cannot predict now 😶",
        "Better not tell you 🤐",
        "No! ❌",
        "I doubt it 😅",
        "Probably not 👎",
        "Absolutely not! 🚫",
        "In your dreams 💭",
        "100%! 🎯",
        "Never! 😂",
    ],
}


async def eight_ball_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if not context.args:
        if lang == "fa":
            await update.message.reply_text("❌ استفاده: /8ball آیا فردا بارون میاد؟")
        else:
            await update.message.reply_text("❌ Usage: /8ball will it rain tomorrow?")
        return

    question = " ".join(context.args)
    answer = random.choice(EIGHT_BALL[lang])

    if lang == "fa":
        text = f"🎱 *سوال:* {question}\n\n🔮 *جواب:* {answer}"
    else:
        text = f"🎱 *Question:* {question}\n\n🔮 *Answer:* {answer}"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /whois (random member picker) ---------
async def whois_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if not context.args:
        if lang == "fa":
            await update.message.reply_text("❌ استفاده: /whois کی بهترین آدم گروهه؟")
        else:
            await update.message.reply_text("❌ Usage: /whois who is the best person here?")
        return

    question = " ".join(context.args)
    members = get_members(chat.id)

    if not members:
        if lang == "fa":
            await update.message.reply_text("❌ هنوز هیچ کسی توی گروه ثبت نشده!")
        else:
            await update.message.reply_text("❌ No members tracked yet!")
        return

    chosen_id = random.choice(members)
    try:
        member = await context.bot.get_chat_member(chat.id, chosen_id)
        name = member.user.first_name or "User"
    except Exception:
        name = f"User {chosen_id}"

    if lang == "fa":
        text = f"🎯 *سوال:* {question}\n\n👉 *جواب:* *{name}*!"
    else:
        text = f"🎯 *Question:* {question}\n\n👉 *Answer:* *{name}*!"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /truth (truth or dare - truth) ---------
TRUTHS = {
    "fa": [
        "بزرگترین رازت چیه؟ 🤫",
        "آخرین باری که گریه کردی کی بود؟ 😢",
        "از کی توی گروه خوشت میاد؟ 😏",
        "بدترین دروغی که گفتی چی بوده؟ 🤥",
        "اگه یه روز از عمرت مونده بود چیکار می‌کردی؟ ⏰",
        "خجالت‌آورترین لحظه زندگیت چی بوده؟ 😳",
        "بزرگترین ترست چیه؟ 😨",
        "آخرین بار کی استوری یکی رو استالک کردی؟ 👀",
        "اگه نامرئی بودی چیکار می‌کردی؟ 👻",
        "تا حالا عاشق شدی؟ 💕",
        "از چی توی خودت بدت میاد؟ 😕",
        "بدترین نمره‌ات چند بوده؟ 📝",
        "تا حالا دزدی کردی؟ 🤭",
        "خوابت رو تعریف کن 💤",
        "اگه برگردی عقب یه چیز رو عوض کنی چیه؟ ⏪",
    ],
    "en": [
        "What's your biggest secret? 🤫",
        "When was the last time you cried? 😢",
        "Who do you have a crush on in this group? 😏",
        "What's the biggest lie you've told? 🤥",
        "If you had one day to live, what would you do? ⏰",
        "What's your most embarrassing moment? 😳",
        "What's your biggest fear? 😨",
        "When was the last time you stalked someone's profile? 👀",
        "If you were invisible, what would you do? 👻",
        "Have you ever been in love? 💕",
        "What do you dislike about yourself? 😕",
        "What's the worst grade you've gotten? 📝",
        "Have you ever stolen something? 🤭",
        "Describe your last dream 💤",
        "If you could change one thing in your past, what? ⏪",
    ],
}


async def truth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    name = user.first_name or "User"
    truth = random.choice(TRUTHS[lang])

    if lang == "fa":
        text = f"🔥 *حقیقت برای {name}:*\n\n{truth}"
    else:
        text = f"🔥 *Truth for {name}:*\n\n{truth}"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /dare ---------
DARES = {
    "fa": [
        "یه ویسمسیج بامزه بفرست! 🎤",
        "پروفایلت رو برای ۱ ساعت عوض کن! 📸",
        "به آخرین نفری که بهت پیام داده بگو دوستت دارم! 💝",
        "یه سلفی الان بفرست! 🤳",
        "تا ۱۰ دقیقه فقط با ایموجی حرف بزن! 😜",
        "اسم کراشت رو بگو! 💘",
        "یه جوک بامزه تعریف کن! 😂",
        "صدای گربه دربیار و ویس بفرست! 🐱",
        "آخرین عکس گالریت رو بفرست! 🖼",
        "بیوگرافیت رو عوض کن و بنویس: من عاشق kntu_bot25 هستم! 🤖",
        "۵ دقیقه فقط با حروف بزرگ بنویس! 🔠",
        "یه آهنگ بخون و ویس بفرست! 🎵",
    ],
    "en": [
        "Send a funny voice message! 🎤",
        "Change your profile pic for 1 hour! 📸",
        "Tell the last person who DM'd you 'I love you'! 💝",
        "Send a selfie right now! 🤳",
        "Only speak in emojis for 10 minutes! 😜",
        "Reveal your crush's name! 💘",
        "Tell a funny joke! 😂",
        "Send a voice message meowing like a cat! 🐱",
        "Send the last photo from your gallery! 🖼",
        "Change your bio to: I love kntu_bot25! 🤖",
        "Type in ALL CAPS for 5 minutes! 🔠",
        "Sing a song and send a voice message! 🎵",
    ],
}


async def dare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    name = user.first_name or "User"
    dare = random.choice(DARES[lang])

    if lang == "fa":
        text = f"🎲 *جرئت برای {name}:*\n\n{dare}"
    else:
        text = f"🎲 *Dare for {name}:*\n\n{dare}"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /quote (fake/funny quotes) ---------
QUOTES = {
    "fa": [
        "هر کسی که زود بیدار میشه، لزوماً موفق نمیشه... شاید فقط خوابش نبرده! 😴",
        "پول خوشبختی نمیاره، ولی گریه توی لامبورگینی بهتر از گریه توی اتوبوسه! 🚗",
        "زندگی مثل دوچرخه‌ست، اگه نچرخونیش میخوری زمین! 🚲",
        "درس نخوندن هنر نیست، ولی پاس کردن بدون درس خوندن هنره! 🎓",
        "هر کسی یه استعداد داره، استعداد بعضیا خوابیدنه! 💤",
        "وقتی زندگی بهت لیمو میده، بخواه تکیلا هم بده! 🍋",
        "هیچکس کامل نیست، به جز من! 😎",
        "عشق کوره... ولی قبض گازش سنگینه! 💕🔥",
        "آدم باید همیشه مثبت فکر کنه، مخصوصا وقتی حسابش منفیه! 💰",
        "صبر کلید موفقیته... ولی کیبورد من کلید صبر نداره! ⌨️",
    ],
    "en": [
        "Not all who wake up early are successful... some just couldn't sleep! 😴",
        "Money can't buy happiness, but crying in a Ferrari is better than on a bus! 🚗",
        "Life is like a bicycle, if you stop pedaling you fall! 🚲",
        "Not studying is not a talent, but passing without studying is! 🎓",
        "Everyone has a talent. Some people's talent is sleeping! 💤",
        "When life gives you lemons, ask for tequila too! 🍋",
        "Nobody is perfect, except me! 😎",
        "Love is blind... but the neighbors aren't! 💕👀",
        "Always think positive, especially when your bank account is negative! 💰",
        "Patience is the key to success... but my keyboard has no patience key! ⌨️",
    ],
}


async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    q = random.choice(QUOTES[lang])

    if lang == "fa":
        text = f"💬 *نقل قول روز:*\n\n_{q}_"
    else:
        text = f"💬 *Quote of the Day:*\n\n_{q}_"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /advice (random advice) ---------
ADVICE = {
    "fa": [
        "آب زیاد بخور! بدنت ممنون میشه 💧",
        "یه بار دیگه به مامانت زنگ بزن، دلش تنگ شده 📞",
        "امروز یه کار مهربونانه برای یه غریبه انجام بده ❤️",
        "گوشیت رو بذار کنار و یه ساعت کتاب بخون 📚",
        "یه قدم بزن توی هوای آزاد، ذهنت صاف میشه 🚶",
        "به خودت ایمان داشته باش، تو از اون چیزی که فکر می‌کنی قوی‌تری 💪",
        "یه مهارت جدید یاد بگیر، حتی اگه کوچیک باشه 🎯",
        "زیاد نگران آینده نباش، الانت رو زندگی کن 🌟",
        "از اشتباهاتت درس بگیر، ولی خودت رو سرزنش نکن 🧠",
        "امشب زود بخواب! ☺️",
    ],
    "en": [
        "Drink more water! Your body will thank you 💧",
        "Call your mom, she misses you 📞",
        "Do one kind thing for a stranger today ❤️",
        "Put your phone down and read a book for an hour 📚",
        "Go for a walk outside, clear your mind 🚶",
        "Believe in yourself, you're stronger than you think 💪",
        "Learn a new skill, even a small one 🎯",
        "Don't worry too much about the future, live in the now 🌟",
        "Learn from your mistakes, but don't blame yourself 🧠",
        "Go to bed early tonight! ☺️",
    ],
}


async def advice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    a = random.choice(ADVICE[lang])

    if lang == "fa":
        text = f"💡 *نصیحت:*\n\n{a}"
    else:
        text = f"💡 *Advice:*\n\n{a}"

    await update.message.reply_text(text, parse_mode="Markdown")


# --------- /profile (fun fake profile card) ---------
TITLES_FA = ["هکر حرفه‌ای 💻", "نابغه ریاضی 🧮", "عاشق بی‌قرار 💕", "خوابالوی حرفه‌ای 😴",
             "جوکر گروه 🃏", "استاد پیتزا خوری 🍕", "سلطان میم 👑", "قهرمان پروکرستینیشن 🏆",
             "مهندس ناسا 🚀", "دکتر عشق 💝"]
TITLES_EN = ["Pro Hacker 💻", "Math Genius 🧮", "Hopeless Romantic 💕", "Professional Sleeper 😴",
             "Group Jester 🃏", "Pizza Master 🍕", "Meme Lord 👑", "Procrastination Champion 🏆",
             "NASA Engineer 🚀", "Love Doctor 💝"]


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    name = user.first_name or "User"
    iq = random.randint(30, 200)
    beauty = random.randint(0, 100)
    luck = random.randint(0, 100)
    title = random.choice(TITLES_FA if lang == "fa" else TITLES_EN)
    mood_fa = random.choice(["خوشحال 😊", "خسته 😩", "عصبی 😤", "عاشق 😍", "گشنه 🍔", "خوابالو 😴", "هیجان‌زده 🤩"])
    mood_en = random.choice(["Happy 😊", "Tired 😩", "Angry 😤", "In Love 😍", "Hungry 🍔", "Sleepy 😴", "Excited 🤩"])

    if lang == "fa":
        text = (
            f"🪪 *پروفایل {name}*\n\n"
            f"🏷 لقب: {title}\n"
            f"🧠 IQ: *{iq}*\n"
            f"💄 زیبایی: *{beauty}%*\n"
            f"🍀 شانس: *{luck}%*\n"
            f"😊 حال: {mood_fa}\n"
        )
    else:
        text = (
            f"🪪 *{name}'s Profile*\n\n"
            f"🏷 Title: {title}\n"
            f"🧠 IQ: *{iq}*\n"
            f"💄 Beauty: *{beauty}%*\n"
            f"🍀 Luck: *{luck}%*\n"
            f"😊 Mood: {mood_en}\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")
