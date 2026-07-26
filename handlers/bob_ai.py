# ==========================================
# KNTU Bot 25 — BOB 🤖 (/bob)
# Public name: Bob  |  Brain: Hermes-style agent
#
# Commands (unchanged for users):
#   /bob [text]   — talk to Bob (Hermes brain)
#   /bobstats     — brain / provider / session report
# Passive listen        — optional light auto-replies when mentioned
# ==========================================

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang, load_bob, save_bob

try:
    from config import ADMIN_IDS
except Exception:  # pragma: no cover
    ADMIN_IDS = []

from handlers.hermes_brain import (
    chat as hermes_chat,
    clear_history,
    get_stats as hermes_stats,
    load_soul,
    ping_providers,
    session_count,
)

logger = logging.getLogger("kntu_bot25.bob")

_executor = ThreadPoolExecutor(max_workers=int(os.environ.get("BOB_WORKERS") or "4"))

_BOB_MENTION = re.compile(r"\bbob\b|باب", re.IGNORECASE)
_FA_CHARS = re.compile(r"[\u0600-\u06ff]")

BOB_MAX_AUTO_REPLIES_PER_DAY = int(os.environ.get("BOB_MAX_AUTO_REPLIES_PER_DAY") or "3")
_AUTO_REPLY_MENTION_CHANCE = float(os.environ.get("BOB_AUTO_MENTION_CHANCE") or "0.35")
_AUTO_REPLY_BASE_CHANCE = float(os.environ.get("BOB_AUTO_BASE_CHANCE") or "0.0")

# in-RAM auto-reply counters: chat_id -> {date, count}
_auto_log: dict[str, dict] = {}
_meta_lock = __import__("threading").Lock()


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _is_farsi(text: str) -> bool:
    return bool(_FA_CHARS.search(text or ""))


def _reply_lang(text: str, chat_lang: str) -> str:
    if text and _is_farsi(text):
        return "fa"
    if text and re.search(r"[A-Za-z]", text) and not _is_farsi(text):
        return "en"
    return "fa" if chat_lang == "fa" else "en"


def _is_admin(uid: int | None) -> bool:
    return bool(uid) and int(uid) in set(ADMIN_IDS or [])


def _legacy_brain_snapshot() -> dict:
    """Keep optional legacy bob_brain stats for continuity in /bobstats."""
    try:
        brain = load_bob() or {}
    except Exception:
        brain = {}
    stats = brain.get("stats") or {}
    return {
        "legacy_seen": stats.get("seen", 0),
        "legacy_replies": stats.get("replies", 0),
        "legacy_born": stats.get("born"),
        "legacy_pairs": sum(len(v) for v in (brain.get("pairs") or {}).values())
        if isinstance(brain.get("pairs"), dict)
        else 0,
    }


def _bump_legacy_reply():
    try:
        brain = load_bob() or {}
        st = brain.setdefault("stats", {})
        st["replies"] = int(st.get("replies") or 0) + 1
        if "born" not in st:
            st["born"] = time.time()
        brain.setdefault("engine", "hermes")
        save_bob(brain)
    except Exception as e:
        logger.debug("legacy reply bump failed: %s", e)


async def _run_hermes(
    *,
    chat_id: int,
    user_id: int,
    text: str,
    lang: str,
    user_name: str,
) -> tuple[str, dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        lambda: hermes_chat(
            chat_id=chat_id,
            user_id=user_id,
            user_text=text,
            lang=lang,
            user_name=user_name,
        ),
    )


def _admin_help(lang: str) -> str:
    if lang == "fa":
        return (
            "🤖 *باب — مغز هرمس*\n"
            "`/bob <متن>` — حرف بزن\n"
            "`/bob reset` — پاک کردن حافظهٔ این چت\n"
            "`/bobstats` — وضعیت مغز و پروایدرها\n"
            "ادمین: `/bob ping` تست اتصال API"
        )
    return (
        "🤖 *Bob — Hermes brain*\n"
        "`/bob <text>` — chat\n"
        "`/bob reset` — clear this chat memory\n"
        "`/bobstats` — brain & provider status\n"
        "Admin: `/bob ping` API connectivity"
    )


async def bob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bob [message] — talk to Bob (Hermes brain)."""
    if not update.message:
        return
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    chat_lang = get_lang(chat_id)
    lang = "fa" if chat_lang == "fa" else "en"

    raw = " ".join(context.args) if context.args else ""
    if not raw and update.message.reply_to_message and update.message.reply_to_message.text:
        raw = update.message.reply_to_message.text

    if not raw:
        await update.message.reply_text(_admin_help(lang), parse_mode="Markdown")
        return

    low = raw.strip().lower()
    if low in {"reset", "clear", "پاک", "ریست"}:
        ok = clear_history(chat_id, user.id if user else 0)
        msg = "🧠 memory wiped." if ok else "🧠 nothing stored yet."
        if lang == "fa":
            msg = "🧠 حافظه پاک شد." if ok else "🧠 چیزی ذخیره نشده بود."
        await update.message.reply_text(msg)
        return

    if low in {"ping", "health"} and _is_admin(user.id if user else None):
        await update.message.reply_text("⏳ probing providers…")
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(_executor, ping_providers)
        lines = []
        for r in results:
            mark = "✅" if r.get("ok") else "❌"
            lines.append(f"{mark} {r.get('provider')} / {r.get('model')}: {r.get('sample') or r.get('error')}")
        await update.message.reply_text("\n".join(lines) or "no providers configured")
        return

    # typing indicator
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    rlang = _reply_lang(raw, lang)
    try:
        reply, meta = await _run_hermes(
            chat_id=chat_id,
            user_id=user.id if user else 0,
            text=raw,
            lang=rlang,
            user_name=(user.first_name if user else "") or "",
        )
    except Exception as e:
        logger.exception("bob hermes failed")
        reply = f"⚠️ brain error: {e}" if lang == "en" else f"⚠️ خطای مغز: {e}"
        meta = {}

    _bump_legacy_reply()

    # Telegram hard limit safety
    if len(reply) > 4000:
        reply = reply[:3990] + "…"

    await update.message.reply_text(reply)


async def bobstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bobstats — Bob brain report (Hermes engine)."""
    if not update.message:
        return
    chat_id = update.effective_chat.id
    lang = "fa" if get_lang(chat_id) == "fa" else "en"

    hs = hermes_stats()
    legacy = _legacy_brain_snapshot()
    providers = hs.get("providers") or []
    prov_lines = []
    for p in providers:
        prov_lines.append(f"• *{p['name']}* — models: `{', '.join(p['models'][:4])}` (keys:{p['keys']})")
    if not prov_lines:
        prov_lines = ["• _no providers configured — set OPENCODE_API_KEYS / NVIDIA_API_KEY_"]

    soul_ok = "✅" if hs.get("soul_loaded") else "⚠️ missing"
    age = hs.get("age_days", 0.0)

    if lang == "fa":
        msg = (
            "🤖 *باب — مغز هرمس (Hermes-style)*\n\n"
            f"🧠 موتور: *hermes*\n"
            f"📡 آخرین پروایدر: *{hs.get('provider_last') or '—'}*\n"
            f"🧩 آخرین مدل: `{hs.get('model_last') or '—'}`\n"
            f"💬 تماس‌ها: *{hs.get('calls', 0)}* · خطاها: *{hs.get('errors', 0)}*\n"
            f"🗂 سشن‌های فعال: *{hs.get('sessions', session_count())}*\n"
            f"📜 SOUL.md: {soul_ok}\n"
            f"🎂 سن پروسه: *{age:.1f}* روز\n\n"
            f"*پروایدرها:*\n" + "\n".join(prov_lines) + "\n\n"
            f"_legacy markov brain (آرشیو): seen={legacy['legacy_seen']}, "
            f"replies={legacy['legacy_replies']}, pairs={legacy['legacy_pairs']}_\n"
            f"HERMES_HOME: `{hs.get('hermes_home') or '—'}`"
        )
    else:
        msg = (
            "🤖 *Bob — Hermes-style brain*\n\n"
            f"🧠 Engine: *hermes*\n"
            f"📡 Last provider: *{hs.get('provider_last') or '—'}*\n"
            f"🧩 Last model: `{hs.get('model_last') or '—'}`\n"
            f"💬 Calls: *{hs.get('calls', 0)}* · errors: *{hs.get('errors', 0)}*\n"
            f"🗂 Sessions: *{hs.get('sessions', session_count())}*\n"
            f"📜 SOUL.md: {soul_ok}\n"
            f"🎂 Process age: *{age:.1f}* days\n\n"
            f"*Providers:*\n" + "\n".join(prov_lines) + "\n\n"
            f"_legacy markov archive: seen={legacy['legacy_seen']}, "
            f"replies={legacy['legacy_replies']}, pairs={legacy['legacy_pairs']}_\n"
            f"HERMES_HOME: `{hs.get('hermes_home') or '—'}`"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def bob_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Optional mention auto-reply via Hermes (rate-limited)."""
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    if not user or user.is_bot:
        return
    text = update.message.text
    if text.startswith("/"):
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    mentioned = bool(_BOB_MENTION.search(text))
    reply_to_bob = bool(
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )
    chance = _AUTO_REPLY_MENTION_CHANCE if (mentioned or reply_to_bob) else _AUTO_REPLY_BASE_CHANCE
    if chance <= 0 or random.random() >= chance:
        return

    key = str(chat.id)
    with _meta_lock:
        log = _auto_log.setdefault(key, {"date": _today(), "count": 0})
        if log["date"] != _today():
            log["date"] = _today()
            log["count"] = 0
        if log["count"] >= BOB_MAX_AUTO_REPLIES_PER_DAY:
            return
        log["count"] += 1

    chat_lang = get_lang(chat.id)
    rlang = _reply_lang(text, chat_lang)
    try:
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        reply, _meta = await _run_hermes(
            chat_id=chat.id,
            user_id=user.id,
            text=text,
            lang=rlang,
            user_name=user.first_name or "",
        )
        _bump_legacy_reply()
        if len(reply) > 4000:
            reply = reply[:3990] + "…"
        await update.message.reply_text(reply)
    except Exception as e:
        logger.warning("Bob auto-reply failed: %s", e)
