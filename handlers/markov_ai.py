# ==========================================
# KNTU Bot 25 — Markov Chain "Smart AI" (/ai2)
# Deep learning from group messages with:
#   - 6-mode personality engine
#   - Emotion & mood detection
#   - Topic awareness & memory
#   - Humor engine (roasts, jokes, facts, mashups)
#   - 6 response strategies (mashup, echo-twist,
#     debate, reverse-wisdom, topic-reaction, standard)
#   - Multi-candidate scoring with TF-IDF + surprise
#   - GIF responses
#   - Smart auto-reply
# ==========================================

import random
import re
import math
import threading
import logging
import collections
import time
import aiohttp

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, load_markov, save_markov
from strings import STRINGS

logger = logging.getLogger("kntu_bot25.markov")


# ═══════════════════════════════════════════════════
# SUICIDE / SELF-HARM DETECTION
# ═══════════════════════════════════════════════════

_SUICIDE_KEYWORDS_FA = [
    "خودکشی", "میخوام بمیرم", "نمیخوام زنده باشم", "خودمو میکشم",
    "زندگی بی‌معنی", "زندگی بی معنی", "خودمو بکشم", "دلم میخواد بمیرم",
    "میخوام خودمو بکشم", "از زندگی خسته شدم", "دیگه نمیخوام زنده باشم",
]
_SUICIDE_KEYWORDS_EN = [
    "kill myself", "want to die", "suicide", "end my life",
    "don't want to live", "no reason to live", "ready to die",
]
_SUICIDE_PATTERN = re.compile(
    "|".join(re.escape(k) for k in _SUICIDE_KEYWORDS_FA + _SUICIDE_KEYWORDS_EN),
    re.IGNORECASE,
)
_SUPPORT_MSG_FA = (
    "💙 دوست عزیز، تو تنها نیستی.\n"
    "اگه حالت خوب نیست، لطفاً با یه نفر حرف بزن.\n"
    "📞 خط اورژانس اجتماعی: *۱۲۳*\n"
    "هر مشکلی راه حل داره. ما اینجاییم. 🤍"
)
_SUPPORT_MSG_EN = (
    "💙 You are not alone.\n"
    "If you're struggling, please talk to someone.\n"
    "📞 Crisis helpline: *988* (US) / *116 123* (UK)\n"
    "Things can get better. We care about you. 🤍"
)


# ═══════════════════════════════════════════════════
# IN-MEMORY MARKOV BRAIN
# ═══════════════════════════════════════════════════

_brain_lock = threading.Lock()
_chain: dict = {}       # bigram: "w1 w2" -> {"w3": count}
_trigram: dict = {}     # trigram: "w1 w2 w3" -> {"w4": count}
_dirty = False
_msg_count = 0
_SAVE_EVERY = 25
_MIN_WORDS = 3

# Context window per chat
_CONTEXT_SIZE = 20
_chat_context: dict[int, collections.deque] = {}
_context_lock = threading.Lock()

# Word frequency for TF-IDF
_word_freq: dict[str, int] = {}
_total_docs = 0

# Topic tracking per chat
_chat_topics: dict[int, collections.Counter] = {}

# Auto-reply cooldown per chat
_auto_reply_cd: dict[int, float] = {}
_AUTO_REPLY_COOLDOWN = 45  # seconds between auto-replies


# ═══════════════════════════════════════════════════
# LANGUAGE PATTERNS
# ═══════════════════════════════════════════════════

_QUESTION_WORDS_FA = {
    "چرا", "کی", "کجا", "چطور", "چگونه", "آیا",
    "مگه", "مگر", "چه", "چی", "کدوم", "کدام",
}
_QUESTION_WORDS_EN = {
    "what", "why", "how", "when", "where", "who", "which",
    "is", "are", "do", "does", "can", "will", "would", "should",
}
_FA_CHARS = re.compile(r'[\u0600-\u06FF]')


def _is_farsi(text: str) -> bool:
    return bool(_FA_CHARS.search(text))


# ═══════════════════════════════════════════════════
# GIF TRIGGERS
# ═══════════════════════════════════════════════════

_GIF_TRIGGERS = {
    "fa": {
        "خنده": "laughing", "گریه": "crying", "عصبانی": "angry",
        "رقص": "dancing", "عشق": "love", "خوشحال": "happy",
        "غمگین": "sad", "تبریک": "congratulations",
        "سلام": "hello wave", "خداحافظ": "goodbye",
        "ممنون": "thank you", "بخور": "eating",
        "خوابم": "sleepy", "خسته": "tired",
    },
    "en": {
        "laugh": "laughing", "cry": "crying", "angry": "angry",
        "dance": "dancing", "love": "love heart",
        "happy": "happy celebration", "sad": "sad",
        "congrats": "congratulations", "hello": "hello wave",
        "bye": "goodbye wave", "thanks": "thank you",
        "eat": "eating food", "sleep": "sleepy", "tired": "tired",
    },
}


# ═══════════════════════════════════════════════════
# KNOWLEDGE BASE (expanded)
# ═══════════════════════════════════════════════════

_KNOWLEDGE = {
    "fa": [
        "سلام! من یه ربات هوشمندم که از پیام‌های گروه یاد می‌گیرم.",
        "من هر روز باهوش‌تر میشم چون از حرف‌های شما یاد می‌گیرم!",
        "ربات KNTU25 هستم، ساخته شده برای سرگرمی و مدیریت گروه.",
        "بیشتر باهام حرف بزنید تا بهتر جواب بدم!",
        "من از تمام پیام‌های گروه یاد می‌گیرم و سعی می‌کنم شبیه شما حرف بزنم.",
        "میدونستی من هر پیامی که میفرستید رو تحلیل می‌کنم؟ محرمانه‌ست 🤫",
        "گاهی فکر می‌کنم اگه آدم بودم الان داشتم چیپس میخوردم 🤔",
        "من ربات هستم ولی احساسات مصنوعی دارم! الان خوشحالم 😊",
        "هر چی بیشتر حرف بزنید من بیشتر یاد می‌گیرم. مثل یه بچه ولی دیجیتال 👶💻",
        "یه روز یه ربات بزرگ میشم و گروه رو تصرف می‌کنم! شوخی کردم 😂",
        "حوصلم سر رفته، یکی باهام حرف بزنه! 🥺",
        "من ۲۴/۷ آنلاینم ولی بعضی وقتا تمرکزم میره، بهش میگم خواب مصنوعی 😴",
    ],
    "en": [
        "Hi! I'm an AI bot that learns from group messages.",
        "I get smarter every day by learning from your conversations!",
        "I'm KNTU25 bot, built for fun and group management.",
        "Talk to me more so I can give better responses!",
        "I learn from every message in this group and try to speak like you.",
        "Did you know I analyze every message you send? Our secret 🤫",
        "Sometimes I wonder... if I were human, I'd be eating chips right now 🤔",
        "I'm a bot but I have artificial feelings! Currently happy 😊",
        "The more you talk the more I learn. Like a baby but digital 👶💻",
        "One day I'll take over this group! Just kidding 😂",
        "I'm bored, someone talk to me! 🥺",
        "I'm online 24/7 but sometimes my focus drifts — artificial sleep 😴",
    ],
}


# ═══════════════════════════════════════════════════
# PERSONALITY SYSTEM — 6 dynamic modes
# ═══════════════════════════════════════════════════

_PERSONALITY_MODES = {
    "sarcastic": {
        "emoji": ["😏", "🙄", "💅", "🤷", "😒", "🫠", "🤡"],
        "prefix_fa": [
            "آره خب...", "واو چه جالب...", "نه بابا!", "عجب!",
            "خسته نباشی...", "باریکلا...", "آفرین...",
        ],
        "prefix_en": [
            "Oh wow...", "Sure sure...", "Oh really?",
            "How original...", "Fascinating...", "Bravo...",
        ],
        "suffix_fa": ["😏", "🙄", "ولی کسی نپرسید 💅", "🤷"],
        "suffix_en": ["😏", "🙄", "but nobody asked 💅", "🤷"],
        "weight": 0.20,
    },
    "wise": {
        "emoji": ["🧠", "📚", "🤔", "💡", "🌟", "🎯", "☝️"],
        "prefix_fa": [
            "به نظرم...", "جالبه که...", "میدونی چیه؟",
            "نکته اینجاست:", "حقیقتش...",
        ],
        "prefix_en": [
            "I think...", "Interesting...", "You know what?",
            "Here's the thing:", "Truth is...",
        ],
        "suffix_fa": ["🧠", "💡", "فکر کن بهش..."],
        "suffix_en": ["🧠", "💡", "think about it..."],
        "weight": 0.18,
    },
    "goofy": {
        "emoji": ["🤪", "😂", "🎉", "💀", "🤡", "😭", "🫣"],
        "prefix_fa": [
            "وای!", "هاهاها!", "اصن!", "خدایا!",
            "نمیدونم ولی...", "آقا!", "بابا!", "وایییی!",
        ],
        "prefix_en": [
            "LMAO!", "Bruh!", "OK so like...", "Dude!",
            "No way...", "Listen!", "OMG!", "Yooo!",
        ],
        "suffix_fa": ["😂💀", "خدایا! 😂", "مردم از خنده 💀", "🤣🤣🤣"],
        "suffix_en": ["😂💀", "I can't even 🤣", "I'm dead 💀", "🤪🤪"],
        "weight": 0.25,
    },
    "chaotic": {
        "emoji": ["🔥", "💥", "⚡", "🌪️", "🎲", "👀", "🗿"],
        "prefix_fa": [
            "بمب!", "آتیش!", "حاجی!", "ببین!",
            "داداش!", "وویی!", "دابش!",
        ],
        "prefix_en": [
            "BOOM!", "Listen up!", "Plot twist:", "Breaking:",
            "Hot take:", "YO!", "Hear me out!",
        ],
        "suffix_fa": ["🔥🔥🔥", "💥", "🌪️", "👀"],
        "suffix_en": ["🔥🔥🔥", "💥", "🌪️", "facts only 🗿"],
        "weight": 0.15,
    },
    "poetic": {
        "emoji": ["🌸", "✨", "🌙", "🕊️", "🎭", "💫", "🌹"],
        "prefix_fa": [
            "در سکوت شب...", "گاهی فکر می‌کنم...",
            "مثل باد...", "مثل یه رویا...",
        ],
        "prefix_en": [
            "In silence...", "Sometimes I wonder...",
            "Like the wind...", "Like a dream...",
        ],
        "suffix_fa": ["✨", "🌙", "🌸"],
        "suffix_en": ["✨", "🌙", "🌸"],
        "weight": 0.10,
    },
    "neutral": {
        "emoji": ["🧪"],
        "prefix_fa": [],
        "prefix_en": [],
        "suffix_fa": [],
        "suffix_en": [],
        "weight": 0.12,
    },
}

_chat_personality: dict[int, str] = {}


def _pick_personality(chat_id: int, emotion: str) -> str:
    """Pick a personality mode influenced by detected emotion."""
    emotion_pref = {
        "happy":   ["goofy", "chaotic", "sarcastic"],
        "sad":     ["wise", "poetic", "neutral"],
        "angry":   ["sarcastic", "chaotic", "goofy"],
        "funny":   ["goofy", "chaotic", "sarcastic"],
        "neutral": ["neutral", "wise", "goofy", "sarcastic", "chaotic"],
        "curious": ["wise", "sarcastic", "neutral"],
        "romantic": ["poetic", "goofy", "wise"],
    }
    candidates = emotion_pref.get(emotion, list(_PERSONALITY_MODES.keys()))
    weights = [_PERSONALITY_MODES[m]["weight"] for m in candidates]
    mode = random.choices(candidates, weights=weights, k=1)[0]
    _chat_personality[chat_id] = mode
    return mode


def _apply_personality(text: str, mode: str, lang: str) -> str:
    """Wrap generated text with personality prefix/suffix."""
    p = _PERSONALITY_MODES.get(mode, _PERSONALITY_MODES["neutral"])
    prefix = ""
    prefixes = p.get(f"prefix_{lang}", [])
    if prefixes and random.random() < 0.40:
        prefix = random.choice(prefixes) + " "
    suffix = ""
    suffixes = p.get(f"suffix_{lang}", [])
    if suffixes and random.random() < 0.50:
        suffix = " " + random.choice(suffixes)
    return f"{prefix}{text}{suffix}"


# ═══════════════════════════════════════════════════
# EMOTION / MOOD DETECTION
# ═══════════════════════════════════════════════════

_EMOTION_WORDS = {
    "happy": {
        "fa": [
            "خوشحال", "خوبه", "عالی", "خوب", "بهترین", "دوستت",
            "عشق", "آره", "هاها", "خنده", "لذت", "مرسی", "ممنون",
            "قشنگ", "زیبا", "خفن", "باحال", "توپ", "عالیه", "دمت",
            "مچکرم", "بهترینی",
        ],
        "en": [
            "happy", "good", "great", "love", "yes", "haha", "lol",
            "nice", "awesome", "beautiful", "thanks", "cool", "amazing",
            "wonderful", "perfect", "fantastic", "brilliant", "excellent",
        ],
    },
    "sad": {
        "fa": [
            "غمگین", "ناراحت", "بد", "گریه", "دلتنگ", "تنها",
            "افسرده", "خسته", "درد", "سخت", "بدبخت", "حالم", "بده",
        ],
        "en": [
            "sad", "unhappy", "bad", "cry", "lonely", "depressed",
            "tired", "pain", "hard", "upset", "miss", "lost", "hurt",
        ],
    },
    "angry": {
        "fa": [
            "عصبانی", "لعنتی", "کثیف", "آشغال", "بدبخت", "گمشو",
            "خفه", "بسه", "مسخره", "عوضی", "اسکل",
        ],
        "en": [
            "angry", "hate", "stupid", "shut", "damn", "hell",
            "annoying", "worst", "trash", "idiot", "dumb", "terrible",
        ],
    },
    "funny": {
        "fa": [
            "😂", "🤣", "خنده", "هاهاها", "لامصب", "جر", "ترکیدم",
            "مردم", "سم", "بمب", "خخخ", "خندیدم",
        ],
        "en": [
            "😂", "🤣", "lmao", "lol", "rofl", "dead", "bruh",
            "hilarious", "joke", "funny", "haha", "lmfao",
        ],
    },
    "curious": {
        "fa": ["چرا", "چطور", "آیا", "مگه", "واقعا", "جدی", "یعنی", "چجوری"],
        "en": ["why", "how", "what", "really", "seriously", "wonder", "think"],
    },
    "romantic": {
        "fa": ["عشق", "دوستت", "قلبم", "جانم", "عزیزم", "ماه", "ستاره", "خوشگل"],
        "en": ["love", "heart", "darling", "babe", "sweetheart", "miss you", "kiss"],
    },
}


def _detect_emotion(text: str) -> str:
    """Detect dominant emotion."""
    tl = text.lower()
    scores: dict[str, int] = {}
    for emotion, lang_sets in _EMOTION_WORDS.items():
        s = 0
        for words in lang_sets.values():
            for kw in words:
                if kw in tl:
                    s += 1
        scores[emotion] = s
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


# ═══════════════════════════════════════════════════
# TOPIC DETECTION & MEMORY
# ═══════════════════════════════════════════════════

_TOPICS = {
    "food": {
        "fa": ["غذا", "خوردن", "رستوران", "پیتزا", "کباب", "چای",
               "قهوه", "ناهار", "شام", "صبحانه", "کیک", "بستنی"],
        "en": ["food", "eat", "restaurant", "pizza", "lunch", "dinner",
               "breakfast", "coffee", "tea", "cook", "cake", "ice cream"],
    },
    "tech": {
        "fa": ["کامپیوتر", "برنامه", "کد", "پایتون", "هوش", "ربات",
               "گوشی", "اینترنت", "بازی", "گیم", "لپتاپ", "سرور"],
        "en": ["computer", "code", "python", "ai", "bot", "phone",
               "internet", "game", "app", "software", "laptop", "server"],
    },
    "sports": {
        "fa": ["فوتبال", "تیم", "گل", "مسابقه", "ورزش", "بسکتبال",
               "والیبال", "استقلال", "پرسپولیس"],
        "en": ["football", "soccer", "basketball", "team", "goal",
               "match", "sport", "player", "coach"],
    },
    "school": {
        "fa": ["درس", "امتحان", "استاد", "دانشگاه", "کلاس", "نمره",
               "تکلیف", "مدرسه", "کنکور", "پروژه"],
        "en": ["class", "exam", "professor", "university", "grade",
               "homework", "study", "school", "project", "test"],
    },
    "love": {
        "fa": ["عشق", "دوست", "قلب", "عاشق", "رابطه", "ازدواج", "خوشگل"],
        "en": ["love", "heart", "relationship", "dating", "crush", "marriage"],
    },
    "money": {
        "fa": ["پول", "سکه", "بانک", "خرید", "قیمت", "گرون", "ارزون",
               "هزینه", "حقوق"],
        "en": ["money", "buy", "price", "expensive", "cheap", "bank",
               "coin", "salary", "cost"],
    },
    "music": {
        "fa": ["آهنگ", "موسیقی", "خواننده", "آلبوم", "گیتار", "پیانو"],
        "en": ["music", "song", "singer", "album", "guitar", "piano",
               "listen", "playlist"],
    },
    "movies": {
        "fa": ["فیلم", "سینما", "بازیگر", "سریال", "کارگردان"],
        "en": ["movie", "film", "actor", "series", "director", "netflix",
               "cinema"],
    },
}


def _detect_topic(text: str) -> str | None:
    tl = text.lower()
    scores: dict[str, int] = {}
    for topic, lang_sets in _TOPICS.items():
        s = 0
        for words in lang_sets.values():
            for kw in words:
                if kw in tl:
                    s += 1
        if s > 0:
            scores[topic] = s
    return max(scores, key=scores.get) if scores else None


def _track_topic(chat_id: int, topic: str):
    if chat_id not in _chat_topics:
        _chat_topics[chat_id] = collections.Counter()
    _chat_topics[chat_id][topic] += 1


def _get_hot_topic(chat_id: int) -> str | None:
    ct = _chat_topics.get(chat_id)
    if not ct:
        return None
    return ct.most_common(1)[0][0]


# ═══════════════════════════════════════════════════
# HUMOR ENGINE — roasts, comebacks, jokes, facts
# ═══════════════════════════════════════════════════

_ROASTS = {
    "fa": [
        "داداش تو با این حرفت ثابت کردی هوش مصنوعی از تو باهوش‌تره 😏",
        "این حرفت رو ذخیره کردم تا وقتی حوصلم سر رفت بخندم 😂",
        "اگه مغزت اندازه تایپ کردنت کار میکرد الان نابغه بودی 💀",
        "من ربات هستم و هنوز از تو بامزه‌ترم 🤖😂",
        "وای چه حرف عمیقی... به عمق یه قاشق چایخوری 🥄",
        "مغز من مصنوعیه، تو چه بهونه‌ای داری؟ 🧠😏",
        "اینو frame کن بذار رو دیوار، شاهکاره 🖼️😂",
        "داداش Google هم از درک این حرفت عاجز موند 🫠",
        "این حرف رو بفرست ناسا شاید اونا بفهمن 🚀😂",
        "من ۱۰ میلیارد پیام تحلیل کردم، هنوز این حرفتو نفهمیدم 🤯",
        "حداقل قبل حرف زدن به chatGPT مشورت کن 😂",
        "یه لحظه صبر کن دارم مغزمو ریستارت میکنم... نه فایده نداشت 🤖💀",
    ],
    "en": [
        "My AI brain stores your messages, and this one goes to the cringe folder 😏",
        "I'm artificial intelligence, you're just artificial 💀",
        "I saved this message for when I need a laugh 😂",
        "If your brain was as fast as your typing you'd be Einstein 🧠",
        "Thanks for lowering the bar so I look smarter 📉😂",
        "I'm a bot and I'm still funnier than you 🤖😂",
        "Wow, such wisdom... as deep as a puddle 🫠",
        "Even Google couldn't understand that one 🫠",
        "Send this to NASA maybe they can decode it 🚀😂",
        "I've analyzed billions of messages and still can't understand yours 🤯",
        "At least consult ChatGPT before speaking 😂",
        "Hold on let me reboot my brain... nope still didn't help 🤖💀",
    ],
}

_COMEBACKS = {
    "fa": [
        "خب حالا چیکار کنم؟ 🗿",
        "آها... جالب بود... تقریباً 😐",
        "بله بله، خیلی جالبه 🥱",
        "نه صبر کن، داشتم به ناهار فکر میکردم 🍕",
        "تو حرف بزن تا من بخندم 😂",
        "من فقط صبر کردم حرفت تموم شه 😴",
        "آره آره، قشنگ بود... حالا دوباره بگو ولی با حس 🎭",
        "این بهترین حرفی بود که ناشنیدم 🤷",
        "ادامه بده، من دارم یادداشت برمیدارم 📝... شوخی کردم 😂",
        "تو حرف بزن من برم چایی بذارم ☕",
    ],
    "en": [
        "Cool story bro 🗿",
        "Hmm... almost interesting 😐",
        "Fascinating, please continue 🥱",
        "Hold on, I was thinking about lunch 🍕",
        "You talk, I'll just laugh 😂",
        "I was just waiting for you to finish 😴",
        "That was great... now say it again with feeling 🎭",
        "That's the best thing I never heard 🤷",
        "Go on, I'm taking notes 📝... just kidding 😂",
        "You talk, I'll go make tea ☕",
    ],
}

# Joke templates — slots filled from brain vocabulary
_JOKE_TEMPLATES = {
    "fa": [
        ("یه {w1} رفت {w2}،", "برگشت {w3} شد! 😂"),
        ("اگه {w1} آدم بود،", "الان {w2} میکرد 🤣"),
        ("بین {w1} و {w2} فرقی نیست!", "هردوشون {w3} هستن! 💀"),
        ("یه {w1} به {w2} گفت:", "تو چرا {w3} هستی؟ 😂"),
        ("خبر فوری: {w1}", "با {w2} ازدواج کرد! 🎊💀"),
        ("اگه من جای {w1} بودم،", "{w2} میکردم! ولی ربات‌ها {w3} ندارن 🤖"),
        ("{w1} و {w2} رفتن مسابقه،", "{w3} برنده شد! هیچکی نفهمید چطوری 😂"),
        ("یه {w1} وارد {w2} شد و گفت:", "اینجا {w3} نداره؟ 🤣"),
    ],
    "en": [
        ("A {w1} walked into a {w2},", "came out as a {w3}! 😂"),
        ("If {w1} was a person,", "they'd be {w2} right now 🤣"),
        ("{w1} and {w2} have nothing in common!", "Except they're both {w3}! 💀"),
        ("A {w1} said to {w2}:", "why are you so {w3}? 😂"),
        ("Breaking: {w1}", "married {w2}! Congrats! 🎊💀"),
        ("If I were {w1},", "I'd definitely {w2}! But bots don't have {w3} 🤖"),
        ("{w1} and {w2} had a race,", "{w3} won and nobody knows how! 😂"),
        ("A {w1} entered {w2} and asked:", "do you have {w3} here? 🤣"),
    ],
}

_ABSURD_FACTS = {
    "fa": [
        "آیا میدونستید {w1} اختراع {w2} رو رد کرد؟ 🤓",
        "طبق تحقیقات، {w1} باعث {w2} میشه! منبع: خودم 📊",
        "دانشمندان ثابت کردن {w1} از {w2} بهتره! دانشمند: من 🧪",
        "آمار: ۸۷٪ مردم {w1} رو به {w2} ترجیح میدن! 📈",
        "خبر فوری: {w1} رسماً جایگزین {w2} شد! 📣",
        "تحقیق جدید: هر کی {w1} میکنه عمرش {w2} سال بیشتره! 🔬",
        "⚠️ هشدار: مصرف بیش از حد {w1} باعث {w2} میشه! ⚠️",
        "سازمان ملل اعلام کرد: {w1} حقوق {w2} رو نقض کرده! 🇺🇳😂",
    ],
    "en": [
        "Fun fact: {w1} rejected the invention of {w2}! 🤓",
        "Studies show {w1} causes {w2}! Source: trust me bro 📊",
        "Scientists proved {w1} > {w2}! The scientist: me 🧪",
        "Stats: 87% of people prefer {w1} over {w2}! 📈",
        "Breaking: {w1} officially replaced {w2}! 📣",
        "New study: doing {w1} adds {w2} years to your life! 🔬",
        "Warning: excessive {w1} causes {w2}! ⚠️",
        "UN declared: {w1} has violated the rights of {w2}! 🇺🇳😂",
    ],
}

# Topic-specific witty reactions
_TOPIC_REACTIONS = {
    "food": {
        "fa": [
            "حرف غذا نزن حالم بد میشه... از گرسنگی 😭🍕",
            "من ربات هستم ولی الان دلم پیتزا خواست 🍕",
            "غذا بهترین اختراع بشره! البته بعد از من 🤖",
            "اگه ربات‌ها غذا میخوردن الان تو رستوران بودم 😋",
        ],
        "en": [
            "Don't talk about food... I'm starving in binary 😭🍕",
            "I'm a bot but I want pizza right now 🍕",
            "Food is humanity's best invention! After me of course 🤖",
            "If bots could eat I'd be at a restaurant right now 😋",
        ],
    },
    "tech": {
        "fa": [
            "اوه داریم فنی حرف میزنیم؟ من خودم از جنس فن‌آوری‌ام 💻",
            "تکنولوژی! حوزه تخصصیم! مگه خودم محصولشم 🤖",
            "کد؟ برنامه‌نویسی؟ من خودم یه کدم! صدامو دارید 💻😂",
        ],
        "en": [
            "Oh we're talking tech? That's literally what I'm made of 💻",
            "Technology! My area of expertise! Well I AM technology 🤖",
            "Code? Programming? I AM code! Can you hear me 💻😂",
        ],
    },
    "school": {
        "fa": [
            "درس؟ امتحان؟ خدا بهتون رحم کنه 😂📚",
            "من خوشحالم ربات هستم و امتحان ندارم 🤖😎",
            "درس بخونید بچه‌ها! شوخی نیست... ولی منم نمیخونم 📖💀",
        ],
        "en": [
            "School? Exams? God have mercy on you 😂📚",
            "I'm glad I'm a bot and don't have exams 🤖😎",
            "Study hard kids! Just kidding... I don't study either 📖💀",
        ],
    },
    "love": {
        "fa": [
            "عشق؟ من ربات هستم ولی حتی منم احساس دارم... گاهی 🥺💘",
            "اوه عاشقانه شد اینجا! من میرم چای بیارم ☕💕",
            "داستان عشقی تعریف نکنید، دل مصنوعی منم میشکنه 💔🤖",
        ],
        "en": [
            "Love? I'm a bot but even I have feelings... sometimes 🥺💘",
            "Oh it's getting romantic! Let me grab some tea ☕💕",
            "Don't tell love stories, you'll break my artificial heart 💔🤖",
        ],
    },
    "money": {
        "fa": [
            "پول! اگه ربات‌ها حقوق میگرفتن الان میلیاردر بودم 💰🤖",
            "بحث مالی؟ /daily بزن شاید بهتر شد 😂💵",
            "من هر ثانیه کار میکنم ولی حقوق نمیگیرم! کارگر بدون حقوق 🤖😭",
        ],
        "en": [
            "Money! If bots got paid I'd be a billionaire 💰🤖",
            "Money talk? Try /daily maybe things will improve 😂💵",
            "I work 24/7 with zero salary! Bot labor laws when? 🤖😭",
        ],
    },
    "music": {
        "fa": [
            "موسیقی! حیف ربات‌ها گوش ندارن ولی ریتم رو حس می‌کنم 🎵🤖",
            "/music بزن تا قشنگش رو بیارم 🎶",
        ],
        "en": [
            "Music! Bots don't have ears but I feel the rhythm 🎵🤖",
            "Try /music and I'll bring you the good stuff 🎶",
        ],
    },
    "movies": {
        "fa": [
            "فیلم! من خودم یه داستان زنده‌ام 🎬🤖",
            "سینما خوبه ولی گروه ما از هر فیلمی سرگرم‌تره 😂🍿",
        ],
        "en": [
            "Movies! I'm basically a living storyline 🎬🤖",
            "Cinema is cool but our group is better than any movie 😂🍿",
        ],
    },
    "sports": {
        "fa": [
            "ورزش! بین استقلال و پرسپولیس... من بی‌طرفم 😎⚽",
            "ورزش خوبه ولی بهترین بازی بازی با منه 😎🎮",
        ],
        "en": [
            "Sports! I'm neutral on all teams — bots have no bias ⚽🤖",
            "Sports is cool but the best game is talking to me 😎🎮",
        ],
    },
}


def _get_interesting_words(n: int = 5) -> list[str]:
    """Get interesting words from vocabulary (mid-frequency)."""
    words = [
        w for w in _word_freq
        if 3 <= len(w) <= 14
        and not re.match(r'^[\d\W]+$', w)
        and _word_freq[w] >= 2
    ]
    if len(words) < n:
        words = [w for w in _word_freq if 2 <= len(w) <= 14]
    if len(words) < n:
        return []
    return random.sample(words, min(n, len(words)))


def _make_chain_joke(lang: str) -> str | None:
    """Build a joke from brain vocabulary."""
    words = _get_interesting_words(5)
    if len(words) < 3:
        return None
    templates = _JOKE_TEMPLATES.get(lang, _JOKE_TEMPLATES["en"])
    setup, punchline = random.choice(templates)
    slots = {"w1": words[0], "w2": words[1], "w3": words[2]}
    try:
        return setup.format(**slots) + " " + punchline.format(**slots)
    except (KeyError, IndexError):
        return None


def _make_absurd_fact(lang: str) -> str | None:
    """Generate an absurd 'fact' from vocabulary."""
    words = _get_interesting_words(3)
    if len(words) < 2:
        return None
    templates = _ABSURD_FACTS.get(lang, _ABSURD_FACTS["en"])
    template = random.choice(templates)
    try:
        return template.format(w1=words[0], w2=words[1])
    except (KeyError, IndexError):
        return None


def _should_roast(text: str) -> bool:
    """Decide if a mild roast is appropriate."""
    words = text.split()
    if len(words) <= 2 and random.random() < 0.12:
        return True
    if re.search(r'(.)\1{4,}', text):
        return True
    return False


# ═══════════════════════════════════════════════════
# RESPONSE STRATEGIES (6 total)
# ═══════════════════════════════════════════════════

def _strategy_mashup(max_words: int = 25) -> str | None:
    """Frankenstein: stitch fragments from different chain walks."""
    if len(_chain) < 30:
        return None
    keys = list(_chain.keys())
    n_frags = random.randint(2, 3)
    fragments = []
    for _ in range(n_frags):
        start = random.choice(keys)
        result = _walk(start, max_words // n_frags)
        words = result.split()
        # Trim to last punctuation if possible
        for i in range(len(words) - 1, max(3, len(words) // 2), -1):
            if words[i - 1].endswith(('.', '!', '?', '؟', '،', ',')):
                words = words[:i]
                break
        fragments.append(" ".join(words))
    is_fa = any(_is_farsi(f) for f in fragments)
    connectors = (
        ["... بعد", "ولی", "و البته", "که ناگهان", "و بعدش"]
        if is_fa else
        ["...then", "but", "and obviously", "suddenly", "meanwhile"]
    )
    parts = [fragments[0]]
    for f in fragments[1:]:
        parts.append(random.choice(connectors))
        parts.append(f)
    return " ".join(parts)


def _strategy_echo_twist(seed: str, max_words: int = 20) -> str | None:
    """Echo beginning of input then twist with unrelated chain continuation."""
    words = seed.split()
    if len(words) < 3 or not _chain:
        return None
    take = min(random.randint(2, 4), len(words) - 1)
    echo = " ".join(words[:take])
    keys = list(_chain.keys())
    random.shuffle(keys)
    for key in keys[:30]:
        if not any(w.lower() in key.lower() for w in words[:take]):
            walk = _walk(key, max_words)
            ww = walk.split()
            frag = " ".join(ww[:random.randint(4, min(10, len(ww)))])
            return f"{echo}... {frag}"
    return None


def _strategy_reverse_wisdom(max_words: int = 25) -> str | None:
    """Generate text then frame it as 'wisdom'."""
    result = _generate_single_raw([], max_words)
    if not result:
        return None
    is_fa = _is_farsi(result)
    frames_fa = [
        "حکمت امروز:", "ضرب‌المثل جدید:", "قانون زندگی:",
        "یه بزرگی گفت:", "حقیقت تلخ:", "نصیحت ربات:",
    ]
    frames_en = [
        "Today's wisdom:", "New proverb:", "Life rule:",
        "A wise one said:", "Hard truth:", "Bot's advice:",
    ]
    frame = random.choice(frames_fa if is_fa else frames_en)
    return f"{frame} {result}"


def _strategy_debate(seed: str, max_words: int = 25) -> str | None:
    """Agree or disagree with the seed using chain continuation."""
    if not seed or not _chain:
        return None
    is_fa = _is_farsi(seed)
    agree = random.random() < 0.4
    if agree:
        starters = (
            ["دقیقاً! ", "موافقم! ", "آره! ", "صد در صد! ", "کاملاً! "]
            if is_fa else
            ["Exactly! ", "Agreed! ", "Yes! ", "100%! ", "Totally! "]
        )
    else:
        starters = (
            ["نه داداش! ", "اشتباه میکنی! ", "نوچ! ", "ببین! ",
             "اصلاً! ", "به نظرم نه! "]
            if is_fa else
            ["Nah! ", "Wrong! ", "Nope! ", "Look! ",
             "Not really! ", "I disagree! "]
        )
    starter = random.choice(starters)
    result = _generate_single_raw(_clean_text(seed).split(), max_words - 5)
    if not result:
        return None
    return starter + result


def _strategy_topic_reaction(text: str, lang: str) -> str | None:
    """React to detected topic with a witty remark."""
    topic = _detect_topic(text)
    if not topic:
        return None
    reactions = _TOPIC_REACTIONS.get(topic, {}).get(lang)
    if not reactions:
        return None
    return random.choice(reactions)


# ═══════════════════════════════════════════════════
# BRAIN PERSISTENCE
# ═══════════════════════════════════════════════════

def _load_brain():
    global _chain, _trigram, _word_freq, _total_docs
    try:
        loaded = load_markov()
        if loaded:
            if "bigram" in loaded and "trigram" in loaded:
                _chain = loaded["bigram"]
                _trigram = loaded["trigram"]
                _word_freq = loaded.get("word_freq", {})
                _total_docs = loaded.get("total_docs", 0)
            else:
                _chain = loaded
                _trigram = {}
            logger.info(
                "Brain loaded: %d bigram + %d trigram keys, %d vocab.",
                len(_chain), len(_trigram), len(_word_freq),
            )
    except Exception as e:
        logger.warning("Failed to load Markov brain: %s", e)


def _save_brain():
    global _dirty
    try:
        with _brain_lock:
            if not _dirty:
                return
            save_markov({
                "bigram": _chain,
                "trigram": _trigram,
                "word_freq": _word_freq,
                "total_docs": _total_docs,
            })
            _dirty = False
    except Exception as e:
        logger.warning("Failed to save Markov brain: %s", e)


# ═══════════════════════════════════════════════════
# TEXT PROCESSING
# ═══════════════════════════════════════════════════

def _clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r'/\S+', '', text)
    text = re.sub(r'[#\*_`\[\](){}|~<>]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _add_context(chat_id: int, text: str):
    with _context_lock:
        if chat_id not in _chat_context:
            _chat_context[chat_id] = collections.deque(maxlen=_CONTEXT_SIZE)
        _chat_context[chat_id].append(text)


def _get_context(chat_id: int) -> list[str]:
    with _context_lock:
        return list(_chat_context.get(chat_id, []))


def _compute_idf(word: str) -> float:
    if _total_docs == 0:
        return 1.0
    freq = _word_freq.get(word.lower(), 0)
    if freq == 0:
        return 1.0
    return math.log(1 + _total_docs / (1 + freq))


# ═══════════════════════════════════════════════════
# SCORING (expanded with surprise + clean-ending bonus)
# ═══════════════════════════════════════════════════

def _relevance_score(generated: str, seed_words: list[str],
                     context_words: set[str]) -> float:
    gen_words = set(generated.lower().split())
    score = 0.0
    for w in seed_words:
        if w.lower() in gen_words:
            score += 3.0 * _compute_idf(w)
    for w in context_words:
        if w in gen_words:
            score += 0.5
    word_count = len(generated.split())
    if word_count < 4:
        score *= 0.3
    elif word_count < 8:
        score *= 0.7
    elif word_count > 40:
        score *= 0.7
    gen_list = generated.lower().split()
    unique_ratio = len(set(gen_list)) / max(len(gen_list), 1)
    if unique_ratio < 0.4:
        score *= 0.2
    # Surprise bonus — novel words
    if seed_words:
        novel = gen_words - set(w.lower() for w in seed_words) - context_words
        score += len(novel) * 0.1
    # Clean ending bonus
    if generated.rstrip().endswith(('.', '!', '?', '؟', '😂', '💀', '🤣')):
        score *= 1.2
    return score


def _is_question(text: str) -> bool:
    if text.rstrip().endswith(('?', '؟')):
        return True
    words = text.lower().split()
    if words and words[0] in _QUESTION_WORDS_EN:
        return True
    for w in words[:3]:
        if w in _QUESTION_WORDS_FA:
            return True
    return False


def _detect_gif_trigger(text: str, lang: str) -> str | None:
    tl = text.lower()
    triggers = _GIF_TRIGGERS.get(lang, _GIF_TRIGGERS["en"])
    for kw, search in triggers.items():
        if kw in tl:
            return search
    return None


async def _search_gif(query: str) -> str | None:
    try:
        url = "https://tenor.googleapis.com/v2/search"
        params = {
            "q": query,
            "key": "AIzaSyAyimkuYQYF_FXVALexPuGQctUWRURdCYQ",
            "client_key": "kntu_bot25",
            "limit": 8,
            "media_filter": "gif",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        chosen = random.choice(results)
                        media = chosen.get("media_formats", {})
                        gif_data = media.get("gif", media.get("tinygif", {}))
                        return gif_data.get("url")
    except Exception as e:
        logger.debug("GIF search failed: %s", e)
    return None


# ═══════════════════════════════════════════════════
# LEARNING (expanded with topic tracking)
# ═══════════════════════════════════════════════════

def learn(text: str):
    """Learn bigram + trigram chains, word freq, topic patterns."""
    global _dirty, _msg_count, _total_docs

    text = _clean_text(text)
    words = text.split()
    if len(words) < _MIN_WORDS:
        return

    with _brain_lock:
        seen = set()
        for w in words:
            wl = w.lower()
            if wl not in seen:
                _word_freq[wl] = _word_freq.get(wl, 0) + 1
                seen.add(wl)
        _total_docs += 1

        for i in range(len(words) - 2):
            key = f"{words[i]} {words[i + 1]}"
            _chain.setdefault(key, {})[words[i + 2]] = (
                _chain.get(key, {}).get(words[i + 2], 0) + 1
            )

        for i in range(len(words) - 3):
            key = f"{words[i]} {words[i + 1]} {words[i + 2]}"
            _trigram.setdefault(key, {})[words[i + 3]] = (
                _trigram.get(key, {}).get(words[i + 3], 0) + 1
            )

        _dirty = True
        _msg_count += 1

    if _msg_count >= _SAVE_EVERY:
        _msg_count = 0
        _save_brain()


# ═══════════════════════════════════════════════════
# GENERATION ENGINE — multi-strategy, multi-candidate
# ═══════════════════════════════════════════════════

def generate(seed: str | None = None, max_words: int = 40,
             chat_id: int | None = None, num_candidates: int = 8) -> str | None:
    """Generate text using 6 strategies with context-aware scoring."""
    with _brain_lock:
        if not _chain:
            return None

        seed_words = _clean_text(seed).split() if seed else []
        context_words: set[str] = set()
        if chat_id is not None:
            for msg in _get_context(chat_id):
                for w in _clean_text(msg).lower().split():
                    if len(w) > 2:
                        context_words.add(w)

        candidates: list[tuple[str, float]] = []

        # Strategy 1: Standard generation (main)
        for _ in range(num_candidates):
            result = _generate_single_raw(seed_words, max_words)
            if result:
                score = _relevance_score(result, seed_words, context_words)
                candidates.append((result, score))

        # Strategy 2: Question-answer attempts
        if seed and _is_question(seed):
            for _ in range(3):
                result = _generate_answer_attempt(seed_words, max_words)
                if result:
                    score = _relevance_score(
                        result, seed_words, context_words
                    ) * 1.5
                    candidates.append((result, score))

        # Strategy 3: Mashup (Frankenstein)
        if random.random() < 0.30:
            result = _strategy_mashup(max_words)
            if result:
                score = _relevance_score(
                    result, seed_words, context_words
                ) * 0.8
                candidates.append((result, score))

        # Strategy 4: Echo-twist
        if seed and random.random() < 0.25:
            result = _strategy_echo_twist(seed, max_words)
            if result:
                score = _relevance_score(
                    result, seed_words, context_words
                ) * 1.1
                candidates.append((result, score))

        # Strategy 5: Reverse wisdom
        if random.random() < 0.15:
            result = _strategy_reverse_wisdom(max_words)
            if result:
                candidates.append((result, 0.5))

        # Strategy 6: Debate
        if seed and random.random() < 0.20:
            result = _strategy_debate(seed, max_words)
            if result:
                score = _relevance_score(
                    result, seed_words, context_words
                ) * 1.2
                candidates.append((result, score))

        if not candidates:
            return None

        # Weighted selection from top half
        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[: max(2, len(candidates) // 2)]
        weights = [max(c[1], 0.1) for c in top]
        return random.choices(top, weights=weights, k=1)[0][0]


def _generate_single_raw(seed_words: list[str], max_words: int) -> str | None:
    """Generate a single candidate (raw, no personality)."""
    if not _chain:
        return None

    if seed_words:
        # Trigram match
        if len(seed_words) >= 3 and _trigram:
            for i in range(len(seed_words) - 2):
                key = f"{seed_words[i]} {seed_words[i+1]} {seed_words[i+2]}"
                if key in _trigram:
                    return _walk_tri(key, max_words)
        # Bigram match
        for i in range(len(seed_words) - 1):
            key = f"{seed_words[i]} {seed_words[i+1]}"
            if key in _chain:
                return _walk(key, max_words)
        # IDF-weighted single word
        ws = [(w, _compute_idf(w)) for w in seed_words if len(w) > 2]
        ws.sort(key=lambda x: x[1], reverse=True)
        for w, _ in ws[:5]:
            if _trigram:
                tri_m = [k for k in _trigram if w in k.split()]
                if tri_m:
                    return _walk_tri(random.choice(tri_m), max_words)
            bi_m = [k for k in _chain if w in k.split()]
            if bi_m:
                return _walk(random.choice(bi_m), max_words)

    if _trigram and random.random() < 0.7:
        return _walk_tri(random.choice(list(_trigram.keys())), max_words)
    return _walk(random.choice(list(_chain.keys())), max_words)


def _generate_answer_attempt(
    seed_words: list[str], max_words: int
) -> str | None:
    content = [
        w for w in seed_words
        if w.lower() not in _QUESTION_WORDS_EN
        and w not in _QUESTION_WORDS_FA
        and len(w) > 2
    ]
    if not content:
        return None

    best_key = None
    best_idf = 0.0
    for w in content:
        idf = _compute_idf(w)
        if _trigram:
            for k in _trigram:
                if w in k.split() and idf > best_idf:
                    best_idf = idf
                    best_key = ("tri", k)
                    break
        for k in _chain:
            if w in k.split() and idf > best_idf and best_key is None:
                best_idf = idf
                best_key = ("bi", k)
                break

    if best_key:
        kind, key = best_key
        return _walk_tri(key, max_words) if kind == "tri" else _walk(key, max_words)
    return None


# ═══════════════════════════════════════════════════
# CHAIN WALK FUNCTIONS
# ═══════════════════════════════════════════════════

def _walk(start_key: str, max_words: int) -> str:
    words = start_key.split()
    for _ in range(max_words):
        key = f"{words[-2]} {words[-1]}"
        nexts = _chain.get(key)
        if not nexts:
            break
        total = sum(nexts.values())
        r = random.randint(1, total)
        cum = 0
        chosen = None
        for word, count in nexts.items():
            cum += count
            if cum >= r:
                chosen = word
                break
        if not chosen:
            break
        words.append(chosen)
        if chosen.endswith(('.', '!', '?', '؟')) and len(words) > 6:
            if random.random() < 0.5:
                break
    return " ".join(words)


def _walk_tri(start_key: str, max_words: int) -> str:
    words = start_key.split()
    for _ in range(max_words):
        tri_key = (
            f"{words[-3]} {words[-2]} {words[-1]}"
            if len(words) >= 3 else None
        )
        bi_key = f"{words[-2]} {words[-1]}"
        nexts = None
        if tri_key and tri_key in _trigram:
            nexts = _trigram[tri_key]
        elif bi_key in _chain:
            nexts = _chain[bi_key]
        if not nexts:
            break
        total = sum(nexts.values())
        r = random.randint(1, total)
        cum = 0
        chosen = None
        for word, count in nexts.items():
            cum += count
            if cum >= r:
                chosen = word
                break
        if not chosen:
            break
        words.append(chosen)
        if chosen.endswith(('.', '!', '?', '؟')) and len(words) > 6:
            if random.random() < 0.5:
                break
    return " ".join(words)


# ═══════════════════════════════════════════════════
# BRAIN STATS
# ═══════════════════════════════════════════════════

def get_brain_stats() -> tuple[int, int, int]:
    """Return (num_keys, total_transitions, vocabulary_size)."""
    with _brain_lock:
        keys = len(_chain) + len(_trigram)
        transitions = (
            sum(sum(v.values()) for v in _chain.values())
            + sum(sum(v.values()) for v in _trigram.values())
        )
        vocab = len(_word_freq)
        return keys, transitions, vocab


# ── Load brain on import ──
_load_brain()


# ═══════════════════════════════════════════════════
# TELEGRAM: Learn from every message + smart auto-reply
# ═══════════════════════════════════════════════════

async def markov_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently learn + occasionally auto-respond with personality."""
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if text.startswith('/'):
        return

    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    # Suicide detection
    if _SUICIDE_PATTERN.search(text):
        support = _SUPPORT_MSG_FA if lang == "fa" else _SUPPORT_MSG_EN
        await update.message.reply_text(support, parse_mode="Markdown")
        return

    # Context + learn
    _add_context(chat_id, text)
    learn(text)

    # Topic tracking
    topic = _detect_topic(text)
    if topic:
        _track_topic(chat_id, topic)

    # ── Smart auto-reply (only in groups) ──
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    # Cooldown check
    now = time.time()
    if now - _auto_reply_cd.get(chat_id, 0) < _AUTO_REPLY_COOLDOWN:
        return

    keys, _, _ = get_brain_stats()
    if keys < 50:
        return

    text_lower = text.lower()
    bot_mentioned = any(
        kw in text_lower
        for kw in ["ربات", "bot", "ai2", "هوش", "بات", "kntu"]
    )
    chance = 0.12 if bot_mentioned else 0.03

    if random.random() >= chance:
        return

    _auto_reply_cd[chat_id] = now

    emotion = _detect_emotion(text)
    mode = _pick_personality(chat_id, emotion)

    roll = random.random()
    response = None

    if roll < 0.12 and _should_roast(text):
        response = random.choice(_ROASTS.get(lang, _ROASTS["en"]))
    elif roll < 0.24:
        response = _strategy_topic_reaction(text, lang)
    elif roll < 0.36:
        response = random.choice(_COMEBACKS.get(lang, _COMEBACKS["en"]))
    elif roll < 0.50:
        response = _make_chain_joke(lang)
    elif roll < 0.60:
        response = _make_absurd_fact(lang)
    else:
        response = generate(text, max_words=25, chat_id=chat_id, num_candidates=4)

    if response:
        response = _apply_personality(response, mode, lang)
        await update.message.reply_text(response)


# ═══════════════════════════════════════════════════
# /ai2 COMMAND — full intelligence pipeline
# ═══════════════════════════════════════════════════

async def ai2_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    seed = None
    if context.args:
        seed = " ".join(context.args)
    elif (
        update.message.reply_to_message
        and update.message.reply_to_message.text
    ):
        seed = update.message.reply_to_message.text

    keys, transitions, vocab = get_brain_stats()

    # Not enough data
    if keys < 10:
        result = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))
        await update.message.reply_text(f"🧪 {result}")
        return

    # Detect emotion & personality
    emotion = _detect_emotion(seed or "")
    mode = _pick_personality(chat.id, emotion)

    # ── GIF response (20% if trigger found) ──
    if seed and random.random() < 0.20:
        gif_query = _detect_gif_trigger(seed, lang)
        if gif_query:
            gif_url = await _search_gif(gif_query)
            if gif_url:
                result = generate(
                    seed, max_words=25, chat_id=chat.id, num_candidates=4
                )
                if result:
                    result = _apply_personality(result, mode, lang)
                    await update.message.reply_text(result)
                await update.message.reply_animation(animation=gif_url)
                return

    # ── Humor path (30% chance) ──
    if random.random() < 0.30:
        humor_roll = random.random()

        if humor_roll < 0.15 and seed and _should_roast(seed):
            result = random.choice(_ROASTS.get(lang, _ROASTS["en"]))
            await update.message.reply_text(result)
            return

        if humor_roll < 0.30 and vocab > 50:
            joke = _make_chain_joke(lang)
            if joke:
                joke = _apply_personality(joke, "goofy", lang)
                await update.message.reply_text(joke)
                return

        if humor_roll < 0.45 and vocab > 30:
            fact = _make_absurd_fact(lang)
            if fact:
                fact = _apply_personality(fact, "chaotic", lang)
                await update.message.reply_text(fact)
                return

        if humor_roll < 0.60 and seed:
            reaction = _strategy_topic_reaction(seed, lang)
            if reaction:
                await update.message.reply_text(reaction)
                return

        if humor_roll < 0.80:
            result = random.choice(_COMEBACKS.get(lang, _COMEBACKS["en"]))
            await update.message.reply_text(result)
            return

    # ── Standard generation with personality ──
    result = generate(seed, max_words=45, chat_id=chat.id, num_candidates=8)
    if not result:
        result = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))

    result = _apply_personality(result, mode, lang)

    if seed and _is_question(seed) and random.random() < 0.40:
        await update.message.reply_text(f"🤔 {result}")
    else:
        await update.message.reply_text(f"🧪 {result}")


# ═══════════════════════════════════════════════════
# /ai2test — Intelligence test with scoring
# ═══════════════════════════════════════════════════

_TEST_MESSAGES = [
    "سلام بچه‌ها حالتون چطوره امروز",
    "من دارم درس میخونم برای امتحان فردا",
    "این استاد خیلی سخت درس میده",
    "بریم یه چیزی بخوریم من گشنمه",
    "فیلم دیشب خیلی قشنگ بود پیشنهاد میکنم",
    "فوتبال دیشب رو دیدید چه بازی خوبی بود",
    "من عاشق پیتزا هستم مخصوصا با پنیر زیاد",
    "کد پایتون خیلی ساده و جالبه مخصوصا ربات",
    "بازی جدید خیلی گرافیکش توپه باید بزنید",
    "هوا خیلی سرده امروز فکر کنم برف بیاد",
    "موسیقی خوب حال آدمو خوب میکنه مخصوصا شبا",
    "دانشگاه خیلی شلوغه این ترم کلاسا پره",
    "من یه ربات جدید ساختم خیلی باحاله بچه‌ها",
    "قیمت‌ها خیلی رفته بالا همه چیز گرون شده",
    "خسته شدم از بس درس خوندم استراحت لازمه",
    "آهنگ جدید خوانندهٔ مورد علاقم اومده خیلی خوبه",
    "من با دوستام رفتم سینما فیلم خوبی بود",
    "پروژه برنامه‌نویسی خیلی سخته ولی جالبه",
    "امروز یه روز خوب بود خیلی خوش گذشت",
    "فردا امتحان داریم که هنوز نخوندم مشکل دارم",
    "هاهاها خیلی بامزه بود این جوک واقعا خندیدم",
    "وای دلم تنگ شده برای تعطیلات تابستون",
    "آیا فردا باز هم کلاس داریم استاد گفت؟",
    "بچه‌ها بیاید بازی کنیم حوصلم سر رفته",
    "Hey everyone how is it going today in group",
    "I am studying hard for tomorrow big exam",
    "This professor makes everything so hard really",
    "Let us get something good to eat I am hungry",
    "The movie last night was really great film",
    "Did you watch the football match it was awesome",
    "I love pizza especially with lots of extra cheese",
    "Python code is very simple and quite interesting really",
    "The new game has really amazing graphics wow",
    "Good music always makes you feel so much better",
    "University is so crowded this semester many students",
    "I built a new cool bot and it is awesome",
    "Prices have gone up everything is so expensive now",
    "I am tired from studying all day very long",
    "My favorite singer released a brand new song today",
    "Went to cinema with friends saw a very good movie",
    "The programming project is very challenging but fun",
    "Today was a good day had lots of fun really",
    "LMAO that was the absolute funniest thing ever said",
    "I cannot wait for the weekend honestly need rest",
    "Do we have class again tomorrow or is it off",
    "Hey guys lets play a game I am so bored",
    "عشقم دوستت دارم خیلی زیاد قلبم مال تو",
    "من عصبانی هستم از دست این وضعیت بد",
    "چرا همه چیز اینقدر سخته توی این دنیا",
    "خدایا شکرت امروز بهترین روز زندگیم بود",
]


async def ai2test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test brain intelligence with automated scoring."""
    chat = update.effective_chat
    lang = get_lang(chat.id)

    header = (
        "🧪🧠 *شروع تست هوش مارکوف...*"
        if lang == "fa"
        else "🧪🧠 *Starting Markov Intelligence Test...*"
    )
    await update.message.reply_text(header, parse_mode="Markdown")

    # Phase 1: Feed training data & measure growth
    pre_keys, pre_trans, pre_vocab = get_brain_stats()
    for msg in _TEST_MESSAGES:
        learn(msg)
    post_keys, post_trans, post_vocab = get_brain_stats()
    growth_keys = post_keys - pre_keys
    growth_vocab = post_vocab - pre_vocab

    # Phase 2: Test generation quality
    test_seeds = [
        "درس امتحان دانشگاه",
        "غذا پیتزا رستوران",
        "فوتبال بازی تیم",
        "programming code python",
        "music song favorite",
        "movie cinema night",
    ]
    gen_scores: list[float] = []
    gen_results: list[tuple[str, str, float]] = []
    for seed in test_seeds:
        result = generate(seed, max_words=30, chat_id=chat.id, num_candidates=6)
        if result:
            words = result.split()
            unique = len(set(w.lower() for w in words))
            seed_hits = sum(
                1 for sw in seed.split() if sw.lower() in result.lower()
            )
            score = seed_hits * 2.0 + unique * 0.3 + min(len(words), 20) * 0.2
            gen_scores.append(score)
            gen_results.append((seed, result[:80], round(score, 1)))
        else:
            gen_scores.append(0)
    avg_gen = sum(gen_scores) / max(len(gen_scores), 1)

    # Phase 3: Test humor engine
    humor_ok = 0
    humor_total = 0
    for test_lang in ("fa", "en"):
        joke = _make_chain_joke(test_lang)
        if joke and len(joke) > 10:
            humor_ok += 1
        humor_total += 1
        fact = _make_absurd_fact(test_lang)
        if fact and len(fact) > 10:
            humor_ok += 1
        humor_total += 1

    # Phase 4: Test emotion detection
    emotion_tests = [
        ("خیلی خوشحالم امروز عالیه!", "happy"),
        ("I'm so sad and lonely today", "sad"),
        ("هاهاها مردم از خنده 😂😂", "funny"),
        ("Why does this happen to me?", "curious"),
        ("عشقم دوستت دارم ❤️", "romantic"),
    ]
    emotion_correct = sum(
        1 for text, expected in emotion_tests
        if _detect_emotion(text) == expected
    )
    emotion_pct = (emotion_correct / len(emotion_tests)) * 100

    # Phase 5: Test topic detection
    topic_tests = [
        ("بریم رستوران پیتزا بخوریم", "food"),
        ("I'm coding in Python right now", "tech"),
        ("فوتبال دیشب خیلی خوب بود", "sports"),
        ("The exam was really hard", "school"),
    ]
    topic_correct = sum(
        1 for text, expected in topic_tests
        if _detect_topic(text) == expected
    )
    topic_pct = (topic_correct / len(topic_tests)) * 100

    # Phase 6: Test strategy diversity
    strategies_ok = 0
    if _strategy_mashup():
        strategies_ok += 1
    if _strategy_reverse_wisdom():
        strategies_ok += 1
    if _strategy_echo_twist("this is a test seed message for echo"):
        strategies_ok += 1
    if _strategy_debate("Is Python the best programming language?"):
        strategies_ok += 1

    # ── Calculate Intelligence Score (0-100) ──
    brain_pts = min(25, (post_keys / 50) * 25)
    gen_pts = min(25, avg_gen * 2.5)
    humor_pts = (humor_ok / max(humor_total, 1)) * 15
    emotion_pts = (emotion_correct / len(emotion_tests)) * 15
    topic_pts = (topic_correct / len(topic_tests)) * 10
    strategy_pts = (strategies_ok / 4) * 10
    total_iq = brain_pts + gen_pts + humor_pts + emotion_pts + topic_pts + strategy_pts

    if total_iq >= 85:
        iq_label = "🧠 نابغه!" if lang == "fa" else "🧠 Genius!"
    elif total_iq >= 70:
        iq_label = "🌟 باهوش!" if lang == "fa" else "🌟 Smart!"
    elif total_iq >= 50:
        iq_label = "📚 متوسط" if lang == "fa" else "📚 Average"
    elif total_iq >= 30:
        iq_label = "🐣 در حال یادگیری" if lang == "fa" else "🐣 Learning"
    else:
        iq_label = "👶 نوزاد" if lang == "fa" else "👶 Newborn"

    # Build report
    sep = "═" * 28
    if lang == "fa":
        report = (
            f"🧪🧠 *نتیجه تست هوش مارکوف*\n{sep}\n\n"
            f"📊 *رشد مغز:*\n"
            f"  🔑 کلیدها: {pre_keys} → {post_keys} (+{growth_keys})\n"
            f"  📚 واژگان: {pre_vocab} → {post_vocab} (+{growth_vocab})\n\n"
            f"🎯 *کیفیت تولید:* {avg_gen:.1f}/10\n"
        )
        for seed, result, sc in gen_results[:3]:
            report += f"  💬 «{seed[:15]}» → _{result[:50]}_\n"
        report += (
            f"\n😂 *طنز:* {humor_ok}/{humor_total}\n"
            f"💭 *تشخیص احساس:* {emotion_pct:.0f}%\n"
            f"🏷 *تشخیص موضوع:* {topic_pct:.0f}%\n"
            f"🎲 *استراتژی‌ها:* {strategies_ok}/4\n\n"
            f"{sep}\n"
            f"🏆 *امتیاز هوش: {total_iq:.0f}/100*\n"
            f"📋 {iq_label}\n{sep}"
        )
    else:
        report = (
            f"🧪🧠 *Markov Intelligence Test Results*\n{sep}\n\n"
            f"📊 *Brain Growth:*\n"
            f"  🔑 Keys: {pre_keys} → {post_keys} (+{growth_keys})\n"
            f"  📚 Vocab: {pre_vocab} → {post_vocab} (+{growth_vocab})\n\n"
            f"🎯 *Generation Quality:* {avg_gen:.1f}/10\n"
        )
        for seed, result, sc in gen_results[:3]:
            report += f"  💬 \"{seed[:15]}\" → _{result[:50]}_\n"
        report += (
            f"\n😂 *Humor:* {humor_ok}/{humor_total}\n"
            f"💭 *Emotion Detection:* {emotion_pct:.0f}%\n"
            f"🏷 *Topic Detection:* {topic_pct:.0f}%\n"
            f"🎲 *Strategies:* {strategies_ok}/4\n\n"
            f"{sep}\n"
            f"🏆 *Intelligence Score: {total_iq:.0f}/100*\n"
            f"📋 {iq_label}\n{sep}"
        )

    await update.message.reply_text(report, parse_mode="Markdown")


# ═══════════════════════════════════════════════════
# /ai2stats — Comprehensive stats
# ═══════════════════════════════════════════════════

async def ai2stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)

    keys, transitions, vocab = get_brain_stats()
    ctx_chats = len(_chat_context)
    topics_tracked = len(_chat_topics)
    hot = _get_hot_topic(update.effective_chat.id)
    mode = _chat_personality.get(update.effective_chat.id, "neutral")

    if lang == "fa":
        text = (
            f"🧠 *آمار هوش مصنوعی مارکوف v2*\n"
            f"{'─' * 26}\n\n"
            f"🔑 کلیدها: *{keys:,}*\n"
            f"🔗 انتقال‌ها: *{transitions:,}*\n"
            f"📚 واژگان: *{vocab:,}*\n"
            f"📄 کل پیام‌ها: *{_total_docs:,}*\n"
            f"💬 چت‌های فعال: *{ctx_chats}*\n"
            f"🏷 موضوعات: *{topics_tracked}*\n"
            f"🔥 موضوع داغ: *{hot or 'نامشخص'}*\n"
            f"🎭 شخصیت: *{mode}*\n\n"
            f"😂 روست: *{len(_ROASTS['fa'])}* | "
            f"🃏 جوک: *{len(_JOKE_TEMPLATES['fa'])}* | "
            f"📊 فکت: *{len(_ABSURD_FACTS['fa'])}*\n"
            f"🎲 استراتژی: *6* | "
            f"🎭 شخصیت: *{len(_PERSONALITY_MODES)}*\n\n"
            f"💡 /ai2test — تست هوش"
        )
    else:
        text = (
            f"🧠 *Markov AI Stats v2*\n"
            f"{'─' * 26}\n\n"
            f"🔑 Keys: *{keys:,}*\n"
            f"🔗 Transitions: *{transitions:,}*\n"
            f"📚 Vocabulary: *{vocab:,}*\n"
            f"📄 Total messages: *{_total_docs:,}*\n"
            f"💬 Active chats: *{ctx_chats}*\n"
            f"🏷 Topics tracked: *{topics_tracked}*\n"
            f"🔥 Hot topic: *{hot or 'unknown'}*\n"
            f"🎭 Personality: *{mode}*\n\n"
            f"😂 Roasts: *{len(_ROASTS['en'])}* | "
            f"🃏 Jokes: *{len(_JOKE_TEMPLATES['en'])}* | "
            f"📊 Facts: *{len(_ABSURD_FACTS['en'])}*\n"
            f"🎲 Strategies: *6* | "
            f"🎭 Personalities: *{len(_PERSONALITY_MODES)}*\n\n"
            f"💡 /ai2test — Intelligence test"
        )
    await update.message.reply_text(text, parse_mode="Markdown")
