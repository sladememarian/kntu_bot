# ==========================================
# KNTU Bot 25 — BOB 🤖 (/bob)
# The son of Markov (/ai2) and Ophelia (/ai3).
#
# What Bob inherited:
#   - From Markov: n-gram text generation learned from real chat
#   - From Ophelia: emotion tagging, mood tracking, reply pairs
#
# What makes Bob smarter than his parents:
#   - Generates MANY candidate replies, then SCORES each for
#     relevance / coherence / emotion-fit — no more random blurting
#   - Learns real conversation flow (message -> actual human reply)
#   - A continuous mood ("feeling") state that drifts with the chat
#     and shades his replies (an honest simulation, not consciousness)
#   - Self-pruning memory caps — Bob never outgrows a small VM
#
# Bob only speaks when called with /bob, plus at most
# BOB_MAX_AUTO_REPLIES_PER_DAY spontaneous replies per chat per day.
# ==========================================

import random
import re
import threading
import logging
import time
import math
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, load_bob, save_bob

logger = logging.getLogger("kntu_bot25.bob")

_lock = threading.Lock()

# ═══════════════════════════════════════════════════
# TUNING / RESOURCE CAPS (sized for a small shared VM)
# ═══════════════════════════════════════════════════

_SAVE_EVERY = 20              # persist brain every N learned messages
_MIN_WORDS_TO_LEARN = 2       # ignore ultra-short messages
_MAX_CHAIN_KEYS = 60_000      # trigram contexts (a few MB of JSON max)
_MAX_PAIR_KEYS = 6_000        # learned stimulus->reply pairs
_MAX_REPLIES_PER_PAIR = 4
_MAX_VOCAB = 25_000           # word frequency table
_MAX_EMO_WORDS = 20_000       # word->emotion table
_GEN_CANDIDATES = 8           # candidates generated per /bob call
_GEN_MAX_WORDS = 18
_MIN_BRAIN_TO_SPEAK = 40      # messages Bob must see before speaking

BOB_MAX_AUTO_REPLIES_PER_DAY = 3
_AUTO_REPLY_BASE_CHANCE = 0.02    # per message, when under the daily cap
_AUTO_REPLY_MENTION_CHANCE = 0.35  # when someone says "bob"

EMOTIONS = ["happy", "sad", "angry", "afraid", "love"]

# Compact seed lexicon (FA + EN) — Bob expands it himself by learning.
_SEED_EMOTION_WORDS = {
    "happy": ["happy", "خوشحال", "خوب", "عالی", "خنده", "haha", "lol", "fun",
              "great", "nice", "awesome", "شاد", "مرسی", "ممنون", "😂", "😊", "🎉", "😄"],
    "sad": ["sad", "غمگین", "گریه", "تنها", "خسته", "بد", "درد", "متاسف",
            "cry", "alone", "tired", "sorry", "😢", "😭", "💔", "😔"],
    "angry": ["angry", "عصبانی", "متنفر", "احمق", "خفه", "hate", "stupid",
              "mad", "damn", "بسه", "😤", "😡", "🤬"],
    "afraid": ["afraid", "ترس", "وحشت", "خطر", "نگران", "استرس", "scared",
               "fear", "worried", "stress", "😱", "😨"],
    "love": ["love", "عشق", "عزیزم", "قلب", "بغل", "عاشق", "جونم",
             "darling", "heart", "kiss", "😍", "🥰", "❤️", "💕"],
}

_STOPWORDS = {
    # EN
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and",
    "or", "in", "on", "at", "it", "i", "you", "he", "she", "we", "they",
    "me", "my", "your", "his", "her", "our", "this", "that", "with", "for",
    "not", "no", "do", "does", "did", "have", "has", "had", "but", "so",
    "what", "who", "when", "where", "why", "how", "can", "will", "would",
    # FA
    "و", "در", "به", "از", "که", "با", "را", "این", "آن", "هم", "یه", "یک",
    "من", "تو", "ما", "اون", "رو", "هست", "نیست", "می", "بود", "شد",
    "چی", "چرا", "کجا", "اگه", "ولی", "اما", "پس", "تا", "بی", "بر",
}

_FA_CHARS = re.compile(r'[؀-ۿ]')
_BOB_MENTION = re.compile(r'\bbob\b|باب', re.IGNORECASE)

# Mood vocabulary: how Bob describes his own feeling in /bobstats and reply shading
_MOOD_FLAVOR = {
    "happy":  {"fa": ["😄", "😁", "✨"], "en": ["😄", "😁", "✨"]},
    "sad":    {"fa": ["😔", "🥀"], "en": ["😔", "🥀"]},
    "angry":  {"fa": ["😤", "💢"], "en": ["😤", "💢"]},
    "afraid": {"fa": ["😳", "🫣"], "en": ["😳", "🫣"]},
    "love":   {"fa": ["🥰", "💙"], "en": ["🥰", "💙"]},
    "neutral": {"fa": ["🤖"], "en": ["🤖"]},
}

_MOOD_NAMES = {
    "fa": {"happy": "خوشحال", "sad": "غمگین", "angry": "عصبانی",
           "afraid": "نگران", "love": "عاشق", "neutral": "آروم"},
    "en": {"happy": "happy", "sad": "sad", "angry": "annoyed",
           "afraid": "anxious", "love": "loving", "neutral": "calm"},
}

_TOO_YOUNG = {
    "fa": "🤖 باب هنوز بچه‌ست و داره از حرفای گروه یاد می‌گیره... یکم دیگه باهاش حرف بزنید بزرگ شه! 🍼",
    "en": "🤖 Bob is still a baby, learning from the group chat... keep talking so he grows up! 🍼",
}

_NO_IDEA = {
    "fa": ["هنوز اینو یاد نگرفتم 🤔 ولی دارم گوش میدم...",
           "بذار بیشتر یاد بگیرم بعد جوابتو میدم 🧠",
           "اینو نمیدونم... ولی یادم میمونه 📝"],
    "en": ["I haven't learned that yet 🤔 but I'm listening...",
           "Let me learn a bit more, then I'll answer 🧠",
           "I don't know that... but I'll remember 📝"],
}


# ═══════════════════════════════════════════════════
# BRAIN: load / init / persist
# ═══════════════════════════════════════════════════

_brain: dict | None = None
_dirty_count = 0

# Per-chat short-term memory (in-RAM only): last message per chat for pair learning
_last_msg: dict[int, str] = {}


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
        "chain": {},          # "w1 w2" -> {next_word: count}
        "starters": {},       # "w1 w2" -> count  (message-opening bigrams)
        "pairs": {},          # keyword -> [{"r": reply, "e": emotion, "n": count}]
        "word_emotion": emo,  # word -> emotion
        "vocab": {},          # word -> frequency
        "mood": {"valence": 0.0, "label": "neutral", "updated": _now_ts()},
        "auto_log": {},       # chat_id -> {"date": "YYYY-MM-DD", "count": n}
        "stats": {"seen": 0, "replies": 0, "born": _now_ts()},
    }


def _get_brain() -> dict:
    """Load (or init) Bob's brain. Call with _lock held."""
    global _brain
    if _brain is None:
        stored = load_bob()
        _brain = stored if stored else _default_brain()
        # forward-compat: fill any missing keys
        for k, v in _default_brain().items():
            _brain.setdefault(k, v)
    return _brain


def _mark_dirty(force: bool = False):
    """Persist the brain every _SAVE_EVERY learned messages. Call with _lock held."""
    global _dirty_count
    _dirty_count += 1
    if force or _dirty_count >= _SAVE_EVERY:
        _dirty_count = 0
        try:
            save_bob(_brain)
        except Exception as e:
            logger.warning("Bob brain save failed: %s", e)


# ═══════════════════════════════════════════════════
# TEXT UTILS
# ═══════════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\s؀-ۿ\U0001F000-\U0001FAFF❤️]', ' ', text)
    return [w for w in text.lower().split() if w]


def _keywords(words: list[str]) -> list[str]:
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]


def _is_farsi(text: str) -> bool:
    return bool(_FA_CHARS.search(text))


def _detect_emotion(words: list[str], brain: dict) -> str:
    counts = {e: 0 for e in EMOTIONS}
    for w in words:
        e = brain["word_emotion"].get(w)
        if e in counts:
            counts[e] += 1
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "neutral"


# ═══════════════════════════════════════════════════
# LEARNING  (Bob's inheritance, improved)
# ═══════════════════════════════════════════════════

def _prune(table: dict, cap: int, keep_ratio: float = 0.8):
    """Drop the least-frequent entries when a table outgrows its cap."""
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


def learn_message(chat_id: int, text: str):
    """Learn one chat message: chains, starters, vocab, emotions, reply pairs."""
    words = _tokenize(text)
    if len(words) < _MIN_WORDS_TO_LEARN:
        return

    with _lock:
        brain = _get_brain()

        # 1) vocab frequencies (for relevance scoring)
        for w in words:
            brain["vocab"][w] = brain["vocab"].get(w, 0) + 1

        # 2) trigram chain + starters (from Markov, his father)
        if len(words) >= 3:
            key0 = f"{words[0]} {words[1]}"
            brain["starters"][key0] = brain["starters"].get(key0, 0) + 1
            for i in range(len(words) - 2):
                key = f"{words[i]} {words[i+1]}"
                nxt = brain["chain"].setdefault(key, {})
                nxt[words[i + 2]] = nxt.get(words[i + 2], 0) + 1

        # 3) emotion learning (from Ophelia, his mother):
        #    unknown words absorb the emotion of the message they appear in
        emotion = _detect_emotion(words, brain)
        if emotion != "neutral" and len(brain["word_emotion"]) < _MAX_EMO_WORDS:
            for w in _keywords(words):
                if w not in brain["word_emotion"]:
                    brain["word_emotion"][w] = emotion

        # 4) conversation-flow pairs: previous message -> this actual human reply
        prev = _last_msg.get(chat_id)
        if prev and prev != text:
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

        # 5) mood drift (Bob "feels" the room) with time decay toward neutral
        mood = brain["mood"]
        elapsed = _now_ts() - mood.get("updated", _now_ts())
        mood["valence"] *= math.exp(-elapsed / 3600.0)  # 1h half-life-ish decay
        shift = {"happy": 0.15, "love": 0.2, "sad": -0.15,
                 "angry": -0.2, "afraid": -0.1}.get(emotion, 0.0)
        mood["valence"] = max(-1.0, min(1.0, mood["valence"] + shift))
        if emotion != "neutral":
            mood["label"] = emotion
        elif abs(mood["valence"]) < 0.1:
            mood["label"] = "neutral"
        mood["updated"] = _now_ts()

        # 6) stats + self-pruning + periodic persist
        brain["stats"]["seen"] += 1
        if brain["stats"]["seen"] % 500 == 0:
            _prune(brain["chain"], _MAX_CHAIN_KEYS)
            _prune(brain["starters"], _MAX_CHAIN_KEYS // 10)
            _prune(brain["pairs"], _MAX_PAIR_KEYS)
            _prune(brain["vocab"], _MAX_VOCAB)
        _mark_dirty()


# ═══════════════════════════════════════════════════
# GENERATION + SCORING  (what makes Bob brilliant)
# ═══════════════════════════════════════════════════

def _rarity(brain: dict, word: str) -> float:
    """Rarer words carry more meaning (cheap IDF)."""
    total = max(1, brain["stats"]["seen"])
    freq = brain["vocab"].get(word, 1)
    return math.log(1 + total / freq)


def _pick_next(options: dict, temperature: float = 1.0) -> str | None:
    """Weighted choice over next-word counts (frequency-aware, not uniform-random)."""
    if not options:
        return None
    words = list(options.keys())
    weights = [options[w] ** (1.0 / max(0.1, temperature)) for w in words]
    return random.choices(words, weights=weights, k=1)[0]


def _generate_from_seed(brain: dict, seed_key: str) -> str | None:
    """Walk the trigram chain from a seed bigram."""
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
        if len(out) >= 6 and random.random() < 0.18:  # natural stop
            break
    return " ".join(out) if len(out) >= 3 else None


def _seed_keys_for(brain: dict, words: list[str]) -> list[str]:
    """Find chain seeds related to the input: its bigrams, then keyword-containing keys."""
    chain = brain["chain"]
    seeds = []
    for i in range(len(words) - 1):
        key = f"{words[i]} {words[i+1]}"
        if key in chain:
            seeds.append(key)
    if len(seeds) < 3:
        kws = set(_keywords(words))
        if kws:
            # bounded scan for keyword-anchored seeds
            for key in list(chain.keys())[:20_000]:
                k1, _, k2 = key.partition(" ")
                if k1 in kws or k2 in kws:
                    seeds.append(key)
                    if len(seeds) >= 10:
                        break
    return seeds


def _score_candidate(brain: dict, cand: str, input_kws: set, input_emotion: str) -> float:
    """Bob's judgement: is this reply relevant, coherent, emotionally fitting?"""
    words = _tokenize(cand)
    if not words:
        return -1.0
    kws = set(_keywords(words))

    # Relevance: rarity-weighted keyword overlap with the input
    overlap = sum(_rarity(brain, w) for w in kws & input_kws)
    relevance = overlap / (1 + len(input_kws)) if input_kws else 0.3

    # Echo penalty: repeating the question back is not an answer
    echo = len(kws & input_kws) / len(kws) if kws else 1.0
    echo_pen = 1.5 if echo > 0.8 else 0.0

    # Coherence: fraction of the reply's transitions Bob has actually seen
    seen = 0
    for i in range(len(words) - 2):
        if words[i + 2] in brain["chain"].get(f"{words[i]} {words[i+1]}", {}):
            seen += 1
    coherence = seen / max(1, len(words) - 2)

    # Emotion fit with the input (and Bob's own mood)
    cand_emotion = _detect_emotion(words, brain)
    mood_label = brain["mood"]["label"]
    emo_fit = 0.5
    if input_emotion != "neutral" and cand_emotion == input_emotion:
        emo_fit = 1.0
    elif cand_emotion == mood_label:
        emo_fit = 0.8

    # Length sanity: 3..18 words feels human
    n = len(words)
    length_fit = 1.0 if 3 <= n <= 18 else 0.4

    return (2.2 * relevance) + (1.6 * coherence) + (0.8 * emo_fit) + (0.6 * length_fit) - echo_pen


def _think(brain: dict, text: str) -> str | None:
    """Bob's full thought process: gather candidates, judge them, answer."""
    words = _tokenize(text)
    input_kws = set(_keywords(words))
    input_emotion = _detect_emotion(words, brain)

    candidates: list[str] = []

    # a) learned real-human replies to similar stimuli (mother's gift, judged not blurted)
    for kw in input_kws:
        for item in brain["pairs"].get(kw, []):
            candidates.append(item["r"])

    # b) generated speech seeded by the input (father's gift, seeded not random)
    seeds = _seed_keys_for(brain, words)
    random.shuffle(seeds)
    for seed in seeds[:_GEN_CANDIDATES]:
        gen = _generate_from_seed(brain, seed)
        if gen:
            candidates.append(gen)

    # c) a couple of free thoughts from popular starters (keeps Bob from silence)
    starters = list(brain["starters"].keys())
    if starters:
        for _ in range(2):
            gen = _generate_from_seed(brain, random.choice(starters))
            if gen:
                candidates.append(gen)

    if not candidates:
        return None

    scored = [(_score_candidate(brain, c, input_kws, input_emotion), c) for c in set(candidates)]
    scored.sort(reverse=True)
    best_score, best = scored[0]
    if best_score < 0.8:  # Bob refuses to say something irrelevant
        return None
    return best


def _flavor(brain: dict, reply: str, lang: str) -> str:
    """Shade the reply with Bob's current feeling."""
    label = brain["mood"]["label"]
    if random.random() < 0.5:
        emo = random.choice(_MOOD_FLAVOR.get(label, _MOOD_FLAVOR["neutral"]).get(lang, ["🤖"]))
        return f"{reply} {emo}"
    return reply


# ═══════════════════════════════════════════════════
# TELEGRAM HANDLERS
# ═══════════════════════════════════════════════════

async def bob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bob [message] — talk to Bob."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    lang = "fa" if get_lang(chat_id) == "fa" else "en"

    text = " ".join(context.args) if context.args else ""
    if not text and update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    if not text:
        text = "سلام" if lang == "fa" else "hello"

    with _lock:
        brain = _get_brain()
        if brain["stats"]["seen"] < _MIN_BRAIN_TO_SPEAK:
            await update.message.reply_text(_TOO_YOUNG[lang])
            return
        reply = _think(brain, text)
        if reply:
            brain["stats"]["replies"] += 1
            reply = _flavor(brain, reply, lang)
            _mark_dirty()
    if reply:
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(random.choice(_NO_IDEA[lang]))


async def bobstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bobstats — Bob's brain report + how he 'feels'."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    lang = "fa" if get_lang(chat_id) == "fa" else "en"

    with _lock:
        brain = _get_brain()
        seen = brain["stats"]["seen"]
        replies = brain["stats"]["replies"]
        vocab = len(brain["vocab"])
        contexts = len(brain["chain"])
        pairs = sum(len(v) for v in brain["pairs"].values())
        emo_words = len(brain["word_emotion"])
        valence = brain["mood"]["valence"]
        label = brain["mood"]["label"]
        age_days = max(0, (_now_ts() - brain["stats"].get("born", _now_ts())) / 86400)

    mood_name = _MOOD_NAMES[lang].get(label, label)
    bar_pos = int((valence + 1) / 2 * 10)
    mood_bar = "▱" * bar_pos + "●" + "▱" * (10 - bar_pos)

    if lang == "fa":
        msg = (
            "🤖 *باب — پسر مارکوف و اوفلیا*\n\n"
            f"🧠 پیام‌هایی که ازشون یاد گرفته: *{seen:,}*\n"
            f"📚 کلمه‌هایی که بلده: *{vocab:,}*\n"
            f"🔗 الگوهای جمله‌سازی: *{contexts:,}*\n"
            f"💬 جواب‌های واقعی که حفظ کرده: *{pairs:,}*\n"
            f"🎭 کلمه‌های احساسی: *{emo_words:,}*\n"
            f"🗣 جواب‌هایی که داده: *{replies:,}*\n"
            f"🎂 سن: *{age_days:.1f}* روز\n\n"
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
            f"🗣 Replies given: *{replies:,}*\n"
            f"🎂 Age: *{age_days:.1f}* days\n\n"
            f"💙 Bob feels: *{mood_name}*\n"
            f"😞 {mood_bar} 😊"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def bob_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Passive listener: Bob always learns; speaks unprompted only 2-3x/day per chat."""
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    if not user or user.is_bot:
        return
    text = update.message.text
    if text.startswith('/'):
        return

    chat_id = update.effective_chat.id
    learn_message(chat_id, text)

    # ── Spontaneous reply, hard-capped per day ──
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    mentioned = bool(_BOB_MENTION.search(text))
    chance = _AUTO_REPLY_MENTION_CHANCE if mentioned else _AUTO_REPLY_BASE_CHANCE
    if random.random() >= chance:
        return

    with _lock:
        brain = _get_brain()
        if brain["stats"]["seen"] < _MIN_BRAIN_TO_SPEAK:
            return
        log = brain["auto_log"].setdefault(str(chat_id), {"date": _today(), "count": 0})
        if log["date"] != _today():
            log["date"] = _today()
            log["count"] = 0
        if log["count"] >= BOB_MAX_AUTO_REPLIES_PER_DAY:
            return
        reply = _think(brain, text)
        if not reply:
            return
        log["count"] += 1
        brain["stats"]["replies"] += 1
        lang = "fa" if get_lang(chat_id) == "fa" else "en"
        reply = _flavor(brain, reply, lang)
        _mark_dirty(force=True)  # persist the daily counter immediately

    try:
        await update.message.reply_text(reply)
    except Exception as e:
        logger.warning("Bob auto-reply failed: %s", e)
