# ==========================================
# KNTU Bot 25 — Persian (Pahlavi/Achaemenid) Calendar
# ==========================================

import random
from datetime import date, datetime
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, get_balance, add_balance, get_all_balances, load_data, save_data
from strings import STRINGS

# Persian Solar (Shamsi) months
PERSIAN_MONTHS = {
    "fa": [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ],
    "en": [
        "Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
        "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"
    ],
}

# Simple Gregorian → Persian Solar conversion (approximate)
def _gregorian_to_persian(g_y, g_m, g_d):
    """Approximate Gregorian to Persian Solar (Jalali) conversion."""
    g_days_in_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy = g_y - 1600
    gm = g_m - 1
    gd = g_d - 1
    g_d_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400 + g_days_in_month[gm] + gd
    if gm > 1 and ((gy + 1600) % 4 == 0 and ((gy + 1600) % 100 != 0 or (gy + 1600) % 400 == 0)):
        g_d_no += 1

    j_d_no = g_d_no - 79
    j_np = j_d_no // 12053
    j_d_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_d_no // 1461)
    j_d_no %= 1461

    if j_d_no >= 366:
        jy += (j_d_no - 1) // 365
        j_d_no = (j_d_no - 1) % 365

    for i in range(11):
        jmi = 31 if i < 6 else 30
        if j_d_no < jmi:
            break
        j_d_no -= jmi

    jm = i + 1
    jd = j_d_no + 1
    return jy, jm, jd


def get_persian_date():
    """Returns (year, month, day) in Persian Solar calendar."""
    today = date.today()
    return _gregorian_to_persian(today.year, today.month, today.day)


# Special days in Persian calendar (month, day)
# Pahlavi/Achaemenid & ancient Iranian celebrations (NOT Islamic)
SPECIAL_DAYS = {
    (1, 1):   {"name_fa": "🎉 نوروز", "name_en": "🎉 Nowruz (Persian New Year)", "prize": 500,
               "desc_fa": "سال نو مبارک! نوروز باستانی خجسته باد! 🌸", "desc_en": "Happy New Year! Blessed ancient Nowruz! 🌸"},
    (1, 2):   {"name_fa": "🌿 نوروز (دوم)", "name_en": "🌿 Nowruz (Day 2)", "prize": 200,
               "desc_fa": "دومین روز نوروز باستانی! شادی و سرور! 🎊", "desc_en": "Second day of Nowruz! Joy and celebration! 🎊"},
    (1, 13):  {"name_fa": "🌳 سیزده به در", "name_en": "🌳 Sizdah Bedar (Nature Day)", "prize": 300,
               "desc_fa": "روز طبیعت! برو بیرون و لذت ببر! 🏕️", "desc_en": "Nature Day! Go outside and enjoy! 🏕️"},
    (4, 13):  {"name_fa": "💧 تیرگان", "name_en": "💧 Tirgan (Water Festival)", "prize": 250,
               "desc_fa": "جشن تیرگان! جشن آب و باران! 🌊", "desc_en": "Tirgan Festival! Celebration of water and rain! 🌊"},
    (7, 10):  {"name_fa": "🍂 مهرگان", "name_en": "🍂 Mehregan (Autumn Festival)", "prize": 300,
               "desc_fa": "جشن مهرگان! جشن پاییز و محبت! 🍁", "desc_en": "Mehregan! Festival of autumn and love! 🍁"},
    (8, 10):  {"name_fa": "🔥 آبانگان", "name_en": "🔥 Abanegan (Water Festival)", "prize": 200,
               "desc_fa": "جشن آبانگان! گرامی‌داشت آب! 💦", "desc_en": "Abanegan! Honoring water! 💦"},
    (9, 1):   {"name_fa": "🔥 آذرگان", "name_en": "🔥 Azargan (Fire Festival)", "prize": 200,
               "desc_fa": "جشن آذرگان! گرامی‌داشت آتش! 🕯️", "desc_en": "Azargan! Honoring fire! 🕯️"},
    (9, 30):  {"name_fa": "🌑 شب یلدا", "name_en": "🌑 Yalda Night (Longest Night)", "prize": 400,
               "desc_fa": "شب یلدا مبارک! بلندترین شب سال! انار و هندونه! 🍉", "desc_en": "Happy Yalda Night! The longest night! Pomegranates and watermelon! 🍉"},
    (10, 1):  {"name_fa": "🎊 جشن دیگان", "name_en": "🎊 Deygan Festival", "prize": 200,
               "desc_fa": "جشن دیگان! روز آفرینش آب! 💧", "desc_en": "Deygan Festival! Day of water creation! 💧"},
    (11, 5):  {"name_fa": "🌟 جشن نوسره", "name_en": "🌟 Jashn-e Noosareh", "prize": 200,
               "desc_fa": "جشن نوسره! جشن آتش در بهمن! 🔥", "desc_en": "Noosareh Festival! Fire festival in Bahman! 🔥"},
    (11, 22): {"name_fa": "👑 جشن بهمنگان", "name_en": "👑 Bahmanegan Festival", "prize": 250,
               "desc_fa": "جشن بهمنگان! روز اندیشه نیک! 🧠", "desc_en": "Bahmanegan! Day of good thoughts! 🧠"},
    (12, 5):  {"name_fa": "🌸 جشن اسفندگان", "name_en": "🌸 Esfandegan (Love Day)", "prize": 300,
               "desc_fa": "جشن اسفندگان! روز عشق و محبت ایرانی! ❤️", "desc_en": "Esfandegan! Iranian day of love! ❤️"},
    (12, 29): {"name_fa": "🔥 چهارشنبه سوری", "name_en": "🔥 Chaharshanbe Suri (Fire Festival)", "prize": 350,
               "desc_fa": "چهارشنبه سوری! از آتش بپر! زردی من از تو، سرخی تو از من! 🎆",
               "desc_en": "Chaharshanbe Suri! Jump over fire! Your redness is mine, my yellowness is yours! 🎆"},
}


async def calendar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's Persian date and check for special day."""
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    jy, jm, jd = get_persian_date()
    month_name = PERSIAN_MONTHS[lang][jm - 1]

    if lang == "fa":
        date_text = f"📅 *تقویم ایران باستان*\n\n🗓 امروز: *{jd} {month_name} {jy}*"
    else:
        date_text = f"📅 *Ancient Persian Calendar*\n\n🗓 Today: *{jd} {month_name} {jy}*"

    special = SPECIAL_DAYS.get((jm, jd))
    if special:
        name = special["name_fa"] if lang == "fa" else special["name_en"]
        desc = special["desc_fa"] if lang == "fa" else special["desc_en"]
        prize = special["prize"]
        date_text += f"\n\n🎊 *{name}*\n{desc}\n\n🎁 جایزه: *{prize}$*" if lang == "fa" else \
                     f"\n\n🎊 *{name}*\n{desc}\n\n🎁 Prize: *{prize}$*"

        # Check if prize already claimed today
        today_str = date.today().isoformat()
        data = load_data()
        cal_claims = data.get("calendar_claims", {}).get(str(chat.id), {})
        user = update.effective_user
        user_claim = cal_claims.get(str(user.id), "")

        if user_claim != today_str:
            add_balance(chat.id, user.id, prize)
            cal_data = data.setdefault("calendar_claims", {}).setdefault(str(chat.id), {})
            cal_data[str(user.id)] = today_str
            save_data(data)
            bal = get_balance(chat.id, user.id)
            if lang == "fa":
                date_text += f"\n\n✅ جایزه دریافت شد! موجودی: *{bal}$*"
            else:
                date_text += f"\n\n✅ Prize claimed! Balance: *{bal}$*"
        else:
            if lang == "fa":
                date_text += "\n\n⚠️ جایزه امروز رو قبلاً دریافت کردی!"
            else:
                date_text += "\n\n⚠️ You already claimed today's prize!"
    else:
        # Show next upcoming special day
        upcoming = _get_next_special(jm, jd, lang)
        if upcoming:
            date_text += f"\n\n{upcoming}"

    await update.message.reply_text(date_text, parse_mode="Markdown")


def _get_next_special(current_month: int, current_day: int, lang: str) -> str:
    """Find the next upcoming special day."""
    sorted_days = sorted(SPECIAL_DAYS.keys())
    for m, d in sorted_days:
        if (m, d) > (current_month, current_day):
            info = SPECIAL_DAYS[(m, d)]
            name = info["name_fa"] if lang == "fa" else info["name_en"]
            month_name = PERSIAN_MONTHS[lang][m - 1]
            if lang == "fa":
                return f"📌 رویداد بعدی: *{name}* — {d} {month_name}"
            else:
                return f"📌 Next event: *{name}* — {month_name} {d}"
    # Wrap around to next year
    if sorted_days:
        m, d = sorted_days[0]
        info = SPECIAL_DAYS[(m, d)]
        name = info["name_fa"] if lang == "fa" else info["name_en"]
        month_name = PERSIAN_MONTHS[lang][m - 1]
        if lang == "fa":
            return f"📌 رویداد بعدی: *{name}* — {d} {month_name} (سال بعد)"
        else:
            return f"📌 Next event: *{name}* — {month_name} {d} (next year)"
    return ""
