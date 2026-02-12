# ==========================================
# KNTU Bot 25 — Anime, Movie & Game Suggestors
# ==========================================

import random
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang
from strings import STRINGS

# ===================== ANIME =====================
ANIME_LIST = {
    "fa": [
        {"title": "Attack on Titan (حمله به تایتان)", "genre": "اکشن / فانتزی", "eps": "87 قسمت", "rating": "9.0", "desc": "بشریت در برابر تایتان‌های غول‌پیکر مبارزه می‌کنه."},
        {"title": "Death Note (دفترچه مرگ)", "genre": "تریلر / روانشناختی", "eps": "37 قسمت", "rating": "9.0", "desc": "یه دانش‌آموز دفترچه‌ای پیدا می‌کنه که می‌تونه باهاش آدم بکشه."},
        {"title": "Naruto (ناروتو)", "genre": "اکشن / ماجرایی", "eps": "720 قسمت", "rating": "8.6", "desc": "داستان یه نینجای جوون که می‌خواد هوکاگه بشه."},
        {"title": "One Piece (وان‌پیس)", "genre": "ماجرایی / کمدی", "eps": "1100+ قسمت", "rating": "8.9", "desc": "لوفی و دوستاش دنبال گنج بزرگ وان‌پیس هستن."},
        {"title": "Fullmetal Alchemist: Brotherhood", "genre": "اکشن / فانتزی", "eps": "64 قسمت", "rating": "9.2", "desc": "دو برادر کیمیاگر دنبال سنگ فیلسوف هستن."},
        {"title": "Demon Slayer (شمشیرزن دیو)", "genre": "اکشن / فانتزی", "eps": "44 قسمت", "rating": "8.7", "desc": "تانجیرو برای نجات خواهرش با دیوها می‌جنگه."},
        {"title": "Jujutsu Kaisen (جوجوتسو کایسن)", "genre": "اکشن / فانتزی", "eps": "48 قسمت", "rating": "8.8", "desc": "یوجی ایتادوری وارد دنیای جادوگران می‌شه."},
        {"title": "Steins;Gate", "genre": "علمی‌تخیلی / تریلر", "eps": "24 قسمت", "rating": "9.1", "desc": "یه دانشمند دیوونه ماشین سفر در زمان می‌سازه."},
        {"title": "Spy x Family", "genre": "کمدی / اکشن", "eps": "37 قسمت", "rating": "8.6", "desc": "یه جاسوس، یه آدمکش و یه بچه تلپات خانواده تشکیل می‌دن!"},
        {"title": "Chainsaw Man (مرد اره‌ای)", "genre": "اکشن / هورور", "eps": "12 قسمت", "rating": "8.5", "desc": "دنجی با ادغام شدن با شیطان اره‌ای، شکارچی شیطان می‌شه."},
    ],
    "en": [
        {"title": "Attack on Titan", "genre": "Action / Fantasy", "eps": "87 eps", "rating": "9.0", "desc": "Humanity fights giant titans threatening their existence."},
        {"title": "Death Note", "genre": "Thriller / Psychological", "eps": "37 eps", "rating": "9.0", "desc": "A student finds a notebook that can kill anyone whose name is written in it."},
        {"title": "Naruto", "genre": "Action / Adventure", "eps": "720 eps", "rating": "8.6", "desc": "A young ninja's journey to become the greatest Hokage."},
        {"title": "One Piece", "genre": "Adventure / Comedy", "eps": "1100+ eps", "rating": "8.9", "desc": "Luffy and his crew search for the legendary One Piece treasure."},
        {"title": "Fullmetal Alchemist: Brotherhood", "genre": "Action / Fantasy", "eps": "64 eps", "rating": "9.2", "desc": "Two alchemist brothers search for the Philosopher's Stone."},
        {"title": "Demon Slayer", "genre": "Action / Fantasy", "eps": "44 eps", "rating": "8.7", "desc": "Tanjiro fights demons to save his sister."},
        {"title": "Jujutsu Kaisen", "genre": "Action / Fantasy", "eps": "48 eps", "rating": "8.8", "desc": "Yuji Itadori enters the world of cursed spirits and sorcerers."},
        {"title": "Steins;Gate", "genre": "Sci-Fi / Thriller", "eps": "24 eps", "rating": "9.1", "desc": "A mad scientist accidentally creates a time machine."},
        {"title": "Spy x Family", "genre": "Comedy / Action", "eps": "37 eps", "rating": "8.6", "desc": "A spy, an assassin, and a telepathic girl form a fake family!"},
        {"title": "Chainsaw Man", "genre": "Action / Horror", "eps": "12 eps", "rating": "8.5", "desc": "Denji merges with a chainsaw devil and becomes a devil hunter."},
    ],
}

# ===================== MOVIES =====================
MOVIE_LIST = {
    "fa": [
        {"title": "جدایی نادر از سیمین", "genre": "درام", "year": "2011", "rating": "8.3", "desc": "داستان طلاق یه زوج ایرانی و پیچیدگی‌های اخلاقی."},
        {"title": "Inception (تلقین)", "genre": "علمی‌تخیلی / اکشن", "year": "2010", "rating": "8.8", "desc": "دزدی از رویاهای مردم و کاشتن یه ایده."},
        {"title": "The Shawshank Redemption (رستگاری در شاوشنک)", "genre": "درام", "year": "1994", "rating": "9.3", "desc": "داستان امید و آزادی یه زندانی بی‌گناه."},
        {"title": "Interstellar (میان‌ستاره‌ای)", "genre": "علمی‌تخیلی", "year": "2014", "rating": "8.7", "desc": "سفر فضایی برای نجات بشریت از نابودی."},
        {"title": "The Dark Knight (شوالیه تاریکی)", "genre": "اکشن / جنایی", "year": "2008", "rating": "9.0", "desc": "بتمن در برابر جوکر، بهترین فیلم ابرقهرمانی."},
        {"title": "Parasite (انگل)", "genre": "تریلر / درام", "year": "2019", "rating": "8.5", "desc": "خانواده فقیر کره‌ای وارد زندگی خانواده ثروتمند می‌شه."},
        {"title": "Whiplash", "genre": "درام / موسیقی", "year": "2014", "rating": "8.5", "desc": "رابطه سخت یه دانشجوی موسیقی با استادش."},
        {"title": "Forrest Gump (فارست گامپ)", "genre": "درام / کمدی", "year": "1994", "rating": "8.8", "desc": "زندگی عجیب و خاص یه مرد ساده‌دل آمریکایی."},
        {"title": "مارمولک", "genre": "کمدی / درام", "year": "2004", "rating": "7.8", "desc": "دزدی که لباس روحانیت می‌پوشه و زندگیش عوض می‌شه."},
        {"title": "The Matrix (ماتریکس)", "genre": "علمی‌تخیلی / اکشن", "year": "1999", "rating": "8.7", "desc": "واقعیت چیه؟ نئو حقیقت رو کشف می‌کنه."},
    ],
    "en": [
        {"title": "A Separation", "genre": "Drama", "year": "2011", "rating": "8.3", "desc": "An Iranian couple's divorce leads to an intense moral dilemma."},
        {"title": "Inception", "genre": "Sci-Fi / Action", "year": "2010", "rating": "8.8", "desc": "A thief steals secrets from dreams and plants an idea."},
        {"title": "The Shawshank Redemption", "genre": "Drama", "year": "1994", "rating": "9.3", "desc": "A story of hope and freedom from an innocent prisoner."},
        {"title": "Interstellar", "genre": "Sci-Fi", "year": "2014", "rating": "8.7", "desc": "A space journey to save humanity from extinction."},
        {"title": "The Dark Knight", "genre": "Action / Crime", "year": "2008", "rating": "9.0", "desc": "Batman vs. Joker — the greatest superhero film."},
        {"title": "Parasite", "genre": "Thriller / Drama", "year": "2019", "rating": "8.5", "desc": "A poor Korean family infiltrates a wealthy household."},
        {"title": "Whiplash", "genre": "Drama / Music", "year": "2014", "rating": "8.5", "desc": "A music student's intense relationship with his demanding teacher."},
        {"title": "Forrest Gump", "genre": "Drama / Comedy", "year": "1994", "rating": "8.8", "desc": "The extraordinary life of a simple-minded man."},
        {"title": "Everything Everywhere All at Once", "genre": "Sci-Fi / Comedy", "year": "2022", "rating": "8.0", "desc": "A woman discovers she can access parallel universes."},
        {"title": "The Matrix", "genre": "Sci-Fi / Action", "year": "1999", "rating": "8.7", "desc": "What is reality? Neo discovers the truth."},
    ],
}

# ===================== GAMES =====================
GAME_LIST = {
    "fa": [
        {"title": "The Witcher 3: Wild Hunt", "genre": "RPG / اکشن", "platform": "PC, PS, Xbox", "rating": "9.3", "desc": "جرالت، ویچر افسانه‌ای، دنبال دختر گمشده‌اشه."},
        {"title": "Red Dead Redemption 2", "genre": "اکشن / ماجرایی", "platform": "PC, PS, Xbox", "rating": "9.7", "desc": "زندگی آرتور مورگان در غرب وحشی آمریکا."},
        {"title": "God of War Ragnarök", "genre": "اکشن / ماجرایی", "platform": "PS5, PC", "rating": "9.4", "desc": "کریتوس و آترئوس در برابر راگناروک."},
        {"title": "Elden Ring", "genre": "RPG / سولزلایک", "platform": "PC, PS, Xbox", "rating": "9.5", "desc": "دنیای باز تاریک و چالشی از سازندگان دارک سولز."},
        {"title": "Minecraft", "genre": "سندباکس / بقا", "platform": "همه پلتفرم‌ها", "rating": "9.0", "desc": "بساز، خراب کن، کاوش کن — محدودیتی نیست!"},
        {"title": "GTA V", "genre": "اکشن / دنیای باز", "platform": "PC, PS, Xbox", "rating": "9.6", "desc": "سه دزد در لس سانتوس ماجراجویی می‌کنن."},
        {"title": "Valorant", "genre": "شوتر تاکتیکی", "platform": "PC", "rating": "8.5", "desc": "بازی شوتر رقابتی ۵ در ۵ با قابلیت‌های ویژه."},
        {"title": "Hollow Knight", "genre": "متروییدوانیا", "platform": "PC, PS, Xbox, Switch", "rating": "9.1", "desc": "ماجراجویی در دنیای زیرزمینی حشرات!"},
        {"title": "Cyberpunk 2077", "genre": "RPG / اکشن", "platform": "PC, PS, Xbox", "rating": "8.5", "desc": "زندگی در نایت‌سیتی آینده‌ی سایبرپانک."},
        {"title": "Stardew Valley", "genre": "شبیه‌سازی / مزرعه‌داری", "platform": "همه پلتفرم‌ها", "rating": "9.0", "desc": "مزرعه‌داری آرامش‌بخش با داستان‌های دوست‌داشتنی."},
    ],
    "en": [
        {"title": "The Witcher 3: Wild Hunt", "genre": "RPG / Action", "platform": "PC, PS, Xbox", "rating": "9.3", "desc": "Geralt, a legendary witcher, searches for his lost adopted daughter."},
        {"title": "Red Dead Redemption 2", "genre": "Action / Adventure", "platform": "PC, PS, Xbox", "rating": "9.7", "desc": "Arthur Morgan's life in the American Wild West."},
        {"title": "God of War Ragnarök", "genre": "Action / Adventure", "platform": "PS5, PC", "rating": "9.4", "desc": "Kratos and Atreus face Ragnarök."},
        {"title": "Elden Ring", "genre": "RPG / Souls-like", "platform": "PC, PS, Xbox", "rating": "9.5", "desc": "A dark, challenging open world from the Dark Souls creators."},
        {"title": "Minecraft", "genre": "Sandbox / Survival", "platform": "All platforms", "rating": "9.0", "desc": "Build, destroy, explore — no limits!"},
        {"title": "GTA V", "genre": "Action / Open World", "platform": "PC, PS, Xbox", "rating": "9.6", "desc": "Three criminals in Los Santos on wild adventures."},
        {"title": "Valorant", "genre": "Tactical Shooter", "platform": "PC", "rating": "8.5", "desc": "Competitive 5v5 shooter with unique character abilities."},
        {"title": "Hollow Knight", "genre": "Metroidvania", "platform": "PC, PS, Xbox, Switch", "rating": "9.1", "desc": "Adventure through an underground insect kingdom!"},
        {"title": "Cyberpunk 2077", "genre": "RPG / Action", "platform": "PC, PS, Xbox", "rating": "8.5", "desc": "Life in the futuristic Night City."},
        {"title": "Stardew Valley", "genre": "Simulation / Farming", "platform": "All platforms", "rating": "9.0", "desc": "Peaceful farming with lovely stories."},
    ],
}


def _format_item(item: dict, lang: str, category: str) -> str:
    if category == "anime":
        if lang == "fa":
            return (
                f"🎌 *{item['title']}*\n"
                f"📂 ژانر: {item['genre']}\n"
                f"📺 تعداد قسمت: {item['eps']}\n"
                f"⭐ امتیاز: {item['rating']}\n\n"
                f"📝 {item['desc']}"
            )
        return (
            f"🎌 *{item['title']}*\n"
            f"📂 Genre: {item['genre']}\n"
            f"📺 Episodes: {item['eps']}\n"
            f"⭐ Rating: {item['rating']}\n\n"
            f"📝 {item['desc']}"
        )
    elif category == "movie":
        if lang == "fa":
            return (
                f"🎬 *{item['title']}*\n"
                f"📂 ژانر: {item['genre']}\n"
                f"📅 سال: {item['year']}\n"
                f"⭐ امتیاز: {item['rating']}\n\n"
                f"📝 {item['desc']}"
            )
        return (
            f"🎬 *{item['title']}*\n"
            f"📂 Genre: {item['genre']}\n"
            f"📅 Year: {item['year']}\n"
            f"⭐ Rating: {item['rating']}\n\n"
            f"📝 {item['desc']}"
        )
    else:  # game
        if lang == "fa":
            return (
                f"🎮 *{item['title']}*\n"
                f"📂 ژانر: {item['genre']}\n"
                f"🖥 پلتفرم: {item['platform']}\n"
                f"⭐ امتیاز: {item['rating']}\n\n"
                f"📝 {item['desc']}"
            )
        return (
            f"🎮 *{item['title']}*\n"
            f"📂 Genre: {item['genre']}\n"
            f"🖥 Platform: {item['platform']}\n"
            f"⭐ Rating: {item['rating']}\n\n"
            f"📝 {item['desc']}"
        )


async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    s = STRINGS[lang]
    anime = random.choice(ANIME_LIST[lang])
    text = _format_item(anime, lang, "anime")
    await update.message.reply_text(s["anime_prefix"] + "\n" + text, parse_mode="Markdown")


async def movie_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    s = STRINGS[lang]
    movie = random.choice(MOVIE_LIST[lang])
    text = _format_item(movie, lang, "movie")
    await update.message.reply_text(s["movie_prefix"] + "\n" + text, parse_mode="Markdown")


async def game_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    s = STRINGS[lang]
    game = random.choice(GAME_LIST[lang])
    text = _format_item(game, lang, "game")
    await update.message.reply_text(s["game_prefix"] + "\n" + text, parse_mode="Markdown")
