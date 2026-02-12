# ==========================================
# KNTU Bot 25 — Book Suggestor
# ==========================================

import random
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang
from strings import STRINGS

BOOKS = {
    "fa": [
        {
            "title": "بوف کور",
            "author": "صادق هدایت",
            "desc": "شاهکار ادبیات فارسی، داستانی تاریک و رازآلود درباره تنهایی و وهم.",
            "genre": "ادبیات کلاسیک",
        },
        {
            "title": "کیمیاگر",
            "author": "پائولو کوئیلو",
            "desc": "سفر یک چوپان جوان اسپانیایی برای یافتن گنج و کشف معنای زندگی.",
            "genre": "فلسفی / ماجرایی",
        },
        {
            "title": "شازده کوچولو",
            "author": "آنتوان دو سنت‌اگزوپری",
            "desc": "داستان کوتاه و زیبا درباره عشق، دوستی و معنای واقعی زندگی.",
            "genre": "فانتزی / فلسفی",
        },
        {
            "title": "صد سال تنهایی",
            "author": "گابریل گارسیا مارکز",
            "desc": "تاریخ هفت نسل خانواده بوئندیا در شهر خیالی ماکوندو.",
            "genre": "رئالیسم جادویی",
        },
        {
            "title": "سووشون",
            "author": "سیمین دانشور",
            "desc": "داستان مقاومت و عشق در شیراز دوران جنگ جهانی دوم.",
            "genre": "رمان تاریخی",
        },
        {
            "title": "چشم‌هایش",
            "author": "بزرگ علوی",
            "desc": "داستان عاشقانه‌ای ساده و عمیق درباره دیدن و دوست داشتن.",
            "genre": "رمان عاشقانه",
        },
        {
            "title": "مدیر مدرسه",
            "author": "جلال آل‌احمد",
            "desc": "نگاهی انتقادی به سیستم آموزشی ایران از زبان یک مدیر.",
            "genre": "اجتماعی",
        },
        {
            "title": "عقل‌هاي گمشده",
            "author": "محمدعلی جمال‌زاده",
            "desc": "مجموعه داستان‌های کوتاه طنزآمیز و اجتماعی.",
            "genre": "داستان کوتاه",
        },
    ],
    "en": [
        {
            "title": "1984",
            "author": "George Orwell",
            "desc": "A dystopian novel about totalitarian government surveillance and control.",
            "genre": "Dystopian Fiction",
        },
        {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "desc": "A story of racial injustice in the American South, told through a child's eyes.",
            "genre": "Classic Fiction",
        },
        {
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "desc": "A hobbit's unexpected journey through Middle-earth with dwarves and a wizard.",
            "genre": "Fantasy",
        },
        {
            "title": "Sapiens",
            "author": "Yuval Noah Harari",
            "desc": "A brief history of humankind, from the Stone Age to the Silicon Age.",
            "genre": "Non-fiction / History",
        },
        {
            "title": "The Alchemist",
            "author": "Paulo Coelho",
            "desc": "A shepherd boy's journey to find treasure and discover the meaning of life.",
            "genre": "Philosophical Fiction",
        },
        {
            "title": "Atomic Habits",
            "author": "James Clear",
            "desc": "Practical strategies for building good habits and breaking bad ones.",
            "genre": "Self-Help",
        },
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "desc": "An epic science fiction tale of politics, religion, and ecology on a desert planet.",
            "genre": "Science Fiction",
        },
        {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "desc": "A story of wealth, love, and the American Dream in the roaring 1920s.",
            "genre": "Classic Fiction",
        },
    ],
}


async def book_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    s = STRINGS[lang]
    book = random.choice(BOOKS[lang])

    if lang == "fa":
        text = (
            f"📚 *{book['title']}*\n"
            f"✍️ نویسنده: {book['author']}\n"
            f"📂 ژانر: {book['genre']}\n\n"
            f"📝 {book['desc']}"
        )
    else:
        text = (
            f"📚 *{book['title']}*\n"
            f"✍️ Author: {book['author']}\n"
            f"📂 Genre: {book['genre']}\n\n"
            f"📝 {book['desc']}"
        )

    await update.message.reply_text(s["book_prefix"] + "\n" + text, parse_mode="Markdown")
