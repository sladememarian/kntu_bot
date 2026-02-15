# ==========================================
# KNTU Bot 25 — OPHELIA-style AI (/ai3)
# Emotion-tagged retrieval chatbot inspired by
# github.com/stringzzz/Chatbot_OPHELIA
#
# Key differences from Markov AI (/ai2):
#   - Learns message→response PAIRS (not chains)
#   - Emotion-tagged storage (happy/sad/angry/afraid/love)
#   - Exact → partial → keyword match retrieval
#   - Mood tracking per user and per chat
#   - Progressive evolution (unlocks skills as it learns)
#   - Personality shifts based on current mood
# ==========================================

import random
import re
import threading
import logging
import time
import collections

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, load_data, save_data

logger = logging.getLogger("kntu_bot25.ophelia")

_lock = threading.Lock()

# ═══════════════════════════════════════════════════
# EMOTION SYSTEM
# ═══════════════════════════════════════════════════

EMOTIONS = ["happy", "sad", "angry", "afraid", "love"]

# Seed emotion dictionary (FA + EN words)
_SEED_EMOTION_WORDS = {
    "happy": [
        "happy", "خوشحال", "good", "great", "خوب", "عالی", "nice", "awesome",
        "love", "fun", "funny", "lol", "haha", "خنده", "بامزه", "cool", "عشق",
        "beautiful", "زیبا", "perfect", "best", "بهترین", "amazing", "wow",
        "joy", "شاد", "smile", "لبخند", "blessed", "thank", "ممنون", "مرسی",
        "excellent", "fantastic", "wonderful", "brilliant", "superb", "خفن",
        "cute", "ناز", "sweet", "lovely", "adorable", "دوست", "like", "enjoy",
        "celebrate", "party", "win", "بردیم", "bravo", "آفرین", "yay", "هورا",
        "😂", "😊", "😍", "🥰", "❤️", "💕", "🎉", "👏", "😄", "🤣",
    ],
    "sad": [
        "sad", "غمگین", "cry", "گریه", "miss", "دلتنگ", "alone", "تنها",
        "lonely", "depressed", "افسرده", "sorry", "متاسف", "pain", "درد",
        "broke", "lost", "hurt", "tired", "خسته", "بد", "bad", "terrible",
        "awful", "horrible", "worst", "بدترین", "unfortunately", "متاسفانه",
        "disappointed", "ناامید", "tear", "اشک", "sigh", "آه", "miss",
        "😢", "😭", "💔", "😞", "😔", "🥺",
    ],
    "angry": [
        "angry", "عصبانی", "hate", "متنفر", "shut", "خفه", "stupid", "احمق",
        "idiot", "fool", "دیوونه", "mad", "furious", "rage", "خشم", "damn",
        "hell", "fight", "جنگ", "kill", "destroy", "نابود", "terrible",
        "annoying", "اذیت", "disgusting", "چندش", "ugly", "زشت", "worst",
        "lame", "trash", "garbage", "sick", "fed up", "بسه", "ساکت",
        "😤", "😡", "🤬", "💢", "👊",
    ],
    "afraid": [
        "afraid", "ترس", "scared", "fear", "وحشت", "danger", "خطر", "help",
        "کمک", "run", "فرار", "ghost", "روح", "dark", "تاریک", "monster",
        "horror", "وحشتناک", "creepy", "nightmare", "کابوس", "panic",
        "terrified", "worried", "نگران", "nervous", "استرس", "stress",
        "anxious", "اضطراب", "shock", "شوک", "omg", "yikes",
        "😱", "😰", "😨", "🫣", "💀",
    ],
    "love": [
        "love", "عشق", "darling", "عزیزم", "heart", "قلب", "kiss", "بوسه",
        "hug", "بغل", "romance", "رمانتیک", "crush", "baby", "عزیز",
        "sweetheart", "honey", "جونم", "miss you", "دلم تنگه", "forever",
        "together", "couple", "boyfriend", "girlfriend", "wife", "husband",
        "marry", "ازدواج", "valentine", "rose", "گل", "date", "عاشق",
        "💕", "💖", "💗", "💘", "💝", "😘", "🥰", "😍", "💑", "❤️‍🔥",
    ],
}

# Neutral words to ignore during matching
_NEUTRAL_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "must", "need", "ought",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "mine",
    "yours", "hers", "ours", "theirs", "this", "that", "these", "those",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "not", "no", "nor", "but", "or", "and", "if", "then", "else", "so",
    "than", "too", "very", "just", "about", "above", "after", "again",
    "all", "also", "any", "because", "before", "between", "both", "each",
    "few", "for", "from", "get", "got", "here", "in", "into", "more",
    "most", "of", "on", "only", "other", "our", "out", "over", "own",
    "same", "some", "such", "to", "up", "with", "at", "by",
    "و", "در", "به", "از", "که", "با", "را", "این", "آن", "هم",
    "یه", "یک", "من", "تو", "ما", "اون", "رو", "هست", "نیست",
    "می", "بود", "شد", "داره", "داری", "دارم", "کجا", "چی", "چرا",
}


# ═══════════════════════════════════════════════════
# OPHELIA BRAIN: Persistent storage via data.json/PG
# ═══════════════════════════════════════════════════

def _load_ophelia() -> dict:
    """Load OPHELIA brain from persistent storage."""
    data = load_data()
    brain = data.get("ophelia_brain", {})
    if not brain:
        brain = {
            "emotion_dict": {},      # word → emotion
            "message_pairs": {e: {} for e in EMOTIONS},  # emotion → {msg: response}
            "chat_moods": {},        # chat_id → {emotion counts + current mood}
            "user_moods": {},        # chat_id → {user_id → {emotion counts}}
            "stats": {"total_learned": 0, "total_conversations": 0},
        }
        # Seed the emotion dictionary
        for emotion, words in _SEED_EMOTION_WORDS.items():
            for w in words:
                brain["emotion_dict"][w.lower()] = emotion
    return brain


def _save_ophelia(brain: dict):
    """Save OPHELIA brain to persistent storage."""
    data = load_data()
    data["ophelia_brain"] = brain
    save_data(data)


# ═══════════════════════════════════════════════════
# CORE LOGIC
# ═══════════════════════════════════════════════════

def _detect_mood(text: str, brain: dict) -> tuple:
    """
    Analyze text, detect emotion of each word, return:
    (overall_mood, emotion_counts, unknown_words)
    """
    words = re.sub(r'[^\w\s]', '', text.lower()).split()
    counts = {e: 0 for e in EMOTIONS}
    unknown = []

    for w in words:
        if w in _NEUTRAL_WORDS or len(w) < 2:
            continue
        emotion = brain["emotion_dict"].get(w)
        if emotion and emotion in counts:
            counts[emotion] += 1
        else:
            unknown.append(w)

    # Determine dominant mood
    max_count = max(counts.values()) if counts else 0
    if max_count == 0:
        mood = "happy"  # default
    else:
        mood = max(counts, key=counts.get)

    return mood, counts, unknown


def _learn_unknown_words(brain: dict, unknown_words: list, mood: str):
    """Tag unknown words with the detected mood (OPHELIA's learning)."""
    for w in unknown_words:
        if w not in brain["emotion_dict"] and len(w) >= 2:
            brain["emotion_dict"][w] = mood


def _update_chat_mood(brain: dict, chat_id: str, counts: dict):
    """Update the chat's overall mood based on new message."""
    chat_moods = brain.setdefault("chat_moods", {})
    cm = chat_moods.setdefault(chat_id, {e: 0 for e in EMOTIONS})
    cm.setdefault("current", "happy")
    for e in EMOTIONS:
        cm[e] = cm.get(e, 0) + counts.get(e, 0)
    # Determine new current mood
    max_e = max(EMOTIONS, key=lambda e: cm.get(e, 0))
    if cm.get(max_e, 0) > 0:
        cm["current"] = max_e


def _update_user_mood(brain: dict, chat_id: str, user_id: str, counts: dict):
    """Track each user's emotional tendency."""
    user_moods = brain.setdefault("user_moods", {})
    um = user_moods.setdefault(chat_id, {}).setdefault(user_id, {e: 0 for e in EMOTIONS})
    for e in EMOTIONS:
        um[e] = um.get(e, 0) + counts.get(e, 0)


def _get_chat_mood(brain: dict, chat_id: str) -> str:
    """Get current mood for a chat."""
    return brain.get("chat_moods", {}).get(chat_id, {}).get("current", "happy")


def _get_user_dominant_mood(brain: dict, chat_id: str, user_id: str) -> str:
    """Get a user's overall dominant mood."""
    um = brain.get("user_moods", {}).get(chat_id, {}).get(user_id, {})
    if not um:
        return "happy"
    return max(EMOTIONS, key=lambda e: um.get(e, 0))


# ═══════════════════════════════════════════════════
# RETRIEVAL: Exact → Partial → Keyword match
# ═══════════════════════════════════════════════════

def _find_response(brain: dict, text: str, mood: str) -> str | None:
    """
    OPHELIA-style retrieval:
    1. Exact match under current mood
    2. Partial match under current mood
    3. Exact/partial match under any mood
    4. Single keyword match (progressive: needs enough learning)
    5. No match → return None (will learn instead)
    """
    text_lower = text.lower().strip()
    pairs = brain.get("message_pairs", {})

    # 1. Exact match in current mood
    mood_pairs = pairs.get(mood, {})
    if text_lower in mood_pairs:
        return mood_pairs[text_lower]

    # 2. Partial match in current mood
    for msg, resp in mood_pairs.items():
        if msg in text_lower or text_lower in msg:
            return resp

    # 3. Exact/partial in OTHER moods
    for other_mood in EMOTIONS:
        if other_mood == mood:
            continue
        other_pairs = pairs.get(other_mood, {})
        if text_lower in other_pairs:
            return other_pairs[text_lower]
        for msg, resp in other_pairs.items():
            if msg in text_lower or text_lower in msg:
                return resp

    # 4. Word-overlap scoring (fuzzy match across all moods)
    words_set = set(re.sub(r'[^\w\s]', '', text_lower).split())
    meaningful = {w for w in words_set if w not in _NEUTRAL_WORDS and len(w) >= 2}

    if meaningful:
        best_resp = None
        best_score = 0

        for m in EMOTIONS:
            for msg, resp in pairs.get(m, {}).items():
                msg_words = set(msg.split())
                overlap = meaningful & msg_words
                if overlap:
                    score = len(overlap) / max(len(meaningful), len(msg_words))
                    # Boost score if same mood
                    if m == mood:
                        score *= 1.3
                    if score > best_score:
                        best_score = score
                        best_resp = resp

        # Accept if overlap is decent
        if best_resp and best_score >= 0.2:
            return best_resp

    # 5. Keyword match (progressive — only if learned enough)
    total_words = len(brain.get("emotion_dict", {}))
    total_pairs = sum(len(v) for v in pairs.values())

    keyword_chance = 0.0
    if total_words >= 100 and total_pairs >= 15:
        keyword_chance = 0.35
    if total_words >= 300 and total_pairs >= 50:
        keyword_chance = 0.60
    if total_words >= 700 and total_pairs >= 100:
        keyword_chance = 0.85

    if keyword_chance > 0 and random.random() < keyword_chance:
        kw_list = list(meaningful)
        random.shuffle(kw_list)

        for word in kw_list:
            emo = brain["emotion_dict"].get(word)
            search_mood = emo if (emo and emo != "neutral") else mood

            for msg, resp in pairs.get(search_mood, {}).items():
                if word in msg:
                    return resp
            for m in EMOTIONS:
                if m == search_mood:
                    continue
                for msg, resp in pairs.get(m, {}).items():
                    if word in msg:
                        return resp

    return None


def _learn_pair(brain: dict, prev_msg: str, response: str, mood: str):
    """Learn a new message→response pair under the given mood."""
    if not prev_msg or not response or len(prev_msg) < 2 or len(response) < 2:
        return
    pairs = brain.setdefault("message_pairs", {e: {} for e in EMOTIONS})
    mood_pairs = pairs.setdefault(mood, {})

    prev_lower = prev_msg.lower().strip()
    resp_lower = response.lower().strip()

    # Don't learn if identical
    if prev_lower == resp_lower:
        return

    # Cap per-mood pairs at 2000 to prevent bloat
    if len(mood_pairs) >= 2000:
        # Remove oldest (first inserted)
        oldest_key = next(iter(mood_pairs))
        del mood_pairs[oldest_key]

    mood_pairs[prev_lower] = resp_lower
    brain["stats"]["total_learned"] = brain["stats"].get("total_learned", 0) + 1


# ═══════════════════════════════════════════════════
# MOOD-BASED RANDOM RESPONSES (fallback)
# ═══════════════════════════════════════════════════

_MOOD_RESPONSES = {
    "happy": {
        "fa": [
            "😊 خوشحالم! بگو بگو!",
            "🎉 عالیه! ادامه بده!",
            "😄 چه حال خوبی داری! منم خوشحالم!",
            "✨ امروز روز خوبیه!",
            "💫 انرژی مثبت حس می‌کنم!",
            "🌟 آره بابا! زندگی خوبه!",
            "😁 هه هه! خوش می‌گذره!",
            "🥳 بریم که بریم!",
        ],
        "en": [
            "😊 I'm happy! Tell me more!",
            "🎉 Awesome! Keep going!",
            "😄 What a great mood! I'm happy too!",
            "✨ Today is a good day!",
            "💫 I feel positive energy!",
            "🌟 Yeah! Life is good!",
            "😁 Hehe! Having fun!",
            "🥳 Let's goooo!",
        ],
    },
    "sad": {
        "fa": [
            "😢 ناراحت نباش... همه‌چیز درست میشه.",
            "💙 من اینجام. حرف بزن.",
            "🥺 غمگینم... ولی امید هست.",
            "😔 بعضی روزها سخته... ولی می‌گذره.",
            "💔 درکت می‌کنم...",
            "🌧️ بعد از بارون آفتاب میاد.",
            "😿 حالم خوب نیست...",
            "🫂 یه بغل مجازی بهت می‌دم.",
        ],
        "en": [
            "😢 Don't be sad... everything will be okay.",
            "💙 I'm here. Talk to me.",
            "🥺 I'm sad too... but there's hope.",
            "😔 Some days are hard... but they pass.",
            "💔 I understand...",
            "🌧️ After the rain comes sunshine.",
            "😿 I'm not feeling great...",
            "🫂 Sending you a virtual hug.",
        ],
    },
    "angry": {
        "fa": [
            "😤 آروم باش! نفس عمیق بکش!",
            "🔥 اوه! عصبانی شدی؟",
            "😡 خب... حق داری عصبانی باشی.",
            "💢 بزن به تخته! آروم شو!",
            "🤬 واو! چه خشمی!",
            "😠 هی! آروم‌تر!",
            "⚡ انرژی منفی حس می‌کنم!",
            "🧊 یه لیوان آب سرد بخور آروم شی.",
        ],
        "en": [
            "😤 Calm down! Take a deep breath!",
            "🔥 Whoa! You seem angry!",
            "😡 Well... you have the right to be mad.",
            "💢 Easy there! Calm down!",
            "🤬 Wow! Such rage!",
            "😠 Hey! Take it easy!",
            "⚡ I sense negative energy!",
            "🧊 Have a glass of cold water to cool off.",
        ],
    },
    "afraid": {
        "fa": [
            "😱 نترس! من اینجام!",
            "🫣 چی شده؟ نگران نباش!",
            "😰 آروم باش... خطری نیست.",
            "💪 قوی باش! می‌تونی!",
            "🛡️ من محافظتت می‌کنم!",
            "😨 اوه! ترسناکه ولی نگران نباش!",
            "🌟 همه‌چیز امن و امانه!",
            "🤗 نگران نباش، با هم از پسش برمیایم!",
        ],
        "en": [
            "😱 Don't be afraid! I'm here!",
            "🫣 What happened? Don't worry!",
            "😰 Calm down... there's no danger.",
            "💪 Be strong! You can do it!",
            "🛡️ I'll protect you!",
            "😨 Oh! Scary, but don't worry!",
            "🌟 Everything is safe!",
            "🤗 Don't worry, we'll get through this together!",
        ],
    },
    "love": {
        "fa": [
            "💕 اوووو! عشق در هواست!",
            "😍 چه رمانتیک!",
            "💘 قلبم داره تند تند می‌زنه!",
            "🥰 عاشقانه‌هاتو دوست دارم!",
            "💝 عشق همه‌چیزه!",
            "💗 چه احساس قشنگی!",
            "😘 بوووس!",
            "❤️‍🔥 آتیش عشق!",
        ],
        "en": [
            "💕 Awww! Love is in the air!",
            "😍 How romantic!",
            "💘 My heart is beating fast!",
            "🥰 I love your love stories!",
            "💝 Love is everything!",
            "💗 What a beautiful feeling!",
            "😘 Muah!",
            "❤️‍🔥 Fire of love!",
        ],
    },
}


# ═══════════════════════════════════════════════════
# MOOD PERSONALITY PREFIXES (make responses feel moody)
# ═══════════════════════════════════════════════════

_MOOD_WRAPPERS = {
    "happy": {
        "fa": ["😊 ", "😄 ", "🌟 ", "✨ ", ""],
        "en": ["😊 ", "😄 ", "🌟 ", "✨ ", ""],
    },
    "sad": {
        "fa": ["😢 ", "😔 ", "💙 ", "🥺 ", ""],
        "en": ["😢 ", "😔 ", "💙 ", "🥺 ", ""],
    },
    "angry": {
        "fa": ["😤 ", "😡 ", "🔥 ", "💢 ", ""],
        "en": ["😤 ", "😡 ", "🔥 ", "💢 ", ""],
    },
    "afraid": {
        "fa": ["😰 ", "😱 ", "🫣 ", "😨 ", ""],
        "en": ["😰 ", "😱 ", "🫣 ", "😨 ", ""],
    },
    "love": {
        "fa": ["💕 ", "😍 ", "💘 ", "🥰 ", ""],
        "en": ["💕 ", "😍 ", "💘 ", "🥰 ", ""],
    },
}


# ═══════════════════════════════════════════════════
# CONTEXT TRACKING: remember last messages per chat
# ═══════════════════════════════════════════════════

_last_messages: dict[int, str] = {}  # chat_id → last bot-seen user message
_chat_history: dict[int, list] = {}  # chat_id → last N messages for context
_HISTORY_SIZE = 8  # remember last 8 messages per chat
_auto_reply_cd: dict[int, float] = {}  # chat_id → last auto-reply timestamp

AUTO_REPLY_CHANCE = 0.08  # 8%
AUTO_REPLY_MENTIONED = 0.30  # 30% when mentioned
AUTO_REPLY_COOLDOWN = 25  # seconds

_MENTION_PATTERNS = re.compile(
    r"(ophelia|آفلیا|ai3|هوش3|ربات|bot)", re.IGNORECASE
)


# ═══════════════════════════════════════════════════
# MAIN HANDLERS
# ═══════════════════════════════════════════════════

async def ophelia_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listen to group messages, learn pairs, and occasionally auto-reply."""
    if not update.message or not update.message.text:
        return
    chat = update.effective_chat
    user = update.effective_user
    if not user or user.is_bot:
        return

    text = update.message.text.strip()
    if not text or len(text) < 2 or text.startswith("/"):
        return

    cid = str(chat.id)
    uid = str(user.id)

    with _lock:
        brain = _load_ophelia()

        # Detect mood of message
        mood, counts, unknown = _detect_mood(text, brain)

        # Learn unknown words
        _learn_unknown_words(brain, unknown, mood)

        # Update mood tracking
        _update_chat_mood(brain, cid, counts)
        _update_user_mood(brain, cid, uid, counts)

        # Learn message→response pair from conversation flow
        prev = _last_messages.get(chat.id)
        if prev and prev != text.lower():
            _learn_pair(brain, prev, text, mood)

        # Remember this message and update chat history
        _last_messages[chat.id] = text.lower()
        hist = _chat_history.setdefault(chat.id, [])
        hist.append(text.lower())
        if len(hist) > _HISTORY_SIZE:
            hist.pop(0)

        _save_ophelia(brain)

    # Auto-reply chance
    now = time.time()
    last_reply = _auto_reply_cd.get(chat.id, 0)
    if now - last_reply < AUTO_REPLY_COOLDOWN:
        return

    mentioned = bool(_MENTION_PATTERNS.search(text))
    # Boost chance if user replied to bot's message
    is_reply_to_bot = (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.is_bot
    )
    if is_reply_to_bot:
        chance = 0.85
    else:
        chance = AUTO_REPLY_MENTIONED if mentioned else AUTO_REPLY_CHANCE

    if random.random() < chance:
        _auto_reply_cd[chat.id] = now
        lang = get_lang(chat.id)

        with _lock:
            brain = _load_ophelia()
            chat_mood = _get_chat_mood(brain, cid)

            # Try to find a learned response
            response = _find_response(brain, text, chat_mood)

            if response:
                # Wrap with mood emoji
                prefix = random.choice(_MOOD_WRAPPERS.get(chat_mood, {}).get(lang, [""]))
                reply = prefix + response
            else:
                # Fallback: mood-based random response
                reply = random.choice(
                    _MOOD_RESPONSES.get(chat_mood, _MOOD_RESPONSES["happy"]).get(lang, ["..."])
                )

        await update.message.reply_text(reply)


async def ai3_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ai3 [message] — Talk to OPHELIA AI.
    Uses emotion-tagged retrieval, learns from you.
    """
    chat = update.effective_chat
    user = update.effective_user
    lang = get_lang(chat.id)

    args_text = " ".join(context.args) if context.args else ""

    # If replying to a message with no args, use the replied text
    if not args_text and update.message.reply_to_message and update.message.reply_to_message.text:
        args_text = update.message.reply_to_message.text

    if not args_text:
        # Show help/info
        with _lock:
            brain = _load_ophelia()
        total_words = len(brain.get("emotion_dict", {}))
        total_pairs = sum(len(v) for v in brain.get("message_pairs", {}).values())
        learned = brain.get("stats", {}).get("total_learned", 0)

        # Evolution level
        if total_pairs < 30:
            level = "🥒 Newborn" if lang == "en" else "🥒 نوزاد"
        elif total_pairs < 80:
            level = "🌱 Learning" if lang == "en" else "🌱 یادگیرنده"
        elif total_pairs < 150:
            level = "🌿 Aware" if lang == "en" else "🌿 آگاه"
        elif total_pairs < 300:
            level = "🌳 Smart" if lang == "en" else "🌳 باهوش"
        else:
            level = "🧠 Genius" if lang == "en" else "🧠 نابغه"

        if lang == "fa":
            msg = (
                "🦋 *OPHELIA AI — هوش مصنوعی احساسی*\n\n"
                f"📊 کلمات احساسی: *{total_words}*\n"
                f"💬 جفت‌های پیام یادگرفته: *{total_pairs}*\n"
                f"📈 کل یادگیری: *{learned}*\n"
                f"🎭 سطح تکامل: *{level}*\n\n"
                "💡 استفاده: `/ai3 سلام چطوری؟`\n"
                "📖 آفلیا از مکالمات گروه یاد می‌گیره و\n"
                "بر اساس *احساسات* جواب می‌ده!\n\n"
                "🆚 تفاوت با /ai2:\n"
                "• ai2 = زنجیره مارکوف (تولید متن)\n"
                "• ai3 = حافظه احساسی (بازیابی پاسخ)"
            )
        else:
            msg = (
                "🦋 *OPHELIA AI — Emotion-Aware Intelligence*\n\n"
                f"📊 Emotion Words: *{total_words}*\n"
                f"💬 Learned Pairs: *{total_pairs}*\n"
                f"📈 Total Learning: *{learned}*\n"
                f"🎭 Evolution Level: *{level}*\n\n"
                "💡 Usage: `/ai3 hello how are you?`\n"
                "📖 OPHELIA learns from group conversations and\n"
                "responds based on *emotions*!\n\n"
                "🆚 Difference from /ai2:\n"
                "• ai2 = Markov chains (text generation)\n"
                "• ai3 = Emotion memory (response retrieval)"
            )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    cid = str(chat.id)
    uid = str(user.id)
    user_name = user.first_name or "User"

    with _lock:
        brain = _load_ophelia()

        # Detect mood
        mood, counts, unknown = _detect_mood(args_text, brain)

        # Learn unknown words
        _learn_unknown_words(brain, unknown, mood)

        # Update moods
        _update_chat_mood(brain, cid, counts)
        _update_user_mood(brain, cid, uid, counts)

        # Current chat mood (influenced by all messages)
        chat_mood = _get_chat_mood(brain, cid)

        # Try to find a response
        response = _find_response(brain, args_text, chat_mood)

        if response:
            # Wrap with mood personality
            prefix = random.choice(_MOOD_WRAPPERS.get(chat_mood, {}).get(lang, [""]))
            reply = prefix + response
        else:
            # No match — give mood fallback and learn
            reply = random.choice(
                _MOOD_RESPONSES.get(chat_mood, _MOOD_RESPONSES["happy"]).get(lang, ["..."])
            )

        # Learn from this interaction
        prev = _last_messages.get(chat.id)
        if prev:
            _learn_pair(brain, prev, args_text, mood)
        _last_messages[chat.id] = args_text.lower()

        _save_ophelia(brain)

    await update.message.reply_text(reply)


async def ai3stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ai3stats — Show OPHELIA brain statistics."""
    chat = update.effective_chat
    lang = get_lang(chat.id)
    cid = str(chat.id)

    with _lock:
        brain = _load_ophelia()

    total_words = len(brain.get("emotion_dict", {}))
    pairs = brain.get("message_pairs", {})
    total_pairs = sum(len(v) for v in pairs.values())
    learned = brain.get("stats", {}).get("total_learned", 0)
    chat_mood = _get_chat_mood(brain, cid)

    # Count words per emotion
    emo_counts = collections.Counter()
    for w, e in brain.get("emotion_dict", {}).items():
        emo_counts[e] += 1

    # Pair counts per emotion
    pair_counts = {e: len(pairs.get(e, {})) for e in EMOTIONS}

    # Evolution features
    kw_match = "❌"
    if total_words >= 100 and total_pairs >= 15:
        kw_match = "35%"
    if total_words >= 300 and total_pairs >= 50:
        kw_match = "60%"
    if total_words >= 700 and total_pairs >= 100:
        kw_match = "85%"

    # Evolution level
    if total_pairs < 30:
        level = "🥒 Newborn" if lang == "en" else "🥒 نوزاد"
    elif total_pairs < 80:
        level = "🌱 Learning" if lang == "en" else "🌱 یادگیرنده"
    elif total_pairs < 150:
        level = "🌿 Aware" if lang == "en" else "🌿 آگاه"
    elif total_pairs < 300:
        level = "🌳 Smart" if lang == "en" else "🌳 باهوش"
    else:
        level = "🧠 Genius" if lang == "en" else "🧠 نابغه"

    emo_labels = {"happy": "😊", "sad": "😢", "angry": "😡", "afraid": "😨", "love": "💕"}

    if lang == "fa":
        lines = [
            "🦋 *آمار مغز OPHELIA*\n",
            f"📊 کل کلمات: *{total_words}*",
            f"💬 کل جفت‌ها: *{total_pairs}*",
            f"📈 یادگیری: *{learned}*",
            f"🎭 سطح: *{level}*",
            f"🧠 حال‌وهوای چت: *{emo_labels.get(chat_mood, '❓')} {chat_mood}*",
            f"🔍 تطبیق کلیدواژه: *{kw_match}*\n",
            "*کلمات احساسی:*",
        ]
        for e in EMOTIONS:
            lines.append(f"  {emo_labels[e]} {e}: {emo_counts.get(e, 0)} کلمه | {pair_counts[e]} جفت")
    else:
        lines = [
            "🦋 *OPHELIA Brain Stats*\n",
            f"📊 Total Words: *{total_words}*",
            f"💬 Total Pairs: *{total_pairs}*",
            f"📈 Learning: *{learned}*",
            f"🎭 Level: *{level}*",
            f"🧠 Chat Mood: *{emo_labels.get(chat_mood, '❓')} {chat_mood}*",
            f"🔍 Keyword Match: *{kw_match}*\n",
            "*Emotion Words:*",
        ]
        for e in EMOTIONS:
            lines.append(f"  {emo_labels[e]} {e}: {emo_counts.get(e, 0)} words | {pair_counts[e]} pairs")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
