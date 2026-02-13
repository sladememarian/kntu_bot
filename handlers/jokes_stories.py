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
        "یه روز یه گوشی زنگ خورد، صاحبش جواب نداد. گوشی قهر کرد رفت! 📱😂",
        "به یه نفر گفتن: چند تا زبون بلدی؟\nگفت: یکی! ولی همونو هم درست حرف نمی‌زنم! 😅",
        "یه روز باد اومد، کلاه یه نفر رو برد.\nصاحبش داد زد: آهای! من بدون تو سرما میخورم! 🎩💨",
        "به یه نفر گفتن: چرا همیشه دیر میای؟\nگفت: آخه ساعتم همیشه جلوئه، من صبر می‌کنم برسه! ⏰😂",
        "یه نفر رفت رستوران گفت: غذا سرده!\nگارسون گفت: خب بخورش تا گرم شه! 🍽️😄",
        "یه روز یه عینک رفت چشم‌پزشکی.\nدکتر گفت: مشکلت اینه که چارچوب ذهنیت محدوده! 👓😂",
        "به یه مرغ گفتن: چرا از خیابون رد شدی؟\nمرغ گفت: اون طرف Wi-Fi بهتر بود! 🐔📶",
        "معلم: اگه ۵ تا سیب داری و ۳ تاشو بدی، چند تا می‌مونه؟\nشاگرد: بستگی داره بدم یا نه! 🍎😅",
        "یه برنامه‌نویس گفت: من باگ ندارم!\nکامپیوتر: Error 404 - Honesty not found! 💻🐛",
        "یه روز یه پاکت شیر رفت مسابقه دو.\nبرنده شد چون تاریخ انقضاش نزدیک بود! 🥛🏃",
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
        "Why don't skeletons fight each other? They don't have the guts! 💀😂",
        "What do you call a bear with no teeth? A gummy bear! 🐻😄",
        "I told my computer a joke. It didn't laugh — no sense of humor, only bytes! 💻😅",
        "What do you call a dog that does magic? A Labracadabrador! 🐕✨",
        "Why did the coffee file a police report? It got mugged! ☕🚔",
        "What's the best thing about Switzerland? I don't know, but the flag is a big plus! 🇨🇭😂",
        "I'm on a seafood diet. I see food and I eat it! 🦞🍽️",
        "Why did the bicycle fall over? Because it was two-tired! 🚲😴",
        "What do you call a sleeping dinosaur? A dino-snore! 🦕💤",
        "Parallel lines have so much in common. Too bad they'll never meet! 📐😢",
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
        (
            "📖 *ربات و پروانه*\n\n"
            "توی یه کارخانه قدیمی، یه ربات کوچیک هر روز قطعات ماشین جمع می‌کرد. یه روز "
            "یه پروانه آبی از پنجره اومد تو. ربات تا حالا چیز به این زیبایی ندیده بود. "
            "سعی کرد بگیرتش ولی پروانه هر بار فرار می‌کرد. آخرش ربات فهمید بعضی چیزها "
            "رو نباید گرفت، فقط باید تماشا کرد. از اون روز، ربات هر روز پنجره رو باز می‌ذاشت. 🦋🤖"
        ),
        (
            "📖 *سکه‌ی شانس*\n\n"
            "یه پیرمرد توی بازار یه سکه قدیمی پیدا کرد. هر بار سکه رو می‌نداخت، شیر میومد. "
            "فکر کرد سکه جادویی‌ه. با اعتماد به نفس رفت مسابقه شطرنج، مسابقه دو، حتی مسابقه "
            "آشپزی! و همشون رو برد. ولی وقتی سکه رو گم کرد، فهمید شانس توی سکه نبود — "
            "توی خودش بود که جرئت امتحان کردن پیدا کرده بود! 🪙✨"
        ),
        (
            "📖 *آخرین نامه*\n\n"
            "نامه‌رسان پیر هر روز نامه می‌برد ولی هیچ‌وقت نامه‌ای برای خودش نمی‌اومد. "
            "آخرین روز کارش، یه نامه بدون آدرس پیدا کرد. بازش کرد و نوشته بود: "
            "«ممنون از تمام سال‌هایی که با لبخند نامه‌هامون رو آوردی. تو خودت بهترین پیام بودی.» "
            "چشم‌هاش پر اشک شد و فهمید دیده شده. 💌😢"
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
        (
            "📖 *The Last Library*\n\n"
            "In a world where everything was digital, one old library remained. No one visited it "
            "except a small robot who charged its battery there every night. One day the robot "
            "opened a book for the first time. The words didn't compute — they made it *feel*. "
            "The robot started reading every book, and when they finally demolished the library, "
            "the robot had memorized every single story. It became the last library. 🤖📚"
        ),
        (
            "📖 *Bridges*\n\n"
            "Two brothers lived on opposite sides of a river and hadn't spoken in years. "
            "One morning, a carpenter arrived and asked for work. The older brother said: "
            "'Build me a fence so I never have to see the other side.' The carpenter nodded. "
            "When the brother came back, there was no fence — just a beautiful bridge. "
            "His younger brother was already walking across it with open arms. 🌉💕"
        ),
        (
            "📖 *The Timekeeper's Gift*\n\n"
            "An old clockmaker could fix any clock except his own. His clocks worked perfectly, "
            "but his personal watch always ran backwards. One day a child asked why. He smiled: "
            "'Because I've learned that the best moments are the ones worth reliving.' "
            "He wound his watch backwards one more time and smiled at a memory. ⏰🕰️"
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
