# ==========================================
# KNTU Bot 25 — Markov Chain "Dumb AI" (/ai2)
# Learns from all messages in all topics,
# generates responses mimicking the group's style.
# ==========================================

import random
import re
import threading
import time
import logging

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, load_markov, save_markov
from strings import STRINGS

logger = logging.getLogger("kntu_bot25.markov")

# ---- In-memory Markov brain ----

_brain_lock = threading.Lock()
_chain: dict = {}  # {"w1 w2": {"w3": count, ...}, ...}
_dirty = False      # True if chain has unsaved changes
_msg_count = 0      # messages since last save
_SAVE_EVERY = 25    # save to DB every N messages
_MIN_WORDS = 3      # minimum words in a message to learn from


def _load_brain():
    """Load brain from persistent storage on startup."""
    global _chain
    try:
        loaded = load_markov()
        if loaded:
            _chain = loaded
            total_keys = len(_chain)
            logger.info("Markov brain loaded: %d bigram keys.", total_keys)
    except Exception as e:
        logger.warning("Failed to load Markov brain: %s", e)


def _save_brain():
    """Persist current brain to storage."""
    global _dirty
    try:
        with _brain_lock:
            if not _dirty:
                return
            save_markov(_chain)
            _dirty = False
    except Exception as e:
        logger.warning("Failed to save Markov brain: %s", e)


def _clean_text(text: str) -> str:
    """Normalize a message for learning."""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove mentions and commands
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r'/\S+', '', text)
    # Remove excessive punctuation/symbols but keep Persian
    text = re.sub(r'[#\*_`\[\](){}|~<>]', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def learn(text: str):
    """Learn from a single message."""
    global _dirty, _msg_count

    text = _clean_text(text)
    words = text.split()
    if len(words) < _MIN_WORDS:
        return

    with _brain_lock:
        for i in range(len(words) - 2):
            key = f"{words[i]} {words[i + 1]}"
            nxt = words[i + 2]
            if key not in _chain:
                _chain[key] = {}
            _chain[key][nxt] = _chain[key].get(nxt, 0) + 1
        _dirty = True
        _msg_count += 1

    # Periodic save
    if _msg_count >= _SAVE_EVERY:
        _msg_count = 0
        _save_brain()


def generate(seed: str | None = None, max_words: int = 35) -> str | None:
    """Generate text from the Markov chain."""
    with _brain_lock:
        if not _chain:
            return None

        # Try to seed from user input
        if seed:
            seed_words = _clean_text(seed).split()
            # Try to find a matching bigram from the seed
            for i in range(len(seed_words) - 1):
                key = f"{seed_words[i]} {seed_words[i + 1]}"
                if key in _chain:
                    return _walk(key, max_words)
            # Try any key containing a seed word
            for w in reversed(seed_words):
                matches = [k for k in _chain if w in k.split()]
                if matches:
                    return _walk(random.choice(matches), max_words)

        # Random start
        key = random.choice(list(_chain.keys()))
        return _walk(key, max_words)


def _walk(start_key: str, max_words: int) -> str:
    """Random walk through the chain."""
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
        # Natural stop: if we hit sentence-ending punctuation, maybe stop
        if chosen.endswith(('.', '!', '?', '؟')) and len(words) > 6:
            if random.random() < 0.5:
                break
    return " ".join(words)


def get_brain_stats() -> tuple[int, int]:
    """Return (num_bigrams, total_transitions)."""
    with _brain_lock:
        keys = len(_chain)
        transitions = sum(sum(v.values()) for v in _chain.values())
        return keys, transitions


# ---- Load brain on import ----
_load_brain()


# ---- Telegram handler: learn from all messages ----

async def markov_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently learn from every text message in the group."""
    if not update.message or not update.message.text:
        return
    # Skip very short messages and bot commands
    text = update.message.text
    if text.startswith('/'):
        return
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

    keys, transitions = get_brain_stats()

    if keys < 10:
        await update.message.reply_text(s["ai2_not_ready"], parse_mode="Markdown")
        return

    result = generate(seed, max_words=40)
    if not result:
        await update.message.reply_text(s["ai2_not_ready"], parse_mode="Markdown")
        return

    await update.message.reply_text(f"🧪 {result}")


# ---- /ai2stats command (admin) ----

async def ai2stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    s = STRINGS[lang]

    keys, transitions = get_brain_stats()
    text = s["ai2_stats"].format(keys=keys, transitions=transitions)
    await update.message.reply_text(text, parse_mode="Markdown")
