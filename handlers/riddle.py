# ==========================================
# KNTU Bot 25 — Riddles
# ==========================================

import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_lang, add_balance, get_balance
from strings import STRINGS

RIDDLE_REWARD = 50

RIDDLES = {
    "fa": [
        {"q": "چیه که پا نداره ولی می‌دوه؟", "a": "آب", "options": ["آب", "باد", "سنگ", "خاک"]},
        {"q": "چیه که دهن داره ولی حرف نمی‌زنه؟", "a": "رودخانه", "options": ["رودخانه", "کوه", "درخت", "ماهی"]},
        {"q": "چیه که هرچقدر ازش برداری بزرگتر میشه؟", "a": "چاله", "options": ["چاله", "کوه", "دریا", "آسمون"]},
        {"q": "چیه که همه می‌شکنن ولی دست نمی‌زنن؟", "a": "قول", "options": ["قول", "شیشه", "دل", "تخم‌مرغ"]},
        {"q": "چیه که کلید داره ولی قفل نداره؟", "a": "پیانو", "options": ["پیانو", "در", "گاوصندوق", "ماشین"]},
        {"q": "چیه که ۴ تا پا داره ولی راه نمی‌ره؟", "a": "میز", "options": ["میز", "گربه", "سگ", "اسب"]},
        {"q": "چیه که می‌بینی ولی نمی‌تونی لمسش کنی؟", "a": "سایه", "options": ["سایه", "هوا", "نور", "بوی گل"]},
        {"q": "چیه که سر داره، دم داره ولی بدن نداره؟", "a": "سکه", "options": ["سکه", "مار", "ماهی", "مداد"]},
        {"q": "چه‌چیزی زنده نیست ولی رشد می‌کنه؟", "a": "آتش", "options": ["آتش", "گل", "درخت", "حیوان"]},
        {"q": "چیه که خیس میشه هرچی بیشتر خشک کنه؟", "a": "حوله", "options": ["حوله", "اسفنج", "موپ", "دستمال"]},
        {"q": "چیه که گوش داره ولی نمیشنوه؟", "a": "کوزه", "options": ["کوزه", "دیوار", "در", "کتاب"]},
        {"q": "چیه که بال داره پرواز نمی‌کنه؟", "a": "بینی", "options": ["بینی", "مرغ", "هواپیما", "فرشته"]},
        {"q": "چیه که روز میخوابه شب بیداره؟", "a": "ستاره", "options": ["ستاره", "جغد", "خفاش", "ماه"]},
        {"q": "چیه که هر وقت اسمش رو صدا بزنی خراب میشه؟", "a": "سکوت", "options": ["سکوت", "خواب", "آرامش", "صبر"]},
        {"q": "چیه که همه ازش فرار می‌کنن ولی نمیشه ازش فرار کرد؟", "a": "مرگ", "options": ["مرگ", "زمان", "سایه", "بارون"]},
    ],
    "en": [
        {"q": "What has keys but no locks?", "a": "Piano", "options": ["Piano", "Door", "Safe", "Car"]},
        {"q": "What has a head, a tail, but no body?", "a": "Coin", "options": ["Coin", "Snake", "Fish", "Pencil"]},
        {"q": "What gets wetter the more it dries?", "a": "Towel", "options": ["Towel", "Sponge", "Mop", "Tissue"]},
        {"q": "What can you break without touching?", "a": "Promise", "options": ["Promise", "Glass", "Heart", "Egg"]},
        {"q": "What has 4 legs but can't walk?", "a": "Table", "options": ["Table", "Cat", "Dog", "Horse"]},
        {"q": "What runs but never walks?", "a": "Water", "options": ["Water", "Wind", "Fire", "Time"]},
        {"q": "What has a mouth but never speaks?", "a": "River", "options": ["River", "Mountain", "Cave", "Jar"]},
        {"q": "The more you take, the more you leave behind. What am I?", "a": "Footsteps", "options": ["Footsteps", "Memories", "Money", "Breath"]},
        {"q": "What can travel around the world while staying in a corner?", "a": "Stamp", "options": ["Stamp", "Globe", "Map", "Internet"]},
        {"q": "What has eyes but cannot see?", "a": "Needle", "options": ["Needle", "Potato", "Storm", "Camera"]},
        {"q": "What comes once in a minute, twice in a moment, but never in a thousand years?", "a": "The letter M", "options": ["The letter M", "Time", "Luck", "A second"]},
        {"q": "What building has the most stories?", "a": "Library", "options": ["Library", "Skyscraper", "School", "Hospital"]},
        {"q": "What is always in front of you but can't be seen?", "a": "Future", "options": ["Future", "Air", "Your nose", "Destiny"]},
        {"q": "What disappears when you say its name?", "a": "Silence", "options": ["Silence", "Darkness", "A secret", "Time"]},
        {"q": "I have cities but no houses. I have mountains but no trees. What am I?", "a": "A map", "options": ["A map", "A dream", "A painting", "A globe"]},
    ],
}

# Track active riddles per chat: {chat_id: {msg_id: {answer, user_id, answered_by}}}
_active_riddles = {}


async def riddle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    riddle = random.choice(RIDDLES[lang])
    options = riddle["options"][:]
    random.shuffle(options)

    buttons = []
    for opt in options:
        cb = f"riddle:{chat.id}:{{msg_id}}:{opt}"
        buttons.append([InlineKeyboardButton(opt, callback_data=cb)])

    if lang == "fa":
        text = f"🧩 *چیستان:*\n\n{riddle['q']}\n\n💰 جایزه: *{RIDDLE_REWARD}* $"
    else:
        text = f"🧩 *Riddle:*\n\n{riddle['q']}\n\n💰 Reward: *{RIDDLE_REWARD}* $"

    # Send with placeholder, then update callback data with msg_id
    msg = await update.message.reply_text(text, parse_mode="Markdown")

    # Now create buttons with actual message ID
    real_buttons = []
    for opt in options:
        cb = f"riddle:{chat.id}:{msg.message_id}:{opt}"
        real_buttons.append([InlineKeyboardButton(opt, callback_data=cb)])

    # Store riddle data
    _active_riddles.setdefault(chat.id, {})[msg.message_id] = {
        "answer": riddle["a"],
        "asked_by": user.id,
        "answered": False,
    }

    await msg.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(real_buttons),
    )


async def riddle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data  # riddle:chat_id:msg_id:answer_text

    parts = data.split(":", 3)
    if len(parts) != 4 or parts[0] != "riddle":
        await query.answer()
        return

    chat_id = int(parts[1])
    msg_id = int(parts[2])
    chosen = parts[3]
    lang = get_lang(chat_id)
    user = query.from_user

    riddle_data = _active_riddles.get(chat_id, {}).get(msg_id)
    if not riddle_data or riddle_data["answered"]:
        msg = "This riddle is over!" if lang == "en" else "این چیستان تموم شده!"
        await query.answer(msg, show_alert=True)
        return

    correct = riddle_data["answer"]

    if chosen == correct:
        riddle_data["answered"] = True
        new_bal = add_balance(chat_id, user.id, RIDDLE_REWARD)
        name = user.first_name or "User"

        if lang == "fa":
            text = f"🧩✅ *جواب درسته!*\n\n*{name}* درست جواب داد: *{correct}*\n💰 +{RIDDLE_REWARD}$ (موجودی: {new_bal}$)"
        else:
            text = f"🧩✅ *Correct!*\n\n*{name}* got it right: *{correct}*\n💰 +{RIDDLE_REWARD}$ (Balance: {new_bal}$)"

        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        if lang == "fa":
            await query.answer("❌ اشتباهه! دوباره فکر کن.", show_alert=True)
        else:
            await query.answer("❌ Wrong! Think again.", show_alert=True)
        return

    await query.answer()
