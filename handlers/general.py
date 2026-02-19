# ==========================================
# KNTU Bot 25 — General Commands (start, help, lang, debug)
# ==========================================

import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from storage import get_lang, set_lang, get_debug, set_debug, load_data, _use_pg, save_data
from strings import STRINGS


# ═══════════════════════════════════════════════════
# HELP SYSTEM — Interactive category-based help
# ═══════════════════════════════════════════════════

_HELP_CATEGORIES = {
    "fa": {
        "fun": {
            "title": "🎮 بازی و سرگرمی",
            "text": (
                "🎮 *بازی و سرگرمی*\n\n"
                "💕 /ship — شیپ دو نفر تصادفی\n"
                "🏷 /lagab \\[لقب\\] — لقب دادن (ریپلای)\n"
                "😂 /joke — جوک\n"
                "📖 /story — داستان کوتاه\n"
                "😏 /rizz — نرخ ریز\n"
                "🌈 /gay — نرخ گی\n"
                "🔥 /truth — حقیقت\n"
                "🎲 /dare — جرئت\n"
                "🎮 /xo — بازی دوز (ریپلای)\n"
                "🧩 /riddle — چیستان (۱۵ تا در روز)\n"
                "🎱 /8ball \\[سوال\\] — گوی جادو\n"
                "📊 /howmuch \\[سوال\\] — چقدر؟\n"
                "🎯 /whois \\[سوال\\] — کی هست؟\n"
                "💬 /quote — نقل قول\n"
                "💡 /advice — نصیحت\n"
                "🪪 /profile — کارت پروفایل\n"
            ),
        },
        "gacha": {
            "title": "🎰 گاچا و کلکسیون",
            "text": (
                "🎰 *گاچا و کلکسیون*\n\n"
                "🎲 /roll — رول کن! شخصیت اسطوره‌ای بگیر\n"
                "🃏 /collection — مجموعه شخصیت‌هات\n"
                "💰 /sellchar \\[نام\\] — فروش شخصیت\n"
                "🔄 /tradechar \\[نام\\] — معامله (ریپلای)\n\n"
                "📊 *نادرگی‌ها:*\n"
                "⚪ معمولی (45%) | 🟢 غیرمعمول (25%)\n"
                "🔵 کمیاب (18%) | 🟣 حماسی (9%)\n"
                "🟡 افسانه‌ای (3%)\n\n"
                "🏛️ *شخصیت‌ها:* اسطوره‌های جهان\n"
                "⚡ زئوس | 👁️ اودین | ☀️ رع\n"
                "🦁 رستم | 🔨 ثور | 🦉 آتنا\n"
                "🃏 لوکی | 🧙‍♂️ مرلین | ...\n\n"
                "🖼 _هر شخصیت تصویر آواتار منحصر به فرد داره!_\n"
                "💡 _۵ رول هر ۴ ساعت — اولین نفری که بزنه میگیره!_"
            ),
        },
        "economy": {
            "title": "💰 اقتصاد",
            "text": (
                "💰 *اقتصاد*\n\n"
                "👛 /wallet — موجودی کیف پول\n"
                "📅 /daily — دریافت روزانه (+ استریک!)\n"
                "💼 /work — کار کردن (هر ۱ ساعت)\n"
                "🎡 /spin — چرخ شانس (هر ۸ ساعت)\n"
                "🎣 /fish — ماهیگیری\n"
                "⛏ /mine — معدن\n"
                "📜 /quest — ماموریت روزانه\n\n"
                "🎲 *شرط‌بندی:*\n"
                "🪙 /bet \\[مبلغ\\] | 🎰 /slots \\[مبلغ\\]\n"
                "🎲 /dice \\[فرد/زوج\\] \\[مبلغ\\]\n"
                "✂️ /rps \\[سنگ/کاغذ/قیچی\\] \\[مبلغ\\]\n\n"
                "💸 *تعاملی:*\n"
                "🦹 /rob — دزدی (ریپلای)\n"
                "💸 /give \\[مبلغ\\] — انتقال (ریپلای)\n"
                "🎯 /bounty \\[مبلغ\\] — بانتی (ریپلای)\n"
                "🎯 /bounties — لیست بانتی‌ها\n\n"
                "📈 *سرمایه‌گذاری:*\n"
                "📈 /invest | 📉 /sell | 💼 /portfolio | 📊 /profit\n\n"
                "🏠 /realestate — املاک | 🏘 /buyproperty | 🏚 /sellproperty\n"
                "🔒 /jail | 🏆 /leaderboard | 💝 /donate | 🏅 /charity\n"
                "🌍 /event — رویداد روز | 📊 /economy — وضعیت اقتصادی\n\n"
                "🛡️ _سپر و مین از فروشگاه بخر تا از دزدی محافظت کنی!_\n"
                "🎁 _کیف پول‌های تصادفی هر ۸۰-۱۵۰ پیام میفتن!_"
            ),
        },
        "clan": {
            "title": "⚔️ کلن و جنگ",
            "text": (
                "⚔️ *سیستم کلن*\n\n"
                "📝 /clan create \\[نام\\] — ساخت کلن (5,000$)\n"
                "🤝 /clan join — عضویت (ریپلای)\n"
                "🚪 /clan leave — خروج\n"
                "📊 /clan info — اطلاعات کلن\n"
                "👥 /clan members — لیست اعضا\n"
                "💰 /clan deposit \\[مبلغ\\] — واریز به صندوق\n"
                "💸 /clan withdraw \\[مبلغ\\] — برداشت (فقط رهبر)\n"
                "⚔️ /clan war — جنگ با کلن دشمن (ریپلای)\n"
                "📋 /clan list — لیست همه کلن‌ها\n\n"
                "💡 _حداکثر ۱۰ عضو • رهبر میتونه برداشت کنه_\n"
                "⚔️ _قدرت جنگ = اعضا×۱۰ + بردها×۳ + شانس!_"
            ),
        },
        "shops": {
            "title": "🛒 فروشگاه‌ها",
            "text": (
                "🛒 *فروشگاه‌ها*\n\n"
                "👕 /shop — فروشگاه لباس و اکسسوری\n"
                "🛍 /buy \\[آیتم\\] — خرید آیتم\n"
                "🐾 /petshop — پت شاپ\n"
                "🐶 /buypet \\[حیوان\\] — خرید حیوان\n"
                "🍽 /foodshop — فود شاپ\n"
                "🍔 /buyfood \\[غذا\\] — خرید غذا\n"
                "😋 /eat \\[غذا\\] — خوردن غذا\n"
                "🥤 /drink \\[نوشیدنی\\] — نوشیدن\n"
                "⚔️ /abilities — فروشگاه قدرت\n"
                "⚡ /buyability \\[قدرت\\] — خرید قدرت\n"
                "🎒 /inventory — کوله‌پشتی\n"
                "🎁 /gift \\[آیتم\\] — هدیه (ریپلای)\n\n"
                "🛡️ *محافظت:*\n"
                "🛡️ /buy shield — سپر (۳۰۰$) — جلوی دزدی رو بگیر\n"
                "💣 /buy landmine — مین (۵۰۰$) — دزد رو منفجر کن!\n\n"
                "🥊 *قدرت‌ها:*\n"
                "/punch /hug /kiss /kill /slap\n"
                "/tickle /poke /bite /pat /highfive /revive\n\n"
                "💡 _قیمت‌ها با تقاضا بالا میره!_"
            ),
        },
        "bank": {
            "title": "🏦 بانک و کازینو",
            "text": (
                "🏦 *بانک و کازینو*\n\n"
                "🏦 /bank \\[deposit/withdraw\\] \\[مبلغ\\] — حساب بانکی\n"
                "💸 /loan \\[take/pay\\] \\[مبلغ\\] — وام\n"
                "🏢 /bankmanager — مدیر بانک\n"
                "🤫 /embezzle — اختلاس (مدیر)\n"
                "🔍 /investigate — بازرسی مدیر\n"
                "💣 /bankrob — سرقت بانک (۴+ نفر)\n"
                "⚖️ /bail — وثیقه (ریپلای)\n"
                "🔓 /jailbreak — فرار از زندان (۳+ نفر)\n\n"
                "🎰 *کازینو:*\n"
                "🎰 /casino — منوی کازینو\n"
                "🎰 /megaslots \\[مبلغ\\] — مگا اسلات\n"
                "🃏 /blackjack \\[مبلغ\\] — بلک جک\n"
                "🪙 /coinflip \\[مبلغ\\] — شیر یا خط\n"
                "🍺 /bar — بار و نوشیدنی\n"
                "👑 /casinoleader — رئیس کازینو\n"
                "💰 /paytax — پرداخت مالیات\n"
                "🎮 /casinogame — بازی HTML5 آنلاین\n"
            ),
        },
        "ai": {
            "title": "🧠 هوش مصنوعی",
            "text": (
                "🧠 *هوش مصنوعی*\n\n"
                "🧠 /ai \\[سوال\\] — ایجنت هوشمند LangChain\n"
                "🦋 /ai3 \\[متن\\] — آفلیا (هوش احساسی)\n"
                "📊 /ai3stats — آمار مغز آفلیا\n\n"
                "💡 _آفلیا از مکالمات گروه یاد می‌گیره و_\n"
                "_بر اساس احساسات جواب می‌ده!_"
            ),
        },
        "tools": {
            "title": "🔧 ابزارها",
            "text": (
                "🔧 *ابزارها و متفرقه*\n\n"
                "🎨 /imagine \\[توضیح\\] — ساخت تصویر\n"
                "🎵 /music \\[نام\\] — جستجو آهنگ\n"
                "📚 /book — پیشنهاد کتاب\n"
                "🎌 /anime — پیشنهاد انیمه\n"
                "🎬 /movie — پیشنهاد فیلم\n"
                "🎮 /game — پیشنهاد بازی\n"
                "📰 /news — اخبار\n"
                "👨‍👩‍👧‍👦 /family — درخت خانوادگی\n"
                "📅 /calendar — تقویم باستان\n"
                "🗺 /places — مکان‌ها\n"
                "💑 /date \\[مکان\\] — قرار (ریپلای)\n"
                "🐾 /giftpet — هدیه حیوان (ریپلای)\n"
                "🍽 /giftfood — هدیه غذا (ریپلای)\n"
                "⚠️ warn — اخطار (ریپلای، ادمین)\n"
                "🌐 /lang — تغییر زبان\n"
            ),
        },
    },
    "en": {
        "fun": {
            "title": "🎮 Fun & Games",
            "text": (
                "🎮 *Fun & Games*\n\n"
                "💕 /ship — Ship two random members\n"
                "🏷 /lagab \\[nickname\\] — Set nickname (reply)\n"
                "😂 /joke — Tell a joke\n"
                "📖 /story — Short story\n"
                "😏 /rizz — Rate rizz\n"
                "🌈 /gay — Rate gayness\n"
                "🔥 /truth — Truth question\n"
                "🎲 /dare — Dare challenge\n"
                "🎮 /xo — Tic-tac-toe (reply)\n"
                "🧩 /riddle — Riddle with reward (15/day)\n"
                "🎱 /8ball \\[question\\] — Magic 8-ball\n"
                "📊 /howmuch \\[question\\] — How much %?\n"
                "🎯 /whois \\[question\\] — Who is?\n"
                "💬 /quote — Random quote\n"
                "💡 /advice — Random advice\n"
                "🪪 /profile — Profile card\n"
            ),
        },
        "gacha": {
            "title": "🎰 Gacha & Collection",
            "text": (
                "🎰 *Gacha & Collection*\n\n"
                "🎲 /roll — Roll for mythological characters!\n"
                "🃏 /collection — View your collection\n"
                "💰 /sellchar \\[name\\] — Sell a character\n"
                "🔄 /tradechar \\[name\\] — Trade (reply)\n\n"
                "📊 *Rarities:*\n"
                "⚪ Common (45%) | 🟢 Uncommon (25%)\n"
                "🔵 Rare (18%) | 🟣 Epic (9%)\n"
                "🟡 Legendary (3%)\n\n"
                "🏛️ *Characters:* World mythology\n"
                "⚡ Zeus | 👁️ Odin | ☀️ Ra\n"
                "🦁 Rostam | 🔨 Thor | 🦉 Athena\n"
                "🃏 Loki | 🧙‍♂️ Merlin | ...\n\n"
                "🖼 _Each character has a unique avatar portrait!_\n"
                "💡 _5 rolls every 4 hours — first click claims!_"
            ),
        },
        "economy": {
            "title": "💰 Economy",
            "text": (
                "💰 *Economy*\n\n"
                "👛 /wallet — Check balance\n"
                "📅 /daily — Daily reward (+ streak!)\n"
                "💼 /work — Work & earn (1h cooldown)\n"
                "🎡 /spin — Spin wheel (8h cooldown)\n"
                "🎣 /fish — Go fishing\n"
                "⛏ /mine — Mine for resources\n"
                "📜 /quest — Daily quest\n\n"
                "🎲 *Gambling:*\n"
                "🪙 /bet \\[amount\\] | 🎰 /slots \\[amount\\]\n"
                "🎲 /dice \\[odd/even\\] \\[amount\\]\n"
                "✂️ /rps \\[rock/paper/scissors\\] \\[amount\\]\n\n"
                "💸 *Social:*\n"
                "🦹 /rob — Rob someone (reply)\n"
                "💸 /give \\[amount\\] — Transfer (reply)\n"
                "🎯 /bounty \\[amount\\] — Place bounty (reply)\n"
                "🎯 /bounties — Active bounties\n\n"
                "📈 *Investing:*\n"
                "📈 /invest | 📉 /sell | 💼 /portfolio | 📊 /profit\n\n"
                "🏠 /realestate | 🏘 /buyproperty | 🏚 /sellproperty\n"
                "🔒 /jail | 🏆 /leaderboard | 💝 /donate | 🏅 /charity\n"
                "🌍 /event — Daily event | 📊 /economy — Status\n\n"
                "🛡️ _Buy shields & landmines from shop to protect yourself!_\n"
                "🎁 _Random cash bags drop every 80-150 messages!_"
            ),
        },
        "clan": {
            "title": "⚔️ Clans & War",
            "text": (
                "⚔️ *Clan System*\n\n"
                "📝 /clan create \\[name\\] — Create clan (5,000$)\n"
                "🤝 /clan join — Join (reply to member)\n"
                "🚪 /clan leave — Leave clan\n"
                "📊 /clan info — Clan stats\n"
                "👥 /clan members — Member list\n"
                "💰 /clan deposit \\[amount\\] — Deposit to clan bank\n"
                "💸 /clan withdraw \\[amount\\] — Withdraw (leader only)\n"
                "⚔️ /clan war — War vs enemy clan (reply)\n"
                "📋 /clan list — All clans\n\n"
                "💡 _Max 10 members • Leader can withdraw_\n"
                "⚔️ _War power = members×10 + wins×3 + luck!_"
            ),
        },
        "shops": {
            "title": "🛒 Shops",
            "text": (
                "🛒 *Shops*\n\n"
                "👕 /shop — Clothing & accessories\n"
                "🛍 /buy \\[item\\] — Buy an item\n"
                "🐾 /petshop — Pet shop\n"
                "🐶 /buypet \\[pet\\] — Buy a pet\n"
                "🍽 /foodshop — Food shop\n"
                "🍔 /buyfood \\[food\\] — Buy food\n"
                "😋 /eat \\[food\\] — Eat food\n"
                "🥤 /drink \\[drink\\] — Drink\n"
                "⚔️ /abilities — Ability shop\n"
                "⚡ /buyability \\[ability\\] — Buy ability\n"
                "🎒 /inventory — Your inventory\n"
                "🎁 /gift \\[item\\] — Gift item (reply)\n\n"
                "🛡️ *Protection:*\n"
                "🛡️ /buy shield — Shield (300$) — Block robbers\n"
                "💣 /buy landmine — Landmine (500$) — Explode robbers!\n\n"
                "🥊 *Abilities:*\n"
                "/punch /hug /kiss /kill /slap\n"
                "/tickle /poke /bite /pat /highfive /revive\n\n"
                "💡 _Prices increase with demand!_"
            ),
        },
        "bank": {
            "title": "🏦 Bank & Casino",
            "text": (
                "🏦 *Bank & Casino*\n\n"
                "🏦 /bank \\[deposit/withdraw\\] \\[amount\\] — Banking\n"
                "💸 /loan \\[take/pay\\] \\[amount\\] — Loans\n"
                "🏢 /bankmanager — View manager\n"
                "🤫 /embezzle — Embezzle (manager only)\n"
                "🔍 /investigate — Investigate manager\n"
                "💣 /bankrob — Rob bank (4+ people)\n"
                "⚖️ /bail — Bail out (reply)\n"
                "🔓 /jailbreak — Break out (3+ reply)\n\n"
                "🎰 *Casino:*\n"
                "🎰 /casino — Casino menu\n"
                "🎰 /megaslots \\[amount\\] — 5-reel mega slots\n"
                "🃏 /blackjack \\[amount\\] — Blackjack\n"
                "🪙 /coinflip \\[amount\\] — Coin flip\n"
                "🍺 /bar — Bar & drinks\n"
                "👑 /casinoleader — Casino leader\n"
                "💰 /paytax — Pay daily tax\n"
                "🎮 /casinogame — HTML5 online game\n"
            ),
        },
        "ai": {
            "title": "🧠 AI",
            "text": (
                "🧠 *Artificial Intelligence*\n\n"
                "🧠 /ai \\[question\\] — LangChain AI Agent\n"
                "🦋 /ai3 \\[text\\] — OPHELIA (emotion AI)\n"
                "📊 /ai3stats — OPHELIA brain stats\n\n"
                "💡 _OPHELIA learns from group conversations_\n"
                "_and responds based on emotions!_"
            ),
        },
        "tools": {
            "title": "🔧 Tools",
            "text": (
                "🔧 *Tools & Misc*\n\n"
                "🎨 /imagine \\[desc\\] — Generate image\n"
                "🎵 /music \\[name\\] — Search music\n"
                "📚 /book — Suggest a book\n"
                "🎌 /anime — Suggest an anime\n"
                "🎬 /movie — Suggest a movie\n"
                "🎮 /game — Suggest a game\n"
                "📰 /news — Latest news\n"
                "👨‍👩‍👧‍👦 /family — Family tree\n"
                "📅 /calendar — Ancient calendar\n"
                "🗺 /places — Browse locations\n"
                "💑 /date \\[place\\] — Go on a date (reply)\n"
                "🐾 /giftpet — Gift a pet (reply)\n"
                "🍽 /giftfood — Gift food (reply)\n"
                "⚠️ warn — Warn user (reply, admin)\n"
                "🌐 /lang — Change language\n"
            ),
        },
    },
}

_HELP_CAT_ORDER = ["fun", "gacha", "economy", "clan", "shops", "bank", "ai", "tools"]


def _help_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    cats = _HELP_CATEGORIES[lang]
    buttons = []
    for key in _HELP_CAT_ORDER:
        cat = cats[key]
        buttons.append([InlineKeyboardButton(cat["title"], callback_data=f"help:{key}")])
    return InlineKeyboardMarkup(buttons)


def _help_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    label = "🔙 برگشت" if lang == "fa" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="help:back")]])


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    await update.message.reply_text(s["bot_start"], parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    if lang == "fa":
        text = (
            "📋 *راهنمای kntu\\_bot25*\n\n"
            "🏛️ اقتصاد • گاچا • کلن • کازینو • هوش مصنوعی\n"
            "۸۰+ دستور — یه دسته‌بندی انتخاب کن 👇"
        )
    else:
        text = (
            "📋 *kntu\\_bot25 Help*\n\n"
            "🏛️ Economy • Gacha • Clans • Casino • AI\n"
            "80+ commands — Pick a category 👇"
        )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=_help_main_keyboard(lang),
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help category button clicks."""
    query = update.callback_query
    data = query.data  # "help:fun", "help:back", etc.
    _, key = data.split(":", 1)
    chat_id = query.message.chat.id
    lang = get_lang(chat_id)

    if key == "back":
        if lang == "fa":
            text = (
                "📋 *راهنمای kntu\\_bot25*\n\n"
                "🏛️ اقتصاد • گاچا • کلن • کازینو • هوش مصنوعی\n"
                "۸۰+ دستور — یه دسته‌بندی انتخاب کن 👇"
            )
        else:
            text = (
                "📋 *kntu\\_bot25 Help*\n\n"
                "🏛️ Economy • Gacha • Clans • Casino • AI\n"
                "80+ commands — Pick a category 👇"
            )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=_help_main_keyboard(lang),
        )
    else:
        cats = _HELP_CATEGORIES.get(lang, _HELP_CATEGORIES["en"])
        cat = cats.get(key)
        if cat:
            await query.edit_message_text(
                cat["text"], parse_mode="Markdown",
                reply_markup=_help_back_keyboard(lang),
            )
    await query.answer()


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    current = get_lang(chat.id)
    new_lang = "en" if current == "fa" else "fa"
    set_lang(chat.id, new_lang)
    s = STRINGS[new_lang]
    label = "English 🇬🇧" if new_lang == "en" else "فارسی 🇮🇷"
    await update.message.reply_text(
        s["lang_changed"].format(lang=label), parse_mode="Markdown"
    )


async def debug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text(s["debug_not_admin"], parse_mode="Markdown")
        return

    current = get_debug()
    set_debug(not current)
    msg = s["debug_on"] if not current else s["debug_off"]
    await update.message.reply_text(msg, parse_mode="Markdown")


async def dumpdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: send current data.json as a file via Telegram."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    data = load_data()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    bio = __import__("io").BytesIO(text.encode("utf-8"))
    bio.name = "data.json"
    await update.message.reply_document(document=bio, caption="📦 Live data.json backup")


async def dbstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: show database backend status."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    import os
    db_url = os.environ.get("DATABASE_URL", "")
    data = load_data()
    keys_count = len(data)
    wallets = len(data.get("wallets", {}).get(str(update.effective_chat.id), {}))
    inv_count = sum(
        len(items) for items in data.get("inventory", {}).get(str(update.effective_chat.id), {}).values()
    )

    if _use_pg:
        backend = "✅ PostgreSQL (persistent)"
    elif db_url:
        backend = "⚠️ DATABASE_URL set but PG connection failed — using JSON"
    else:
        backend = "❌ JSON file (NOT persistent — data resets on deploy!)"

    text = (
        f"🗄 *Database Status*\n\n"
        f"Backend: {backend}\n"
        f"Data keys: `{keys_count}`\n"
        f"Wallets in this chat: `{wallets}`\n"
        f"Inventory items: `{inv_count}`\n"
        f"DATABASE\\_URL: {'`set`' if db_url else '`NOT SET`'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def syncdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: force sync current data to PostgreSQL (or save to file)."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    data = load_data()
    save_data(data)
    backend = "PostgreSQL" if _use_pg else "JSON file"
    await update.message.reply_text(f"✅ Data synced to {backend}! ({len(data)} keys)")


async def loaddata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: upload a data.json file and overwrite the database with it."""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    reply = update.message.reply_to_message
    doc = None
    if reply and reply.document:
        doc = reply.document
    elif update.message.document:
        doc = update.message.document

    if not doc:
        await update.message.reply_text(
            "📥 Send or reply to a `.json` file, then use /loaddata",
            parse_mode="Markdown",
        )
        return

    try:
        file = await context.bot.get_file(doc.file_id)
        bio = __import__("io").BytesIO()
        await file.download_to_memory(bio)
        bio.seek(0)
        new_data = json.loads(bio.read().decode("utf-8"))
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to parse file: {e}")
        return

    save_data(new_data)
    backend = "PostgreSQL" if _use_pg else "JSON file"
    wallets = len(new_data.get("wallets", {}).get(str(update.effective_chat.id), {}))
    await update.message.reply_text(
        f"✅ Data loaded into {backend}!\n"
        f"Keys: `{len(new_data)}` | Wallets: `{wallets}`",
        parse_mode="Markdown",
    )
