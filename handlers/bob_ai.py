# ==========================================
# KNTU Bot 25 — BOB 🤖 (/bob)
# The son of Markov (/ai2) and Ophelia (/ai3).
#
# Bob 2.0:
#   - Intent detection (question / greeting / joke / statement)
#   - Immutable identity lore + admin-taught knowledge (priority over learned)
#   - Fuzzy FA/EN taught matching, aliases, confidence, refuse-to-fake
#   - 8-day age gate: chat-learning paused until mature
#   - High-signal learning only (reply_to / mention / quality filters)
#   - Short-term chat context + correction loop (/bob wrong)
#   - Language lock (reply script follows input)
# ==========================================

from __future__ import annotations

import math
import random
import re
import threading
import logging
import time
from collections import deque
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from storage import get_lang, load_bob, save_bob

logger = logging.getLogger("kntu_bot25.bob")

_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════════════════
# TUNING / RESOURCE CAPS (sized for a small shared VM)
# ═══════════════════════════════════════════════════════════════════════════

_SAVE_EVERY = 20
_MIN_WORDS_TO_LEARN = 2
_MAX_CHAIN_KEYS = 60_000
_MAX_PAIR_KEYS = 6_000
_MAX_REPLIES_PER_PAIR = 4
_MAX_VOCAB = 25_000
_MAX_EMO_WORDS = 20_000
_GEN_CANDIDATES = 8
_GEN_MAX_WORDS = 18
_MIN_BRAIN_TO_SPEAK = 40
_MAX_TAUGHT = 500
_MAX_CONTEXT = 6
_AGE_GATE_DAYS = 8.0
_THINK_MIN_SCORE = 0.8
_PAIR_AUTO_MIN_SCORE = 1.4
_TAUGHT_MIN_SCORE = 0.55

BOB_MAX_AUTO_REPLIES_PER_DAY = 3
_AUTO_REPLY_BASE_CHANCE = 0.02
_AUTO_REPLY_MENTION_CHANCE = 0.35

EMOTIONS = ["happy", "sad", "angry", "afraid", "love"]

_SEED_EMOTION_WORDS = {
    "happy": ["lol", "haha", "😂", "😄", "خوش", "خنده", "عالی", "love", "great", "nice", "خوب"],
    "sad": ["😢", "😭", "غم", "ناراحت", "sad", "cry", "miss", "دلم"],
    "angry": ["عصبانی", "فحش", "angry", "hate", "fuck", "shit", "کیر", "حروم"],
    "afraid": ["ترس", "scared", "afraid", "وحشت", "نگران"],
    "love": ["عاشق", "دوستت", "❤️", "love", "kiss", "بغل", "قربون"],
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "is", "are",
    "was", "were", "be", "been", "it", "this", "that", "with", "as", "by", "from", "i", "you",
    "he", "she", "we", "they", "me", "my", "your", "و", "از", "به", "در", "که", "این", "آن",
    "را", "با", "برای", "هم", "یه", "یک", "من", "تو", "او", "ما", "شما", "ایشون", "رو", "تا",
    "اگر", "یا", "نه", "بله", "آره", "خب", "دیگه", "همه", "چی",
}

_FA_CHARS = re.compile(r"[\u0600-\u06ff]")
_BOB_MENTION = re.compile(r"\bbob\b|باب", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+|t\.me/\S+|www\.\S+", re.IGNORECASE)
_EMOJI_HEAVY = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]+",
)
_ZWNJ = "\u200c"

_QUESTION_WORDS_FA = {
    "چرا", "کی", "کجا", "چطور", "چگونه", "آیا",
    "مگه", "مگر", "چه", "چی", "کدوم", "کدام",
    "چند", "کیه", "چیه", "کجاست", "چیه؟",
}
_QUESTION_WORDS_EN = {
    "what", "why", "how", "when", "where", "who", "which",
    "is", "are", "do", "does", "can", "will", "would", "should",
    "did", "could", "whose", "whom",
}

_GREETINGS = {
    "salam", "سلام", "hello", "hi", "hey", "یروطح", "درود", "صبح", "عصر",
    "شب بخیر", "good morning", "good night", "hola", "yo", "سلامم", "سلوم",
    "سلام علیکم", "hiya", "howdy",
}

_JOKE_SIGNALS = {
    "haha", "hahaha", "lol", "lmao", "rofl", "خخ", "خخخ", "خخخخ",
    "😂", "🤣", "💀", "jk", "baje", "باجه", "جوک", "joke",
}

_CORRECTION_WORDS = {
    "غلط", "غلطہ", "wrong", "nope", "incorrect", "نادرست", "اشتباه",
    "نه باب", "نه bob", "اشتباهه", "غلط گفتی",
}

# Core lore — highest priority, not overwritten by chat learning
_DEFAULT_IDENTITY = {
    "name": "Bob",
    "name_fa": "باب",
    "father": "Markov",
    "father_fa": "مارکوف",
    "mother": "Ophelia",
    "mother_fa": "اوفلیا",
    "likes": ["chat", "learning", "kollars", "jokes"],
    "dislikes": ["silence", "spam"],
    "opinions": {
        "father": "My dad Markov taught me how words chain together.",
        "mother": "Mom Ophelia gave me feelings and reply memory.",
        "self": "I'm Bob — still growing, still listening.",
    },
    "lang_default": "fa",
}

# Keyword bags that map to identity slots (FA + EN)
_IDENTITY_TRIGGERS = [
    # (slot_or_callable_key, keyword sets)
    ("father", {"father", "dad", "daddy", "papa", "بابا", "پدر", "پدرت", "بابات", "باباهه"}),
    ("mother", {"mother", "mom", "mum", "mama", "مادر", "مامان", "مادرت", "مامانت"}),
    ("name", {"name", "اسم", "اسمت", "who are you", "تو کی", "کیستی", "خودت"}),
    ("self", {"who are you", "تو کیی", "تو کی هستی", "introduce", "خودتو معرفی"}),
]

_MOOD_FLAVOR = {
    "happy": {"fa": ["😄", "✨", "هی"], "en": ["😄", "✨", "nice"]},
    "sad": {"fa": ["😔", "…"], "en": ["😔", "..."]},
    "angry": {"fa": ["😤"], "en": ["😤"]},
    "afraid": {"fa": ["😬"], "en": ["😬"]},
    "love": {"fa": ["❤️", "💕"], "en": ["❤️", "💕"]},
    "neutral": {"fa": ["🤖"], "en": ["🤖"]},
}

_MOOD_NAMES = {
    "fa": {
        "happy": "خوشحال", "sad": "غمگین", "angry": "عصبانی",
        "afraid": "نگران", "love": "سرشار از محبت", "neutral": "آروم",
    },
    "en": {
        "happy": "happy", "sad": "sad", "angry": "angry",
        "afraid": "uneasy", "love": "loving", "neutral": "calm",
    },
}

_TOO_YOUNG = {
    "fa": "🍼 هنوز خیلی کوچیکم… بذار کمی بیشتر از چت یاد بگیرم (یا تو پی‌وی بهم یاد بده).",
    "en": "🍼 I'm still too young… let me learn a bit more (or teach me in PV).",
}

_NO_IDEA = {
    "fa": [
        "هنوز مطمئن نیستم 🤔",
        "ایدهٔ خوبی ندارم… بهم یاد بده؟",
        "مغزم قفل کرد 🤖",
    ],
    "en": [
        "Not sure yet 🤔",
        "I've got nothing solid — teach me?",
        "Brain blank 🤖",
    ],
}

_DONT_KNOW = {
    "fa": [
        "هنوز نمی‌دونم — تو پی‌وی بهم یاد بده 🧠",
        "اینو بلد نیستم. ادمین می‌تونه با /bob learn یادم بده.",
        "نمی‌دونم هنوز. دروغ نمی‌گم 🤖",
    ],
    "en": [
        "I don't know yet — teach me in PV 🧠",
        "No idea. Admin can /bob learn it for me.",
        "I won't fake an answer. Teach me?",
    ],
}

_GREETING_POOL = {
    "fa": [
        "سلام! من بابم 🤖",
        "درود — گوش می‌دم.",
        "سلام سلام! چه خبر؟",
        "هی! باب اینجاست.",
    ],
    "en": [
        "Hey — Bob here 🤖",
        "Hi! Listening.",
        "Hello hello!",
        "Yo — what's up?",
    ],
}

_JOKE_POOL = {
    "fa": ["خخخ 😂", "باحه 🤣", "کشتیم 💀", "آخ جون جوک"],
    "en": ["haha 😂", "lol nice", "I'm dead 💀", "good one"],
}

# Per-chat short-term memory
_last_msg: dict[int, str] = {}
_context: dict[int, deque] = {}
_last_reply_meta: dict[int, dict] = {}  # chat_id -> {source, pair_kw, pair_reply, taught_q}

_brain = None
_dirty_count = 0


def _now_ts() -> float:
    return time.time()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _default_brain() -> dict:
    emo = {}
    for e, words in _SEED_EMOTION_WORDS.items():
        for w in words:
            emo[w.lower()] = e
    return {
        "chain": {},
        "starters": {},
        "pairs": {},
        "word_emotion": emo,
        "vocab": {},
        "mood": {"valence": 0.0, "label": "neutral", "updated": _now_ts()},
        "auto_log": {},
        "stats": {"seen": 0, "replies": 0, "born": _now_ts(), "taught_uses": 0},
        "taught": [],
        "identity": dict(_DEFAULT_IDENTITY),
        "users": {},  # uid -> {name, notes, last_seen}
    }


def _get_brain() -> dict:
    """Load (or init) Bob's brain. Call with _lock held."""
    global _brain
    if _brain is None:
        stored = load_bob()
        _brain = stored if stored else _default_brain()
        for k, v in _default_brain().items():
            if k == "identity":
                base = dict(_DEFAULT_IDENTITY)
                if isinstance(_brain.get("identity"), dict):
                    base.update(_brain["identity"])
                _brain["identity"] = base
            else:
                _brain.setdefault(k, v if not isinstance(v, dict) else dict(v))
        if "taught" not in _brain or not isinstance(_brain["taught"], list):
            _brain["taught"] = []
        if "users" not in _brain or not isinstance(_brain["users"], dict):
            _brain["users"] = {}
    return _brain


def _mark_dirty(force: bool = False):
    global _dirty_count
    _dirty_count += 1
    if force or _dirty_count >= _SAVE_EVERY:
        _dirty_count = 0
        try:
            save_bob(_brain)
        except Exception as e:
            logger.warning("Bob brain save failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZE / LANGUAGE / INTENT
# ═══════════════════════════════════════════════════════════════════════════

def _fa_normalize_char(ch: str) -> str:
    # Arabic yeh/kaf → Persian; strip tatweel
    table = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
        "ٔ": "",
        "ٰ": "",
        "‌": " ",  # ZWNJ → space for matching
        "‏": "",
        "‎": "",
        "ـ": "",
    }
    return table.get(ch, ch)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = _URL_RE.sub(" ", t)
    t = "".join(_fa_normalize_char(c) for c in t)
    t = re.sub(r"[?!؟.،,;؛:\"'`]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _tokenize(text: str) -> list[str]:
    text = _normalize_text(text)
    text = re.sub(r"[^\w\s\u0600-\u06ff\U0001F000-\U0001FAFF\u2764\ufe0f]", " ", text)
    return [w for w in text.split() if w]


def _keywords(words: list[str]) -> list[str]:
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]


def _keyword_key(text: str) -> str:
    kws = sorted(set(_keywords(_tokenize(text))))
    return " ".join(kws)


def _is_farsi(text: str) -> bool:
    return bool(_FA_CHARS.search(text or ""))


def _reply_lang(text: str, chat_lang: str) -> str:
    """Language lock: prefer input script, else chat default."""
    if text and _is_farsi(text):
        return "fa"
    if text and re.search(r"[A-Za-z]", text) and not _is_farsi(text):
        return "en"
    return "fa" if chat_lang == "fa" else "en"


def _detect_emotion(words: list[str], brain: dict) -> str:
    counts = {e: 0 for e in EMOTIONS}
    for w in words:
        e = brain["word_emotion"].get(w)
        if e in counts:
            counts[e] += 1
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "neutral"


def _detect_intent(text: str) -> str:
    raw = (text or "").strip()
    norm = _normalize_text(raw)
    if not norm:
        return "statement"

    # joke signals first (often short)
    toks = set(norm.split())
    if any(s in norm for s in _JOKE_SIGNALS) or toks & _JOKE_SIGNALS:
        return "joke"

    # greeting: whole message short and greets
    if any(norm == g or norm.startswith(g + " ") or norm.endswith(" " + g) for g in _GREETINGS):
        if len(norm.split()) <= 4:
            return "greeting"
    if toks & _GREETINGS and len(norm.split()) <= 3:
        return "greeting"

    # question
    if raw.rstrip().endswith(("?", "؟")):
        return "question"
    words = _tokenize(raw)
    if words:
        w0 = words[0]
        if w0 in _QUESTION_WORDS_EN or w0 in _QUESTION_WORDS_FA:
            return "question"
        if any(w in _QUESTION_WORDS_FA for w in words[:4]):
            return "question"
        # EN mid-sentence who/what about Bob
        if any(w in {"who", "what", "why", "how", "where", "when"} for w in words[:6]):
            return "question"
    return "statement"


def _age_days(brain: dict) -> float:
    born = brain.get("stats", {}).get("born", _now_ts())
    return max(0.0, (_now_ts() - born) / 86400.0)


def _learning_unlocked(brain: dict) -> bool:
    return _age_days(brain) >= _AGE_GATE_DAYS


def _is_admin(user_id: int | None) -> bool:
    return bool(user_id) and int(user_id) in set(ADMIN_IDS or [])


def _push_context(chat_id: int, text: str):
    buf = _context.setdefault(chat_id, deque(maxlen=_MAX_CONTEXT))
    buf.append(text[:300])


def _context_keywords(chat_id: int) -> set[str]:
    buf = _context.get(chat_id) or []
    kws: set[str] = set()
    for msg in buf:
        kws.update(_keywords(_tokenize(msg))[:6])
    return kws


# ═══════════════════════════════════════════════════════════════════════════
# LEARNING
# ═══════════════════════════════════════════════════════════════════════════

def _prune(table: dict, cap: int, keep_ratio: float = 0.8):
    if len(table) <= cap:
        return

    def weight(v):
        if isinstance(v, dict):
            return sum(n for n in v.values() if isinstance(n, int))
        if isinstance(v, list):
            return sum(item.get("n", 1) for item in v)
        return v if isinstance(v, int) else 1

    keep = int(cap * keep_ratio)
    survivors = sorted(table.items(), key=lambda kv: weight(kv[1]), reverse=True)[:keep]
    table.clear()
    table.update(survivors)


def _quality_ok(text: str) -> bool:
    """Reject spam / low-signal training data."""
    if not text or text.startswith("/"):
        return False
    t = text.strip()
    if len(t) > 400:
        return False
    no_url = _URL_RE.sub("", t).strip()
    if not no_url:
        return False
    words = _tokenize(no_url)
    if len(words) < _MIN_WORDS_TO_LEARN:
        return False
    # mostly emoji
    alpha = re.sub(r"\W+", "", no_url, flags=re.UNICODE)
    if len(alpha) < 2:
        return False
    return True


def learn_message(
    chat_id: int,
    text: str,
    *,
    is_reply: bool = False,
    mentions_bob: bool = False,
    is_private: bool = False,
    force: bool = False,
):
    """Learn one chat message with age gate + quality + signal filters."""
    if not force:
        if not _quality_ok(text):
            return
        # High-signal only after unlock (always allow forced admin paths)
        if not (is_reply or mentions_bob or is_private):
            # still track last msg for pair continuity but don't train chains on noise
            # Actually: for group ambient chat after unlock, learn chains lightly
            # but pairs only on reply/mention. Pre-unlock: skip all.
            pass

    words = _tokenize(text)
    if len(words) < _MIN_WORDS_TO_LEARN:
        return

    with _lock:
        brain = _get_brain()
        if not force and not _learning_unlocked(brain):
            # Age gate: no chains/pairs/vocab/emotion/mood from public chat
            _last_msg[chat_id] = text
            _push_context(chat_id, text)
            return

        high_signal = force or is_reply or mentions_bob or is_private

        # Ambient group messages after unlock: learn style (chains/vocab) only
        # if quality ok; pairs require high_signal
        for w in words:
            brain["vocab"][w] = brain["vocab"].get(w, 0) + 1

        if len(words) >= 3:
            key0 = f"{words[0]} {words[1]}"
            brain["starters"][key0] = brain["starters"].get(key0, 0) + 1
            for i in range(len(words) - 2):
                key = f"{words[i]} {words[i + 1]}"
                nxt = brain["chain"].setdefault(key, {})
                nxt[words[i + 2]] = nxt.get(words[i + 2], 0) + 1

        emotion = _detect_emotion(words, brain)
        if emotion != "neutral" and len(brain["word_emotion"]) < _MAX_EMO_WORDS:
            for w in _keywords(words):
                if w not in brain["word_emotion"]:
                    brain["word_emotion"][w] = emotion

        prev = _last_msg.get(chat_id)
        if high_signal and prev and prev != text:
            for kw in _keywords(_tokenize(prev))[:4]:
                bucket = brain["pairs"].setdefault(kw, [])
                for item in bucket:
                    if item["r"] == text:
                        item["n"] += 1
                        break
                else:
                    bucket.append({"r": text[:200], "e": emotion, "n": 1})
                    if len(bucket) > _MAX_REPLIES_PER_PAIR:
                        bucket.sort(key=lambda x: x["n"], reverse=True)
                        del bucket[_MAX_REPLIES_PER_PAIR:]

        _last_msg[chat_id] = text
        _push_context(chat_id, text)

        mood = brain["mood"]
        elapsed = _now_ts() - mood.get("updated", _now_ts())
        mood["valence"] *= math.exp(-elapsed / 3600.0)
        shift = {
            "happy": 0.15, "love": 0.2, "sad": -0.15,
            "angry": -0.2, "afraid": -0.1,
        }.get(emotion, 0.0)
        mood["valence"] = max(-1.0, min(1.0, mood["valence"] + shift))
        if emotion != "neutral":
            mood["label"] = emotion
        elif abs(mood["valence"]) < 0.1:
            mood["label"] = "neutral"
        mood["updated"] = _now_ts()

        brain["stats"]["seen"] = brain["stats"].get("seen", 0) + 1
        if brain["stats"]["seen"] % 500 == 0:
            _prune(brain["chain"], _MAX_CHAIN_KEYS)
            _prune(brain["starters"], _MAX_CHAIN_KEYS // 10)
            _prune(brain["pairs"], _MAX_PAIR_KEYS)
            _prune(brain["vocab"], _MAX_VOCAB)
        _mark_dirty()


# ═══════════════════════════════════════════════════════════════════════════
# IDENTITY + TAUGHT KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════════

def _identity_answer(brain: dict, text: str, lang: str) -> str | None:
    norm = _normalize_text(text)
    kws = set(_keywords(_tokenize(text)))
    ident = brain.get("identity") or _DEFAULT_IDENTITY

    # father / mother / name
    for slot, triggers in _IDENTITY_TRIGGERS:
        if kws & triggers or any(t in norm for t in triggers if " " in t):
            if slot == "father":
                return ident.get("father_fa") if lang == "fa" else ident.get("father")
            if slot == "mother":
                return ident.get("mother_fa") if lang == "fa" else ident.get("mother")
            if slot == "name":
                name = ident.get("name_fa") if lang == "fa" else ident.get("name")
                dad = ident.get("father_fa") if lang == "fa" else ident.get("father")
                mom = ident.get("mother_fa") if lang == "fa" else ident.get("mother")
                if lang == "fa":
                    return f"من {name} هستم، پسر {dad} و {mom}."
                return f"I'm {name}, son of {dad} and {mom}."
            if slot == "self":
                op = (ident.get("opinions") or {}).get("self")
                if op:
                    return op
                if lang == "fa":
                    return f"من {ident.get('name_fa', 'باب')}ام — هنوز دارم یاد می‌گیرم."
                return f"I'm {ident.get('name', 'Bob')} — still learning."

    # likes / dislikes
    if kws & {"like", "likes", "دوست", "علاقه", "دوست داری", "favorites"}:
        likes = ident.get("likes") or []
        if likes:
            return ("دوست دارم: " if lang == "fa" else "I like: ") + ", ".join(likes)
    if kws & {"dislike", "dislikes", "متنفر", "بدت میاد"}:
        d = ident.get("dislikes") or []
        if d:
            return ("خوشم نمیاد از: " if lang == "fa" else "I dislike: ") + ", ".join(d)

    # opinions about mom/dad
    if kws & {"opinion", "فکر", "نظرت"}:
        ops = ident.get("opinions") or {}
        if kws & {"father", "dad", "پدر", "بابا", "مارکوف", "markov"}:
            return ops.get("father")
        if kws & {"mother", "mom", "مادر", "مامان", "ophelia", "اوفلیا"}:
            return ops.get("mother")
    return None


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _char_ngrams(s: str, n: int = 3) -> set[str]:
    s = re.sub(r"\s+", "", s)
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _taught_score(entry: dict, text: str, brain: dict) -> float:
    """Score how well a taught entry matches the user text."""
    q_raw = entry.get("raw_q") or ""
    aliases = entry.get("aliases") or []
    candidates = [q_raw] + list(aliases)
    input_key = _keyword_key(text)
    input_kws = set(input_key.split()) if input_key else set()
    input_norm = _normalize_text(text)
    best = 0.0

    for cand in candidates:
        cand_key = _keyword_key(cand) if cand else entry.get("q", "")
        if not cand_key and entry.get("q"):
            cand_key = entry["q"]
        if input_key and cand_key and input_key == cand_key:
            best = max(best, 10.0)
            continue
        cand_kws = set(cand_key.split()) if cand_key else set()
        # rarity-weighted overlap
        if input_kws and cand_kws:
            overlap = sum(_rarity(brain, w) for w in input_kws & cand_kws)
            rel = overlap / (1 + len(input_kws))
            jac = _jaccard(input_kws, cand_kws)
            # full phrase containment bonus
            cnorm = _normalize_text(cand)
            contain = 0.4 if cnorm and (cnorm in input_norm or input_norm in cnorm) else 0.0
            # char ngram soft match (FA morphology)
            ng = _jaccard(_char_ngrams(input_norm), _char_ngrams(cnorm)) if cnorm else 0.0
            score = (2.0 * rel) + (1.5 * jac) + contain + (0.8 * ng)
            # prefer more specific (longer) taught questions slightly
            score += 0.05 * min(6, len(cand_kws))
            best = max(best, score)
        elif entry.get("q") == input_key:
            best = max(best, 10.0)
    return best


def _find_taught(brain: dict, text: str) -> tuple[dict | None, float]:
    taught = brain.get("taught") or []
    if not taught:
        return None, 0.0
    best_e, best_s = None, 0.0
    for e in taught:
        s = _taught_score(e, text, brain)
        if s > best_s:
            best_s, best_e = s, e
    if best_e and best_s >= _TAUGHT_MIN_SCORE:
        return best_e, best_s
    return None, best_s


def _upsert_taught(
    brain: dict,
    question: str,
    answer: str,
    aliases: list[str] | None = None,
) -> dict:
    key = _keyword_key(question)
    aliases = aliases or []
    # also split "q1 | q2 | q3" style
    parts = [p.strip() for p in re.split(r"[|｜]", question) if p.strip()]
    if len(parts) > 1:
        question = parts[0]
        aliases = list(aliases) + parts[1:]
        key = _keyword_key(question)

    for e in brain["taught"]:
        if e.get("q") == key or _normalize_text(e.get("raw_q", "")) == _normalize_text(question):
            e["a"] = answer
            e["raw_q"] = question
            e["q"] = key or e.get("q") or _normalize_text(question)
            existing = list(e.get("aliases") or [])
            for a in aliases:
                if a and a not in existing:
                    existing.append(a)
            e["aliases"] = existing[:12]
            e["n_uses"] = e.get("n_uses", 0)
            return e

    entry = {
        "q": key or _normalize_text(question),
        "raw_q": question,
        "a": answer,
        "aliases": aliases[:12],
        "n_uses": 0,
    }
    brain["taught"].append(entry)
    if len(brain["taught"]) > _MAX_TAUGHT:
        brain["taught"].sort(key=lambda x: x.get("n_uses", 0), reverse=True)
        del brain["taught"][_MAX_TAUGHT:]
    return entry


def _forget_taught(brain: dict, question: str) -> bool:
    key = _keyword_key(question)
    norm = _normalize_text(question)
    kept = []
    removed = False
    for e in brain["taught"]:
        if e.get("q") == key or _normalize_text(e.get("raw_q", "")) == norm:
            removed = True
            continue
        # alias hit
        if any(_normalize_text(a) == norm for a in (e.get("aliases") or [])):
            removed = True
            continue
        kept.append(e)
    brain["taught"] = kept
    return removed


def _downrank_last(brain: dict, chat_id: int) -> str:
    """Correction loop: undo/downrank last answer source."""
    meta = _last_reply_meta.get(chat_id) or {}
    src = meta.get("source")
    if src == "taught":
        q = meta.get("taught_q")
        if q and _forget_taught(brain, q):
            return "taught_removed"
        return "taught_miss"
    if src == "pair":
        kw = meta.get("pair_kw")
        reply = meta.get("pair_reply")
        if kw and reply and kw in brain.get("pairs", {}):
            bucket = brain["pairs"][kw]
            brain["pairs"][kw] = [x for x in bucket if x.get("r") != reply]
            if not brain["pairs"][kw]:
                del brain["pairs"][kw]
            return "pair_removed"
        return "pair_miss"
    return "nothing"


# ═══════════════════════════════════════════════════════════════════════════
# GENERATION + SCORING
# ═══════════════════════════════════════════════════════════════════════════

def _rarity(brain: dict, word: str) -> float:
    total = max(1, brain["stats"].get("seen", 1))
    freq = brain["vocab"].get(word, 1)
    return math.log(1 + total / freq)


def _pick_next(options: dict, temperature: float = 1.0) -> str | None:
    if not options:
        return None
    words = list(options.keys())
    weights = [options[w] ** (1.0 / max(0.1, temperature)) for w in words]
    return random.choices(words, weights=weights, k=1)[0]


def _generate_from_seed(brain: dict, seed_key: str) -> str | None:
    chain = brain["chain"]
    if seed_key not in chain:
        return None
    w1, w2 = seed_key.split(" ", 1)
    out = [w1, w2]
    for _ in range(_GEN_MAX_WORDS - 2):
        nxt = _pick_next(chain.get(f"{out[-2]} {out[-1]}", {}), temperature=1.2)
        if not nxt:
            break
        out.append(nxt)
        if len(out) >= 6 and random.random() < 0.18:
            break
    return " ".join(out) if len(out) >= 3 else None


def _seed_keys_for(brain: dict, words: list[str], extra_kws: set[str] | None = None) -> list[str]:
    chain = brain["chain"]
    seeds = []
    for i in range(len(words) - 1):
        key = f"{words[i]} {words[i + 1]}"
        if key in chain:
            seeds.append(key)
    if len(seeds) < 3:
        kws = set(_keywords(words))
        if extra_kws:
            kws |= set(list(extra_kws)[:8])
        if kws:
            for key in list(chain.keys())[:20_000]:
                k1, _, k2 = key.partition(" ")
                if k1 in kws or k2 in kws:
                    seeds.append(key)
                    if len(seeds) >= 10:
                        break
    return seeds


def _score_candidate(brain: dict, cand: str, input_kws: set, input_emotion: str) -> float:
    words = _tokenize(cand)
    if not words:
        return -1.0
    kws = set(_keywords(words))

    overlap = sum(_rarity(brain, w) for w in kws & input_kws)
    relevance = overlap / (1 + len(input_kws)) if input_kws else 0.3

    echo = len(kws & input_kws) / len(kws) if kws else 1.0
    echo_pen = 1.5 if echo > 0.8 else 0.0

    seen = 0
    for i in range(len(words) - 2):
        if words[i + 2] in brain["chain"].get(f"{words[i]} {words[i + 1]}", {}):
            seen += 1
    coherence = seen / max(1, len(words) - 2)

    cand_emotion = _detect_emotion(words, brain)
    mood_label = brain["mood"]["label"]
    emo_fit = 0.5
    if input_emotion != "neutral" and cand_emotion == input_emotion:
        emo_fit = 1.0
    elif cand_emotion == mood_label:
        emo_fit = 0.8

    n = len(words)
    length_fit = 1.0 if 3 <= n <= 18 else 0.4

    return (2.2 * relevance) + (1.6 * coherence) + (0.8 * emo_fit) + (0.6 * length_fit) - echo_pen


def _think(brain: dict, text: str, chat_id: int | None = None) -> tuple[str | None, float, dict]:
    """Return (reply, score, meta). Meta describes source for corrections."""
    words = _tokenize(text)
    input_kws = set(_keywords(words))
    if chat_id is not None:
        input_kws |= set(list(_context_keywords(chat_id))[:6])
    input_emotion = _detect_emotion(words, brain)

    candidates: list[tuple[str, str, dict]] = []  # text, source, meta

    for kw in list(input_kws)[:12]:
        for item in brain["pairs"].get(kw, []):
            candidates.append((item["r"], "pair", {"pair_kw": kw, "pair_reply": item["r"]}))

    seeds = _seed_keys_for(brain, words, input_kws)
    random.shuffle(seeds)
    for seed in seeds[:_GEN_CANDIDATES]:
        gen = _generate_from_seed(brain, seed)
        if gen:
            candidates.append((gen, "generate", {}))

    starters = list(brain["starters"].keys())
    if starters:
        for _ in range(2):
            gen = _generate_from_seed(brain, random.choice(starters))
            if gen:
                candidates.append((gen, "generate", {}))

    if not candidates:
        return None, 0.0, {}

    scored = []
    for c, src, meta in candidates:
        sc = _score_candidate(brain, c, input_kws, input_emotion)
        # slight boost for real pairs over pure generation
        if src == "pair":
            sc += 0.15
        scored.append((sc, c, src, meta))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best, src, meta = scored[0]
    if best_score < _THINK_MIN_SCORE:
        return None, best_score, {}
    meta = dict(meta)
    meta["source"] = src
    return best, best_score, meta


def _flavor(brain: dict, reply: str, lang: str) -> str:
    label = brain["mood"]["label"]
    if random.random() < 0.45:
        emo = random.choice(_MOOD_FLAVOR.get(label, _MOOD_FLAVOR["neutral"]).get(lang, ["🤖"]))
        return f"{reply} {emo}"
    return reply


def _answer(brain: dict, text: str, lang: str, chat_id: int | None = None) -> tuple[str, dict]:
    """
    Full answer pipeline:
      identity → taught → intent handlers → pairs/generate → refuse
    Returns (reply, meta).
    """
    intent = _detect_intent(text)
    meta: dict = {"intent": intent, "source": "none", "confidence": 0.0}

    # 1) identity (immutable lore)
    ident = _identity_answer(brain, text, lang)
    if ident:
        meta.update({"source": "identity", "confidence": 1.0})
        return ident, meta

    # 2) taught knowledge
    entry, tscore = _find_taught(brain, text)
    if entry:
        entry["n_uses"] = entry.get("n_uses", 0) + 1
        brain["stats"]["taught_uses"] = brain["stats"].get("taught_uses", 0) + 1
        meta.update({
            "source": "taught",
            "confidence": min(1.0, tscore / 5.0),
            "taught_q": entry.get("raw_q") or entry.get("q"),
        })
        return entry["a"], meta

    # 3) intent-specific
    if intent == "greeting":
        meta.update({"source": "greeting", "confidence": 0.9})
        return random.choice(_GREETING_POOL[lang]), meta

    if intent == "joke":
        witty, sc, tmeta = _think(brain, text, chat_id)
        base = random.choice(_JOKE_POOL[lang])
        if witty and sc >= _THINK_MIN_SCORE:
            meta.update({"source": tmeta.get("source", "joke"), "confidence": sc / 5.0, **tmeta})
            return f"{base} {witty}", meta
        meta.update({"source": "joke", "confidence": 0.7})
        return base, meta

    # 4) learned / generated — but questions must not hallucinate facts
    reply, score, tmeta = _think(brain, text, chat_id)
    if intent == "question":
        # Only accept strong, *relevant* pair hits for questions.
        # Coherence alone is not enough — require keyword overlap with the ask.
        input_kws = set(_keywords(_tokenize(text)))
        reply_kws = set(_keywords(_tokenize(reply or "")))
        relevant = bool(input_kws & reply_kws)
        if (
            reply
            and tmeta.get("source") == "pair"
            and score >= _PAIR_AUTO_MIN_SCORE
            and relevant
        ):
            meta.update({"confidence": score / 5.0, **tmeta})
            return reply, meta
        meta.update({"source": "refuse", "confidence": 0.0})
        return random.choice(_DONT_KNOW[lang]), meta

    if reply:
        meta.update({"confidence": score / 5.0, **tmeta})
        return reply, meta

    meta.update({"source": "refuse", "confidence": 0.0})
    return random.choice(_NO_IDEA[lang]), meta


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN TEACHING PARSERS
# ═══════════════════════════════════════════════════════════════════════════

_LEARN_RE = re.compile(
    r"^(?:learn|یادبده|یاد\s*بده)\s+(.+?)\s*=\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_FORGET_RE = re.compile(
    r"^(?:forget|فراموش|پاک)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_LIKE_RE = re.compile(r"^(?:like|دوست)\s+(.+)$", re.IGNORECASE)
_DISLIKE_RE = re.compile(r"^(?:dislike|متنفر)\s+(.+)$", re.IGNORECASE)
_OPINION_RE = re.compile(
    r"^(?:opinion|نظر)\s+(\S+)\s*=\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def _admin_help(lang: str) -> str:
    if lang == "fa":
        return (
            "🤖 *آموزش باب (فقط ادمین — پی‌وی)*\n"
            "`/bob learn سوال = جواب`\n"
            "`/bob learn q1 | q2 = answer` (چند عبارت)\n"
            "`/bob forget سوال`\n"
            "`/bob list`\n"
            "`/bob like pizza` / `/bob dislike spam`\n"
            "`/bob opinion father = ...`\n"
            "`/bob wrong` — آخرین جواب اشتباه\n"
            "`/bob <متن>` — تست جواب"
        )
    return (
        "🤖 *Teach Bob (admin PV only)*\n"
        "`/bob learn question = answer`\n"
        "`/bob learn q1 | q2 = answer` (aliases)\n"
        "`/bob forget question`\n"
        "`/bob list`\n"
        "`/bob like pizza` / `/bob dislike spam`\n"
        "`/bob opinion father = ...`\n"
        "`/bob wrong` — correct last reply\n"
        "`/bob <text>` — test answer"
    )


# ═══════════════════════════════════════════════════════════════════════════
# TELEGRAM HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def bob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bob [message] — talk to Bob (admin PV: teach mode)."""
    if not update.message:
        return
    chat = update.effective_chat
    chat_id = chat.id
    user = update.effective_user
    chat_lang = get_lang(chat_id)
    lang = "fa" if chat_lang == "fa" else "en"
    is_private = chat.type == "private"
    admin = _is_admin(user.id if user else None)

    raw_args = " ".join(context.args) if context.args else ""
    if not raw_args and update.message.reply_to_message and update.message.reply_to_message.text:
        raw_args = update.message.reply_to_message.text

    # Admin PV teaching surface
    if is_private and admin:
        if not raw_args:
            await update.message.reply_text(_admin_help(lang), parse_mode="Markdown")
            return

        low = raw_args.strip()
        # list
        if re.match(r"^(list|لیست)$", low, re.I):
            with _lock:
                brain = _get_brain()
                items = list(brain.get("taught") or [])
            if not items:
                await update.message.reply_text("📭 empty" if lang == "en" else "📭 خالیه")
                return
            lines = []
            for e in items[:30]:
                lines.append(f"• {e.get('raw_q', e.get('q'))} → {e.get('a')}")
            more = len(items) - 30
            msg = "📚 taught:\n" + "\n".join(lines)
            if more > 0:
                msg += f"\n… +{more}"
            await update.message.reply_text(msg[:3500])
            return

        # wrong / correction
        if re.match(r"^(wrong|غلط|mistake)$", low, re.I):
            with _lock:
                brain = _get_brain()
                result = _downrank_last(brain, chat_id)
                _mark_dirty(force=True)
            await update.message.reply_text(f"🩹 {result}")
            return

        m = _LEARN_RE.match(low)
        if m:
            q, a = m.group(1).strip(), m.group(2).strip()
            with _lock:
                brain = _get_brain()
                entry = _upsert_taught(brain, q, a)
                _mark_dirty(force=True)
            await update.message.reply_text(
                f"✅ taught: {entry.get('raw_q')} → {entry.get('a')}"
            )
            return

        m = _FORGET_RE.match(low)
        if m:
            q = m.group(1).strip()
            with _lock:
                brain = _get_brain()
                ok = _forget_taught(brain, q)
                _mark_dirty(force=True)
            await update.message.reply_text("🗑️ forgotten" if ok else "❓ not found")
            return

        m = _LIKE_RE.match(low)
        if m:
            thing = m.group(1).strip()
            with _lock:
                brain = _get_brain()
                likes = brain["identity"].setdefault("likes", [])
                if thing not in likes:
                    likes.append(thing)
                _upsert_taught(brain, f"what do you like|دوست داری چی", ", ".join(likes))
                _mark_dirty(force=True)
            await update.message.reply_text(f"💛 likes += {thing}")
            return

        m = _DISLIKE_RE.match(low)
        if m:
            thing = m.group(1).strip()
            with _lock:
                brain = _get_brain()
                d = brain["identity"].setdefault("dislikes", [])
                if thing not in d:
                    d.append(thing)
                _mark_dirty(force=True)
            await update.message.reply_text(f"💔 dislikes += {thing}")
            return

        m = _OPINION_RE.match(low)
        if m:
            key, val = m.group(1).strip().lower(), m.group(2).strip()
            with _lock:
                brain = _get_brain()
                ops = brain["identity"].setdefault("opinions", {})
                ops[key] = val
                _upsert_taught(brain, f"opinion {key}|نظرت درباره {key}", val)
                _mark_dirty(force=True)
            await update.message.reply_text(f"💭 opinion[{key}] = {val}")
            return

    # Normal talk / non-admin
    text = raw_args
    if not text:
        text = "سلام" if lang == "fa" else "hello"

    # group correction shortcut: /bob wrong
    if re.match(r"^(wrong|غلط)$", text.strip(), re.I):
        with _lock:
            brain = _get_brain()
            result = _downrank_last(brain, chat_id)
            _mark_dirty(force=True)
        await update.message.reply_text(f"🩹 {result}")
        return

    rlang = _reply_lang(text, lang)

    with _lock:
        brain = _get_brain()
        has_knowledge = bool(_identity_answer(brain, text, rlang) or _find_taught(brain, text)[0])
        if brain["stats"].get("seen", 0) < _MIN_BRAIN_TO_SPEAK and not has_knowledge:
            # still allow greetings
            if _detect_intent(text) not in ("greeting",) and not has_knowledge:
                await update.message.reply_text(_TOO_YOUNG[rlang])
                return

        reply, meta = _answer(brain, text, rlang, chat_id)
        brain["stats"]["replies"] = brain["stats"].get("replies", 0) + 1
        # don't flavor refuse/identity/taught as heavily
        if meta.get("source") in ("identity", "taught", "refuse", "greeting"):
            out = reply
        else:
            out = _flavor(brain, reply, rlang)
        _last_reply_meta[chat_id] = meta
        _push_context(chat_id, text)
        _mark_dirty()

    await update.message.reply_text(out)


async def bobstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bobstats — Bob's brain report + age gate."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    lang = "fa" if get_lang(chat_id) == "fa" else "en"

    with _lock:
        brain = _get_brain()
        seen = brain["stats"].get("seen", 0)
        replies = brain["stats"].get("replies", 0)
        vocab = len(brain.get("vocab") or {})
        contexts = len(brain.get("chain") or {})
        pairs = sum(len(v) for v in (brain.get("pairs") or {}).values())
        emo_words = len(brain.get("word_emotion") or {})
        taught_n = len(brain.get("taught") or [])
        taught_uses = brain["stats"].get("taught_uses", 0)
        valence = brain["mood"]["valence"]
        label = brain["mood"]["label"]
        age_days = _age_days(brain)
        unlocked = _learning_unlocked(brain)

    mood_name = _MOOD_NAMES[lang].get(label, label)
    bar_pos = int((valence + 1) / 2 * 10)
    mood_bar = "▱" * bar_pos + "●" + "▱" * (10 - bar_pos)
    gate = (
        (f"🍼 learning from chat unlocks at {_AGE_GATE_DAYS:.0f} days "
         f"({max(0, _AGE_GATE_DAYS - age_days):.1f} left)")
        if not unlocked else
        "🎓 chat-learning unlocked"
    )
    gate_fa = (
        (f"🍼 یادگیری از چت در {_AGE_GATE_DAYS:.0f} روزگی باز می‌شود "
         f"({max(0, _AGE_GATE_DAYS - age_days):.1f} روز مانده)")
        if not unlocked else
        "🎓 یادگیری از چت باز است"
    )

    if lang == "fa":
        msg = (
            "🤖 *باب — پسر مارکوف و اوفلیا*\n\n"
            f"🧠 پیام‌هایی که ازشون یاد گرفته: *{seen:,}*\n"
            f"📚 کلمه‌هایی که بلده: *{vocab:,}*\n"
            f"🔗 الگوهای جمله‌سازی: *{contexts:,}*\n"
            f"💬 جواب‌های واقعی که حفظ کرده: *{pairs:,}*\n"
            f"🎭 کلمه‌های احساسی: *{emo_words:,}*\n"
            f"📖 دانش آموزش‌داده‌شده: *{taught_n:,}* (استفاده: {taught_uses})\n"
            f"🗣 جواب‌هایی که داده: *{replies:,}*\n"
            f"🎂 سن: *{age_days:.1f}* روز\n"
            f"{gate_fa}\n\n"
            f"💙 حالِ الان باب: *{mood_name}*\n"
            f"😞 {mood_bar} 😊"
        )
    else:
        msg = (
            "🤖 *Bob — son of Markov & Ophelia*\n\n"
            f"🧠 Messages learned from: *{seen:,}*\n"
            f"📚 Words he knows: *{vocab:,}*\n"
            f"🔗 Sentence patterns: *{contexts:,}*\n"
            f"💬 Real replies memorized: *{pairs:,}*\n"
            f"🎭 Emotion-tagged words: *{emo_words:,}*\n"
            f"📖 Taught knowledge: *{taught_n:,}* (uses: {taught_uses})\n"
            f"🗣 Replies given: *{replies:,}*\n"
            f"🎂 Age: *{age_days:.1f}* days\n"
            f"{gate}\n\n"
            f"💙 Bob feels: *{mood_name}*\n"
            f"😞 {mood_bar} 😊"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def bob_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passive listener: gated learning + sparse auto-replies."""
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    if not user or user.is_bot:
        return
    text = update.message.text
    if text.startswith("/"):
        return

    chat = update.effective_chat
    chat_id = chat.id
    is_private = chat.type == "private"
    is_reply = bool(
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and (
            update.message.reply_to_message.from_user.id == context.bot.id
            or True  # any reply_to is conversational signal
        )
    )
    # stronger signal if replying to Bob specifically
    reply_to_bob = bool(
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )
    mentions_bob = bool(_BOB_MENTION.search(text)) or reply_to_bob

    # remember user display name lightly
    if user and user.first_name:
        with _lock:
            brain = _get_brain()
            u = brain["users"].setdefault(str(user.id), {})
            u["name"] = user.first_name
            u["last_seen"] = _now_ts()

    learn_message(
        chat_id,
        text,
        is_reply=is_reply,
        mentions_bob=mentions_bob,
        is_private=is_private and _is_admin(user.id),
    )

    # correction without command: reply "wrong" to Bob
    _norm_corr = _normalize_text(text)
    if reply_to_bob and (
        _norm_corr in _CORRECTION_WORDS
        or any(w in _norm_corr for w in ("wrong", "غلط", "اشتباه"))
    ):
        with _lock:
            brain = _get_brain()
            result = _downrank_last(brain, chat_id)
            _mark_dirty(force=True)
        try:
            await update.message.reply_text(f"🩹 {result}")
        except Exception:
            pass
        return

    if chat.type not in ("group", "supergroup"):
        return

    chance = _AUTO_REPLY_MENTION_CHANCE if mentions_bob else _AUTO_REPLY_BASE_CHANCE
    if reply_to_bob:
        chance = max(chance, 0.55)
    if random.random() >= chance:
        return

    chat_lang = get_lang(chat_id)
    rlang = _reply_lang(text, chat_lang)

    with _lock:
        brain = _get_brain()
        has_knowledge = bool(_identity_answer(brain, text, rlang) or _find_taught(brain, text)[0])
        if brain["stats"].get("seen", 0) < _MIN_BRAIN_TO_SPEAK and not has_knowledge:
            return
        log = brain["auto_log"].setdefault(str(chat_id), {"date": _today(), "count": 0})
        if log["date"] != _today():
            log["date"] = _today()
            log["count"] = 0
        if log["count"] >= BOB_MAX_AUTO_REPLIES_PER_DAY:
            return

        reply, meta = _answer(brain, text, rlang, chat_id)
        # stricter auto-reply confidence
        conf = float(meta.get("confidence") or 0)
        src = meta.get("source")
        if src == "refuse":
            if not mentions_bob:
                return
        elif src in ("generate",) and conf < 0.25 and not mentions_bob:
            return
        elif src == "none":
            return

        log["count"] += 1
        brain["stats"]["replies"] = brain["stats"].get("replies", 0) + 1
        if src in ("identity", "taught", "greeting", "refuse"):
            out = reply
        else:
            out = _flavor(brain, reply, rlang)
        _last_reply_meta[chat_id] = meta
        _mark_dirty(force=True)

    try:
        await update.message.reply_text(out)
    except Exception as e:
        logger.warning("Bob auto-reply failed: %s", e)


# ── test helpers (used by unit tests; safe no-ops in prod) ─────────────────

def _reset_brain_for_tests(brain: dict | None = None):
    """Replace in-memory brain (tests only)."""
    global _brain, _dirty_count, _last_msg, _context, _last_reply_meta
    with _lock:
        _brain = brain if brain is not None else _default_brain()
        _dirty_count = 0
        _last_msg = {}
        _context = {}
        _last_reply_meta = {}


def _force_born_days_ago(days: float):
    with _lock:
        brain = _get_brain()
        brain["stats"]["born"] = _now_ts() - (days * 86400.0)
