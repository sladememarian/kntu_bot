# ==========================================
# KNTU Bot 25 — AI Agent (Markov-Powered)
#
# Inspired by LangChain agent architecture:
#   Observe → Think → Act → Respond
#
# Uses the Markov brain as the core "reasoning"
# engine with tool-like capabilities:
#   1. Markov Generation (text completion)
#   2. Knowledge Base (built-in facts)
#   3. Humor Engine (jokes, roasts, facts)
#   4. Topic Expert (topic-aware responses)
#   5. Emotion Responder (mood-aware replies)
#   6. Context Memory (recent chat history)
# ==========================================

import random
import re

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang
from strings import STRINGS
from handlers.markov_ai import (
    generate,
    get_brain_stats,
    learn,
    _detect_emotion,
    _detect_topic,
    _is_question,
    _is_farsi,
    _pick_personality,
    _apply_personality,
    _make_chain_joke,
    _make_absurd_fact,
    _should_roast,
    _strategy_topic_reaction,
    _strategy_mashup,
    _strategy_echo_twist,
    _strategy_debate,
    _strategy_reverse_wisdom,
    _get_interesting_words,
    _add_context,
    _get_context,
    _clean_text,
    _KNOWLEDGE,
    _ROASTS,
    _COMEBACKS,
    _TOPIC_REACTIONS,
    _TOPICS,
    _detect_gif_trigger,
    _search_gif,
)


# ═══════════════════════════════════════════════════
# AGENT TOOLS — each "tool" is a function the agent
# can call, similar to LangChain tool pattern
# ═══════════════════════════════════════════════════

def _tool_knowledge(query: str, lang: str) -> str | None:
    """Tool 1: Knowledge base lookup — answers common questions."""
    ql = query.lower()

    # Bot identity questions
    identity_fa = ["تو کی هستی", "اسمت چیه", "چی هستی", "کی ساختت", "معرفی"]
    identity_en = ["who are you", "what are you", "your name", "introduce", "who made"]
    if any(k in ql for k in identity_fa + identity_en):
        if lang == "fa":
            return random.choice([
                "من *KNTU Bot 25* هستم! 🤖 یه ربات هوشمند مارکوف که از پیام‌های گروه یاد می‌گیره.",
                "سلام! من ربات KNTU25 هستم. مغزم از زنجیره مارکوف ساخته شده و هر روز باهوش‌تر میشم! 🧠",
                "من یه هوش مصنوعی مارکوفی هستم. هر چی بیشتر باهام حرف بزنی، بهتر جواب میدم! 🤖✨",
            ])
        return random.choice([
            "I'm *KNTU Bot 25*! 🤖 A Markov-powered AI that learns from group messages.",
            "Hi! I'm KNTU25 bot. My brain is built on Markov chains and I get smarter daily! 🧠",
            "I'm a Markov AI agent. The more you talk to me, the better I respond! 🤖✨",
        ])

    # How it works questions
    how_fa = ["چطور کار میکنی", "چجوری یاد میگیری", "مغزت", "هوشت"]
    how_en = ["how do you work", "how do you learn", "your brain", "your intelligence"]
    if any(k in ql for k in how_fa + how_en):
        keys, trans, vocab = get_brain_stats()
        if lang == "fa":
            return (
                f"🧠 من از *زنجیره مارکوف* استفاده می‌کنم!\n\n"
                f"📊 مغز من الان:\n"
                f"  🔑 {keys:,} الگو\n"
                f"  📚 {vocab:,} واژه\n"
                f"  🔗 {trans:,} اتصال\n\n"
                f"هر پیامی که توی گروه فرستاده میشه رو تحلیل می‌کنم و "
                f"الگوهای جدید یاد می‌گیرم. بعد وقتی سوال می‌پرسی، "
                f"بهترین جواب رو از ترکیب این الگوها تولید می‌کنم! 🤖"
            )
        return (
            f"🧠 I use *Markov chains* as my brain!\n\n"
            f"📊 My brain currently has:\n"
            f"  🔑 {keys:,} patterns\n"
            f"  📚 {vocab:,} words\n"
            f"  🔗 {trans:,} connections\n\n"
            f"I analyze every message in the group and learn new patterns. "
            f"When you ask a question, I combine these patterns to generate "
            f"the best response! 🤖"
        )

    # Help/capabilities questions
    help_fa = ["چیکار میتونی", "چه کارایی", "توانایی", "قابلیت"]
    help_en = ["what can you do", "capabilities", "abilities", "features"]
    if any(k in ql for k in help_fa + help_en):
        if lang == "fa":
            return (
                "🤖 *توانایی‌های من:*\n\n"
                "🧠 جواب دادن به سوالات (از مغز مارکوف)\n"
                "😂 تعریف جوک و فکت‌های جعلی\n"
                "💭 تشخیص احساسات و موضوع\n"
                "🎭 ۶ شخصیت مختلف\n"
                "🔥 روست کردن (با محبت!)\n"
                "🎯 ۶ استراتژی پاسخگویی\n"
                "🎓 یادگیری مداوم از پیام‌ها\n\n"
                "هر چی بیشتر باهام حرف بزنید، باهوش‌تر میشم! 📈"
            )
        return (
            "🤖 *My capabilities:*\n\n"
            "🧠 Answer questions (from Markov brain)\n"
            "😂 Tell jokes & absurd facts\n"
            "💭 Detect emotions & topics\n"
            "🎭 6 personality modes\n"
            "🔥 Roasting (with love!)\n"
            "🎯 6 response strategies\n"
            "🎓 Continuous learning from messages\n\n"
            "The more you talk to me, the smarter I get! 📈"
        )

    return None


def _tool_topic_expert(query: str, lang: str, chat_id: int) -> str | None:
    """Tool 2: Topic-aware response — combines topic reaction with generation."""
    topic = _detect_topic(query)
    if not topic:
        return None

    # Get a topic reaction
    reaction = _strategy_topic_reaction(query, lang)

    # Also try to generate something relevant
    gen = generate(query, max_words=25, chat_id=chat_id, num_candidates=6)

    if reaction and gen:
        return f"{reaction}\n\n💬 {gen}"
    return reaction or gen


def _tool_humor(query: str, lang: str) -> str | None:
    """Tool 3: Humor engine — jokes, absurd facts, roasts."""
    roll = random.random()

    if roll < 0.35:
        joke = _make_chain_joke(lang)
        if joke:
            return f"😂 {joke}"

    if roll < 0.65:
        fact = _make_absurd_fact(lang)
        if fact:
            return f"📊 {fact}"

    if roll < 0.85 and _should_roast(query):
        roast = random.choice(_ROASTS.get(lang, _ROASTS["en"]))
        return roast

    comeback = random.choice(_COMEBACKS.get(lang, _COMEBACKS["en"]))
    return comeback


def _tool_question_answerer(query: str, lang: str, chat_id: int) -> str | None:
    """Tool 4: Question answerer — tries harder for questions."""
    if not _is_question(query):
        return None

    # Try generating multiple candidates and pick the best
    result = generate(query, max_words=40, chat_id=chat_id, num_candidates=12)
    if result:
        return result

    # Fallback: use debate strategy (agree/disagree)
    result = _strategy_debate(query, max_words=30)
    if result:
        return result

    return None


def _tool_creative(query: str, lang: str, chat_id: int) -> str | None:
    """Tool 5: Creative text — mashup, echo-twist, reverse wisdom."""
    roll = random.random()

    if roll < 0.33:
        result = _strategy_mashup(max_words=30)
        if result:
            return result

    if roll < 0.66 and query:
        result = _strategy_echo_twist(query, max_words=25)
        if result:
            return result

    result = _strategy_reverse_wisdom(max_words=25)
    return result


def _tool_generate(query: str, chat_id: int) -> str | None:
    """Tool 6: Standard Markov generation — the default fallback."""
    return generate(query, max_words=40, chat_id=chat_id, num_candidates=8)


# ═══════════════════════════════════════════════════
# AGENT: Observe → Think → Act → Respond
# ═══════════════════════════════════════════════════

def _agent_think(query: str, lang: str, chat_id: int) -> tuple[str, str]:
    """
    Agent reasoning step — decides which tool to use.
    Returns (tool_name, reasoning).

    This mimics LangChain's agent decision loop:
    1. Observe the input (emotion, topic, question type)
    2. Think about which tool is best
    3. Return the chosen tool name
    """
    emotion = _detect_emotion(query)
    topic = _detect_topic(query)
    is_q = _is_question(query)
    query_lower = query.lower()

    # Check for knowledge base hits first (highest priority)
    identity_keywords = [
        "تو کی", "اسمت", "چی هستی", "who are you", "your name",
        "what are you", "چیکار میتونی", "what can you do",
        "چطور کار", "how do you work", "مغزت", "your brain",
        "کی ساختت", "who made", "معرفی", "introduce",
        "هوشت", "your intelligence", "چه کارایی", "capabilities",
    ]
    if any(k in query_lower for k in identity_keywords):
        return "knowledge", "Identity/capability question detected"

    # Questions get priority treatment
    if is_q:
        # Topic-specific questions go to topic expert
        if topic:
            return "topic_expert", f"Question about {topic}"
        return "question", f"Question detected, emotion={emotion}"

    # Humor triggers
    humor_triggers = [
        "جوک", "joke", "بخند", "laugh", "خنده", "funny",
        "بامزه", "سم", "😂", "🤣", "فکت", "fact",
    ]
    if any(k in query_lower for k in humor_triggers):
        return "humor", "Humor requested"

    # Short messages often get roasted or comebacks
    if len(query.split()) <= 3 and random.random() < 0.30:
        return "humor", "Short message, humor response"

    # Topic-specific responses
    if topic and random.random() < 0.45:
        return "topic_expert", f"Topic detected: {topic}"

    # Emotional responses route to creative
    if emotion in ("sad", "romantic") and random.random() < 0.40:
        return "creative", f"Emotional context: {emotion}"

    # Creative responses sometimes
    if random.random() < 0.20:
        return "creative", "Random creative response"

    # Default: standard generation
    return "generate", f"Standard generation, emotion={emotion}, topic={topic}"


def _agent_act(tool_name: str, query: str, lang: str, chat_id: int) -> str | None:
    """Execute the chosen tool and return the result."""
    if tool_name == "knowledge":
        return _tool_knowledge(query, lang)
    elif tool_name == "topic_expert":
        return _tool_topic_expert(query, lang, chat_id)
    elif tool_name == "humor":
        return _tool_humor(query, lang)
    elif tool_name == "question":
        return _tool_question_answerer(query, lang, chat_id)
    elif tool_name == "creative":
        return _tool_creative(query, lang, chat_id)
    elif tool_name == "generate":
        return _tool_generate(query, chat_id)
    return None


# ═══════════════════════════════════════════════════
# /ai COMMAND — Markov AI Agent
# ═══════════════════════════════════════════════════

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    # Get input from args or reply
    query = None
    if context.args:
        query = " ".join(context.args)
    elif (
        update.message.reply_to_message
        and update.message.reply_to_message.text
    ):
        query = update.message.reply_to_message.text

    if not query:
        await update.message.reply_text(s["ai_usage"], parse_mode="Markdown")
        return

    keys, _, vocab = get_brain_stats()

    # If brain is too small, use knowledge base only
    if keys < 10:
        result = _tool_knowledge(query, lang)
        if not result:
            result = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))
        await update.message.reply_text(f"🤖 {result}", parse_mode="Markdown")
        return

    # Show thinking indicator
    thinking_msg = await update.message.reply_text(
        s["ai_thinking"], parse_mode="Markdown"
    )

    # Learn from the query too
    _add_context(chat.id, query)
    learn(query)

    # ── AGENT LOOP: Observe → Think → Act → Respond ──

    # Step 1: Observe
    emotion = _detect_emotion(query)
    mode = _pick_personality(chat.id, emotion)

    # Step 2: Think (choose tool)
    tool_name, reasoning = _agent_think(query, lang, chat.id)

    # Step 3: Act (execute tool)
    result = _agent_act(tool_name, query, lang, chat.id)

    # Retry with fallback tools if primary fails
    if not result:
        fallbacks = ["generate", "creative", "humor"]
        for fb in fallbacks:
            if fb != tool_name:
                result = _agent_act(fb, query, lang, chat.id)
                if result:
                    tool_name = fb
                    break

    # Last resort: knowledge base
    if not result:
        result = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))
        tool_name = "knowledge_fallback"

    # Step 4: Respond (apply personality)
    if tool_name not in ("knowledge",):
        result = _apply_personality(result, mode, lang)

    # Format with tool indicator
    tool_icons = {
        "knowledge": "📚",
        "topic_expert": "🏷",
        "humor": "😂",
        "question": "🤔",
        "creative": "✨",
        "generate": "🧠",
        "knowledge_fallback": "📚",
    }
    icon = tool_icons.get(tool_name, "🤖")

    # GIF response (15% chance if trigger found)
    if random.random() < 0.15:
        gif_query = _detect_gif_trigger(query, lang)
        if gif_query:
            gif_url = await _search_gif(gif_query)
            if gif_url:
                try:
                    await update.message.reply_animation(animation=gif_url)
                except Exception:
                    pass

    try:
        await thinking_msg.edit_text(
            f"{icon} {result}", parse_mode="Markdown"
        )
    except Exception:
        # If Markdown parsing fails, send without formatting
        try:
            await thinking_msg.edit_text(f"{icon} {result}")
        except Exception:
            await thinking_msg.edit_text(
                f"{icon} {random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE['en']))}"
            )
