# ==========================================
# KNTU Bot 25 — BOB 🤖 (/bob)
# Public name: Bob  |  Brain: REAL Hermes Agent (NousResearch)
#
#   /bob [text]   — talk to Bob
#   /bobstats     — Hermes engine / provider / session report
#   /bob reset    — clear this chat's memory
#   /bob ping     — admin: live Hermes ping
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
    hermes_available,
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
    try:
        brain = load_bob() or {}
    except Exception:
        brain = {}
    stats = brain.get("stats") or {}
    return {
        "legacy_seen": stats.get("seen", 0),
        "legacy_replies": stats.get("replies", 0),
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
        brain["engine"] = "hermes_native"
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


def _help(lang: str) -> str:
    if lang == "fa":
        return (
            "🤖 *باب — مغز Hermes (واقعی)*\n"
            "`/bob <متن>` — حرف بزن\n"
            "`/bob reset` — پاک کردن حافظهٔ این چت\n"
            "`/bobstats` — وضعیت موتور هرمس\n"
            "ادمین: `/bob ping`"
        )
    return (
        "🤖 *Bob — real Hermes Agent brain*\n"
        "`/bob <text>` — chat\n"
        "`/bob reset` — clear this chat memory\n"
        "`/bobstats` — Hermes engine status\n"
        "Admin: `/bob ping`"
    )


async def bob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(_help(lang), parse_mode="Markdown")
        return

    low = raw.strip().lower()
    if low in {"reset", "clear", "پاک", "ریست"}:
        ok = clear_history(chat_id, user.id if user else 0)
        msg = (
            ("🧠 حافظه پاک شد." if ok else "🧠 چیزی ذخیره نشده بود.")
            if lang == "fa"
            else ("🧠 memory wiped." if ok else "🧠 nothing stored yet.")
        )
        await update.message.reply_text(msg)
        return

    if low in {"ping", "health"} and _is_admin(user.id if user else None):
        await update.message.reply_text("⏳ probing real Hermes AIAgent…")
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(_executor, ping_providers)
        lines = []
        for r in results:
            mark = "✅" if r.get("ok") else "❌"
            lines.append(
                f"{mark} {r.get('provider')} / {r.get('model')}: "
                f"{r.get('sample') or r.get('error')}"
            )
        await update.message.reply_text("\n".join(lines) or "no result")
        return

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
    if len(reply) > 4000:
        reply = reply[:3990] + "…"
    await update.message.reply_text(reply)


def _md_escape(text: str) -> str:
    """Escape underscores for Telegram Markdown V1 (inside bold/outside backtick)."""
    return str(text).replace("_", "\\_")


async def bobstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    lang = "fa" if get_lang(chat_id) == "fa" else "en"

    try:
        hs = hermes_stats()
        legacy = _legacy_brain_snapshot()
        providers = hs.get("providers") or []
        prov_lines = [
            f"• *{_md_escape(p['name'])}* — `{', '.join(p['models'][:3])}` (keys:{p['keys']})"
            + (f" ⚠️ {p['note']}" if p.get("note") else "")
            for p in providers
        ] or ["• _no providers configured_"]

        import_ok = "✅" if hs.get("hermes_import_ok") else "❌ NOT LOADED"
        soul_ok = "✅" if hs.get("soul_loaded") else "⚠️ missing"
        memory_ok = "✅ enabled" if hs.get("memory_enabled") else "❌ disabled"
        age = hs.get("age_days", 0.0)
        tools = hs.get("toolsets")
        if tools and isinstance(tools[0], str) and tools[0].startswith("ALL"):
            tools_s = tools[0]
        else:
            tools_s = ", ".join(tools[:8]) if tools else "default"
            if tools and len(tools) > 8:
                tools_s += f" +{len(tools)-8} more"
        pool = hs.get("agent_pool_size", 0)

        # Model health info
        health = hs.get("model_health") or {}
        last_working = hs.get("last_working_model", "—")
        health_lines = []
        for mname, mh in health.items():
            status = "✅" if mh.get("healthy") else "❌ cooldown"
            failures = mh.get("failures", 0)
            health_lines.append(f"  `{mname}` {status} (fails:{failures})")
        health_s = "\n".join(health_lines) if health_lines else "  no data yet"

        if lang == "fa":
            msg = (
                "🤖 *باب — موتور Hermes واقعی (NousResearch)*\n\n"
                f"🧠 AIAgent import: {import_ok}\n"
                f"📡 مدل فعال: `{hs.get('model') or '—'}`\n"
                f"🔄 fallback: `{hs.get('fallback_model') or '—'}`\n"
                f"🔗 base: `{hs.get('base_url') or '—'}`\n"
                f"🛠 tools ({len(tools or [])}): `{tools_s}`\n"
                f"🧠 حافظه: {memory_ok}\n"
                f"💬 calls: *{hs.get('calls', 0)}* · errors: *{hs.get('errors', 0)}*\n"
                f"🗂 sessions: *{hs.get('sessions', session_count())}*\n"
                f"♻️ agent pool: *{pool}*\n"
                f"📜 SOUL.md: {soul_ok}\n"
                f"🎂 age: *{age:.1f}*d\n"
                f"📁 HERMES\\_HOME: `{hs.get('hermes_home') or '—'}`\n\n"
                f"*Model Health:*\n  last working: `{last_working}`\n{health_s}\n\n"
                f"*Providers:*\n" + "\n".join(prov_lines) + "\n\n"
                f"legacy: seen={legacy['legacy_seen']}, replies={legacy['legacy_replies']}"
            )
        else:
            msg = (
                "🤖 *Bob — real Hermes Agent (NousResearch)*\n\n"
                f"🧠 AIAgent import: {import_ok}\n"
                f"📡 Active model: `{hs.get('model') or '—'}`\n"
                f"🔄 Fallback: `{hs.get('fallback_model') or '—'}`\n"
                f"🔗 Base: `{hs.get('base_url') or '—'}`\n"
                f"🛠 Tools ({len(tools or [])}): `{tools_s}`\n"
                f"🧠 Memory: {memory_ok}\n"
                f"💬 Calls: *{hs.get('calls', 0)}* · Errors: *{hs.get('errors', 0)}*\n"
                f"🗂 Sessions: *{hs.get('sessions', session_count())}*\n"
                f"♻️ Agent pool: *{pool}*\n"
                f"📜 SOUL.md: {soul_ok}\n"
                f"🎂 Age: *{age:.1f}*d\n"
                f"📁 HERMES\\_HOME: `{hs.get('hermes_home') or '—'}`\n\n"
                f"*Model Health:*\n  last working: `{last_working}`\n{health_s}\n\n"
                f"*Providers:*\n" + "\n".join(prov_lines) + "\n\n"
                f"legacy: seen={legacy['legacy_seen']}, replies={legacy['legacy_replies']}"
            )
        try:
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            plain = msg.replace("*", "").replace("`", "").replace("_", "").replace("\\", "")
            try:
                await update.message.reply_text(plain)
            except Exception as e2:
                logger.error("bobstats reply failed: %s", e2)
                await update.message.reply_text(f"❌ bobstats error: {e2}")
    except Exception as e:
        logger.exception("bobstats build failed")
        await update.message.reply_text(f"❌ bobstats error: {e}")


async def bob_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
