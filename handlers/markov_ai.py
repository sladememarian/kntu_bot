# ==========================================
# KNTU Bot 25 — Markov Chain "Dumb AI" (/ai2)
# Learns from all messages in all topics,
# generates responses mimicking the group's style.
# Deep context-aware system with relevance scoring,
# multi-candidate generation, and GIF responses.
# ==========================================

import random
import re
import threading
import time
import logging
import collections
import hashlib
import aiohttp

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, load_markov, save_markov
from strings import STRINGS

logger = logging.getLogger("kntu_bot25.markov")

# ---- Suicide / self-harm keywords ----
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

# ---- In-memory Markov brain ----

_brain_lock = threading.Lock()
_chain: dict = {}  # {"w1 w2": {"w3": count, ...}, ...}  (bigram)
_trigram: dict = {}  # {"w1 w2 w3": {"w4": count, ...}}  (trigram — higher quality)
_dirty = False      # True if chain has unsaved changes
_msg_count = 0      # messages since last save
_SAVE_EVERY = 25    # save to DB every N messages
_MIN_WORDS = 3      # minimum words in a message to learn from

# ---- Context window — track last N messages per chat ----
_CONTEXT_SIZE = 15  # messages to remember per chat
_chat_context: dict[int, collections.deque] = {}  # chat_id -> deque of messages
_context_lock = threading.Lock()

# ---- Word frequency for TF-IDF scoring ----
_word_freq: dict[str, int] = {}  # global word frequency for IDF weighting
_total_docs = 0  # total messages learned

# ---- Question patterns ----
_QUESTION_WORDS_FA = {"چرا", "کی", "کجا", "چطور", "چگونه", "آیا", "مگه", "مگر", "چه", "چی", "کدوم", "کدام"}
_QUESTION_WORDS_EN = {"what", "why", "how", "when", "where", "who", "which", "is", "are", "do", "does", "can", "will", "would", "should"}

# ---- GIF keywords for mood-based responses ----
_GIF_TRIGGERS = {
    "fa": {
        "خنده": "laughing", "گریه": "crying", "عصبانی": "angry", "رقص": "dancing",
        "عشق": "love", "خوشحال": "happy", "غمگین": "sad", "تبریک": "congratulations",
        "سلام": "hello wave", "خداحافظ": "goodbye", "ممنون": "thank you",
        "بخور": "eating", "خوابم": "sleepy", "خسته": "tired",
    },
    "en": {
        "laugh": "laughing", "cry": "crying", "angry": "angry", "dance": "dancing",
        "love": "love heart", "happy": "happy celebration", "sad": "sad",
        "congrats": "congratulations", "hello": "hello wave", "bye": "goodbye wave",
        "thanks": "thank you", "eat": "eating food", "sleep": "sleepy", "tired": "tired",
    },
}

# Basic knowledge snippets the bot always knows
_KNOWLEDGE = {
    "fa": [
        "سلام! من یه ربات هوشمندم که از پیام‌های گروه یاد می‌گیرم.",
        "من هر روز باهوش‌تر میشم چون از حرف‌های شما یاد می‌گیرم!",
        "ربات KNTU25 هستم، ساخته شده برای سرگرمی و مدیریت گروه.",
        "بیشتر باهام حرف بزنید تا بهتر جواب بدم!",
        "من از تمام پیام‌های گروه یاد می‌گیرم و سعی می‌کنم شبیه شما حرف بزنم.",
    ],
    "en": [
        "Hi! I'm an AI bot that learns from group messages.",
        "I get smarter every day by learning from your conversations!",
        "I'm KNTU25 bot, built for fun and group management.",
        "Talk to me more so I can give better responses!",
        "I learn from every message in this group and try to speak like you.",
    ],
}


def _load_brain():
    """Load brain from persistent storage on startup."""
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
            logger.info("Markov brain loaded: %d bigram + %d trigram keys.", len(_chain), len(_trigram))
    except Exception as e:
        logger.warning("Failed to load Markov brain: %s", e)


def _save_brain():
    """Persist current brain to storage."""
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


def _clean_text(text: str) -> str:
    """Normalize a message for learning."""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r'/\S+', '', text)
    text = re.sub(r'[#\*_`\[\](){}|~<>]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _add_context(chat_id: int, text: str):
    """Add a message to the chat's context window."""
    with _context_lock:
        if chat_id not in _chat_context:
            _chat_context[chat_id] = collections.deque(maxlen=_CONTEXT_SIZE)
        _chat_context[chat_id].append(text)


def _get_context(chat_id: int) -> list[str]:
    """Get recent messages from a chat."""
    with _context_lock:
        if chat_id not in _chat_context:
            return []
        return list(_chat_context[chat_id])


def _compute_idf(word: str) -> float:
    """Inverse document frequency — rarer words get higher score."""
    if _total_docs == 0:
        return 1.0
    freq = _word_freq.get(word.lower(), 0)
    if freq == 0:
        return 1.0
    import math
    return math.log(1 + _total_docs / (1 + freq))


def _relevance_score(generated: str, seed_words: list[str], context_words: set[str]) -> float:
    """Score how relevant a generated response is to the seed + context."""
    gen_words = set(generated.lower().split())
    score = 0.0

    # Direct seed word overlap (heavily weighted)
    for w in seed_words:
        if w.lower() in gen_words:
            score += 3.0 * _compute_idf(w)

    # Context word overlap (lighter weight)
    for w in context_words:
        if w in gen_words:
            score += 0.5

    # Length penalty: prefer 8-30 word responses
    word_count = len(generated.split())
    if word_count < 4:
        score *= 0.3
    elif word_count < 8:
        score *= 0.7
    elif word_count > 40:
        score *= 0.7

    # Penalty for too much repetition
    gen_list = generated.lower().split()
    unique_ratio = len(set(gen_list)) / max(len(gen_list), 1)
    if unique_ratio < 0.4:
        score *= 0.2

    return score


def _is_question(text: str) -> bool:
    """Detect if text is a question."""
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
    """Check if text matches a GIF trigger keyword and return search term."""
    text_lower = text.lower()
    triggers = _GIF_TRIGGERS.get(lang, _GIF_TRIGGERS["en"])
    for keyword, search_term in triggers.items():
        if keyword in text_lower:
            return search_term
    return None


async def _search_gif(query: str) -> str | None:
    """Search for a GIF URL using Tenor's public search."""
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
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
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


def learn(text: str):
    """Learn from a single message (builds bigram + trigram chains + word freq)."""
    global _dirty, _msg_count, _total_docs

    text = _clean_text(text)
    words = text.split()
    if len(words) < _MIN_WORDS:
        return

    with _brain_lock:
        # Update word frequency for IDF scoring
        seen_words = set()
        for w in words:
            wl = w.lower()
            if wl not in seen_words:
                _word_freq[wl] = _word_freq.get(wl, 0) + 1
                seen_words.add(wl)
        _total_docs += 1

        # Bigram chain (w1 w2 -> w3)
        for i in range(len(words) - 2):
            key = f"{words[i]} {words[i + 1]}"
            nxt = words[i + 2]
            if key not in _chain:
                _chain[key] = {}
            _chain[key][nxt] = _chain[key].get(nxt, 0) + 1

        # Trigram chain (w1 w2 w3 -> w4) — higher quality
        for i in range(len(words) - 3):
            key = f"{words[i]} {words[i + 1]} {words[i + 2]}"
            nxt = words[i + 3]
            if key not in _trigram:
                _trigram[key] = {}
            _trigram[key][nxt] = _trigram[key].get(nxt, 0) + 1

        _dirty = True
        _msg_count += 1

    if _msg_count >= _SAVE_EVERY:
        _msg_count = 0
        _save_brain()


def generate(seed: str | None = None, max_words: int = 40,
             chat_id: int | None = None, num_candidates: int = 5) -> str | None:
    """Generate text with multi-candidate selection and context-aware scoring."""
    with _brain_lock:
        if not _chain:
            return None

        seed_words = _clean_text(seed).split() if seed else []

        # Build context word set from recent chat messages
        context_words = set()
        if chat_id is not None:
            for msg in _get_context(chat_id):
                for w in _clean_text(msg).lower().split():
                    if len(w) > 2:
                        context_words.add(w)

        # Generate multiple candidates and pick the best
        candidates = []
        for _ in range(num_candidates):
            result = _generate_single(seed_words, max_words)
            if result:
                score = _relevance_score(result, seed_words, context_words)
                candidates.append((result, score))

        # For questions, also try generating from question-response patterns
        if seed and _is_question(seed):
            for _ in range(3):
                result = _generate_answer_attempt(seed_words, max_words)
                if result:
                    score = _relevance_score(result, seed_words, context_words) * 1.5
                    candidates.append((result, score))

        if not candidates:
            return None

        # Sort by relevance score and pick from top candidates with some randomness
        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:max(2, len(candidates) // 2)]
        return random.choice(top)[0]


def _generate_single(seed_words: list[str], max_words: int) -> str | None:
    """Generate a single candidate response."""
    if not _chain:
        return None

    # Try to match seed with decreasing specificity
    if seed_words:
        # Try trigram match (best quality)
        if len(seed_words) >= 3 and _trigram:
            for i in range(len(seed_words) - 2):
                key = f"{seed_words[i]} {seed_words[i + 1]} {seed_words[i + 2]}"
                if key in _trigram:
                    return _walk_tri(key, max_words)

        # Try bigram match
        for i in range(len(seed_words) - 1):
            key = f"{seed_words[i]} {seed_words[i + 1]}"
            if key in _chain:
                return _walk(key, max_words)

        # Try weighted single-word match (prefer rarer words — higher IDF)
        word_scores = []
        for w in seed_words:
            if len(w) > 2:
                idf = _compute_idf(w)
                word_scores.append((w, idf))
        word_scores.sort(key=lambda x: x[1], reverse=True)

        for w, _ in word_scores[:5]:
            if _trigram:
                tri_matches = [k for k in _trigram if w in k.split()]
                if tri_matches:
                    return _walk_tri(random.choice(tri_matches), max_words)
            matches = [k for k in _chain if w in k.split()]
            if matches:
                return _walk(random.choice(matches), max_words)

    # Random start — prefer trigram
    if _trigram and random.random() < 0.7:
        return _walk_tri(random.choice(list(_trigram.keys())), max_words)

    return _walk(random.choice(list(_chain.keys())), max_words)


def _generate_answer_attempt(seed_words: list[str], max_words: int) -> str | None:
    """Try to generate an answer-like response by finding keys that follow question patterns."""
    # Look for keys that contain content words from the question (skip question words)
    content_words = [w for w in seed_words
                     if w.lower() not in _QUESTION_WORDS_EN and w not in _QUESTION_WORDS_FA
                     and len(w) > 2]
    if not content_words:
        return None

    # Find chains that discuss the same topic
    best_key = None
    best_idf = 0

    for w in content_words:
        idf = _compute_idf(w)
        if _trigram:
            for k in _trigram:
                if w in k.split():
                    if idf > best_idf:
                        best_idf = idf
                        best_key = ("tri", k)
                    break
        for k in _chain:
            if w in k.split():
                if idf > best_idf and best_key is None:
                    best_idf = idf
                    best_key = ("bi", k)
                break

    if best_key:
        kind, key = best_key
        if kind == "tri":
            return _walk_tri(key, max_words)
        return _walk(key, max_words)
    return None


def _walk(start_key: str, max_words: int) -> str:
    """Random walk through the bigram chain."""
    words = start_key.split()
    for _ in range(max_words):
        key = f"{words[-2]} {words[-1]}"
        if key not in _chain:
            break
        nexts = _chain[key]
        total = sum(nexts.values())
        r = random.randint(1, total)
        cumulative = 0
        chosen = None
        for word, count in nexts.items():
            cumulative += count
            if cumulative >= r:
                chosen = word
                break
        if chosen is None:
            break
        words.append(chosen)
        if chosen.endswith(('.', '!', '?', '؟')) and len(words) > 6:
            if random.random() < 0.5:
                break
    return " ".join(words)


def _walk_tri(start_key: str, max_words: int) -> str:
    """Random walk through the trigram chain (higher quality)."""
    words = start_key.split()
    for _ in range(max_words):
        tri_key = f"{words[-3]} {words[-2]} {words[-1]}" if len(words) >= 3 else None
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
        cumulative = 0
        chosen = None
        for word, count in nexts.items():
            cumulative += count
            if cumulative >= r:
                chosen = word
                break
        if chosen is None:
            break
        words.append(chosen)
        if chosen.endswith(('.', '!', '?', '؟')) and len(words) > 6:
            if random.random() < 0.5:
                break
    return " ".join(words)


def get_brain_stats() -> tuple[int, int, int]:
    """Return (num_keys, total_transitions, vocabulary_size)."""
    with _brain_lock:
        keys = len(_chain) + len(_trigram)
        transitions = (sum(sum(v.values()) for v in _chain.values()) +
                       sum(sum(v.values()) for v in _trigram.values()))
        vocab = len(_word_freq)
        return keys, transitions, vocab


# ---- Load brain on import ----
_load_brain()


# ---- Telegram handler: learn from all messages ----

async def markov_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently learn from every text message in the group."""
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if text.startswith('/'):
        return

    # Suicide / self-harm detection — respond supportively, don't learn
    if _SUICIDE_PATTERN.search(text):
        lang = get_lang(update.effective_chat.id)
        support = _SUPPORT_MSG_FA if lang == "fa" else _SUPPORT_MSG_EN
        await update.message.reply_text(support, parse_mode="Markdown")
        return

    # Add to context window
    _add_context(update.effective_chat.id, text)
    learn(text)


# ---- /ai2 command ----

async def ai2_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    # Use args or replied-to message as seed
    seed = None
    if context.args:
        seed = " ".join(context.args)
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        seed = update.message.reply_to_message.text

    keys, transitions, vocab = get_brain_stats()

    if keys < 10:
        result = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))
        await update.message.reply_text(f"🧪 {result}")
        return

    # Check if a GIF response is appropriate (20% chance if trigger found)
    if seed and random.random() < 0.2:
        gif_query = _detect_gif_trigger(seed, lang)
        if gif_query:
            gif_url = await _search_gif(gif_query)
            if gif_url:
                # Send GIF + text response
                result = generate(seed, max_words=25, chat_id=chat.id, num_candidates=3)
                if result:
                    await update.message.reply_text(f"🧪 {result}")
                await update.message.reply_animation(animation=gif_url)
                return

    result = generate(seed, max_words=45, chat_id=chat.id, num_candidates=6)
    if not result:
        result = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))

    # For questions, add a question-answering prefix sometimes
    if seed and _is_question(seed) and random.random() < 0.3:
        prefix = "🤔 " if lang == "en" else "🤔 "
        await update.message.reply_text(f"{prefix}{result}")
    else:
        await update.message.reply_text(f"🧪 {result}")


# ---- /ai2stats command (admin) ----

async def ai2stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    s = STRINGS[lang]

    keys, transitions, vocab = get_brain_stats()
    ctx_chats = len(_chat_context)
    if lang == "fa":
        text = (
            f"🧠 *آمار هوش مصنوعی مارکوف*\n\n"
            f"🔑 کلیدها: *{keys:,}*\n"
            f"🔗 انتقال‌ها: *{transitions:,}*\n"
            f"📚 واژگان: *{vocab:,}*\n"
            f"💬 چت‌های فعال: *{ctx_chats}*\n"
            f"📄 کل پیام‌ها: *{_total_docs:,}*"
        )
    else:
        text = (
            f"🧠 *Markov AI Stats*\n\n"
            f"🔑 Keys: *{keys:,}*\n"
            f"🔗 Transitions: *{transitions:,}*\n"
            f"📚 Vocabulary: *{vocab:,}*\n"
            f"💬 Active chats: *{ctx_chats}*\n"
            f"📄 Total messages: *{_total_docs:,}*"
        )
    await update.message.reply_text(text, parse_mode="Markdown")
