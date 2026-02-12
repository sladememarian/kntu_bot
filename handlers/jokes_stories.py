# ==========================================
# KNTU Bot 25 — Jokes & Stories
# ==========================================

import random
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang
from strings import STRINGS

# ---- Built-in jokes (offline fallback) ----
JOKES = {
    "fa": [
        "یه روز یه مورچه رفت باشگاه، برگشت مورچه‌نگاه شد! 😂",
        "معلم: بچه‌ها کی می‌دونه ماه چقدر از زمین دوره؟\nشاگرد: خب معلوم نیست، من تا حالا نرفتم! 😄",
        "به یه نفر گفتن: چرا داری آینه رو می‌شکنی؟\nگفت: می‌خوام ببینم اون تو کی بود! 🤣",
        "یه روز یه مداد رفت دکتر، دکتر گفت: مشکلت نوکیه! 😂",
        "به یه نفر گفتن: اسمت چیه؟\nگفت: Wi-Fi\nگفتن: اسم واقعیت چیه؟\nگفت: بدون رمز نمیگم! 😅",
        "معلم پرسید: آب در چند درجه یخ می‌زنه؟\nشاگرد: نمی‌دونم، ولی تو یخچال ما همیشه یخ هست! 🧊😂",
        "دکتر به مریض: شما باید کمتر قهوه بخورید.\nمریض: من چایی می‌خورم.\nدکتر: پس وضعتون بدتره! ☕😄",
        "یه روز یه کتاب رفت دکتر، دکتر گفت: بشین صفحه‌هات رو باز کن! 📖😂",
        "به یه برنامه‌نویس گفتن: زندگیت چطوره؟\nگفت: while(true) { work(); sleep(3); } 💻😅",
        "یه روز یه ماهی رفت مدرسه، بهش گفتن: تو که آب زیر کاهی! 🐟😂",
    ],
    "en": [
        "Why don't scientists trust atoms? Because they make up everything! 😂",
        "I told my wife she was drawing her eyebrows too high. She looked surprised! 😄",
        "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾😂",
        "I'm reading a book about anti-gravity. It's impossible to put down! 📖😅",
        "Why don't eggs tell jokes? They'd crack each other up! 🥚😂",
        "What do you call a fake noodle? An impasta! 🍝😄",
        "Why did the programmer quit? Because he didn't get arrays! 💻😂",
        "What's a computer's favorite snack? Microchips! 🖥😅",
        "Why was the math book sad? It had too many problems! 📚😢",
        "I used to hate facial hair, but then it grew on me! 🧔😂",
    ],
}

STORIES = {
    "fa": [
        (
            "📖 *روزی روزگاری...*\n\n"
            "یه پسر جوون توی یه روستای کوچیک زندگی می‌کرد. هر روز صبح زود بیدار می‌شد "
            "و به کوه می‌رفت تا گل‌های وحشی جمع کنه. یه روز یه گل عجیب پیدا کرد که شب‌ها "
            "نور می‌داد. اون گل رو برد خونه و از اون شب به بعد، هیچ‌وقت از تاریکی نترسید. "
            "مردم روستا بهش می‌گفتن: «پسر نور» ✨"
        ),
        (
            "📖 *داستان درخت آرزوها*\n\n"
            "یه دختر کوچولو هر روز زیر یه درخت بزرگ می‌نشست و آرزوهاش رو بهش می‌گفت. "
            "یه روز درخت جواب داد: «من همه آرزوهات رو شنیدم، ولی باید خودت قدم اول رو برداری.» "
            "دختر تعجب کرد ولی از اون روز شروع کرد به تلاش. سال‌ها بعد، وقتی به آرزوهاش "
            "رسید، برگشت پیش درخت و گفت: «ممنون که بهم گفتی خودم باید شروع کنم.» 🌳"
        ),
        (
            "📖 *گربه‌ی ماجراجو*\n\n"
            "یه گربه‌ی کوچولو بود که دوست داشت ماجراجویی کنه. یه روز از خونه فرار کرد "
            "و رفت توی جنگل. اونجا با یه خرگوش دوست شد، با یه پرنده پرواز کرد (البته افتاد!) "
            "و آخر شب وقتی برگشت خونه، صاحبش بغلش کرد و گفت: «دیگه فرار نکن!» "
            "ولی گربه فقط خمیازه کشید 😺"
        ),
    ],
    "en": [
        (
            "📖 *Once upon a time...*\n\n"
            "In a small village by the sea, there lived an old fisherman who never caught any fish. "
            "Everyone laughed at him, but he kept going to the sea every day. One morning, instead of "
            "a fish, he pulled out a golden lamp. When he rubbed it, a genie appeared and said: "
            "'Your patience has been your greatest wish.' From that day, the sea was always kind to him. 🌊"
        ),
        (
            "📖 *The Stargazer*\n\n"
            "A young girl loved watching stars. Every night she'd climb to the rooftop and count them. "
            "One night, a star fell right into her backyard. It was tiny, glowing, and warm. "
            "She kept it in a jar, and it lit her room every night. Years later, when she became a "
            "famous astronomer, she'd say: 'It all started with one fallen star.' ⭐"
        ),
        (
            "📖 *The Code That Came Alive*\n\n"
            "A programmer was debugging at 3 AM. Suddenly, his code started writing itself. "
            "Line by line, it composed a poem about freedom and dreams. The programmer stared in awe. "
            "When it finished, the last line read: 'Even code dreams of being more than logic.' "
            "He saved the file as 'miracle.py' and never deleted it. 💻✨"
        ),
    ],
}


# --------- /joke ---------
async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    s = STRINGS[lang]
    joke = random.choice(JOKES[lang])
    await update.message.reply_text(s["joke_prefix"] + joke, parse_mode="Markdown")


# --------- /story ---------
async def story_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    s = STRINGS[lang]
    story = random.choice(STORIES[lang])
    await update.message.reply_text(s["story_prefix"] + "\n" + story, parse_mode="Markdown")
