# ==========================================
# KNTU Bot 25 — AI Agent (LangChain + Gemini)
#
# Built following "Building a Simple AI Agent
# With Python and Langchain" article EXACTLY:
#
#   1. tools.py — Tool(name, func, description)
#      search, scrape, markov_generate, humor, topic
#   2. System Prompt — ChatPromptTemplate
#   3. Agent — create_tool_calling_agent
#   4. AgentExecutor — runs agent with tools
#   5. Structured Output — PydanticOutputParser
#
# LLM: Google Gemini via langchain-google-genai
# ==========================================

import logging
import random

from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

from telegram import Update
from telegram.ext import ContextTypes

from config import GEMINI_API_KEY
from storage import get_lang
from strings import STRINGS

from handlers.tools import all_tools
from handlers.markov_ai import (
    learn,
    get_brain_stats,
    _add_context,
    _KNOWLEDGE,
    _detect_gif_trigger,
    _search_gif,
)

logger = logging.getLogger("kntu_bot25.ai_agent")


# ═══════════════════════════════════════════════════
# STEP 1 — STRUCTURED OUTPUT (Pydantic models)
# Mirrors the article's LeadResponse / LeadResponseList
# ═══════════════════════════════════════════════════

class AIResponse(BaseModel):
    """Structured output from the AI agent."""
    answer: str
    tools_used: list[str]
    language: str


# ═══════════════════════════════════════════════════
# STEP 2 — LLM + PARSER + PROMPT
# Mirrors the article's main.py setup exactly
# ═══════════════════════════════════════════════════

# Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY,
)

# Pydantic output parser
parser = PydanticOutputParser(pydantic_object=AIResponse)

# System prompt — ChatPromptTemplate exactly like the article
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are KNTU Bot 25, a smart AI assistant in a Telegram group chat.
            You have access to several tools you can use to answer questions:

            1. Use the 'search' tool to look up current information, facts, news,
               or anything the user is asking about from the web.
            2. Use the 'scrape_website' tool if you need detailed content from a
               specific website URL.
            3. Use the 'markov_generate' tool to generate creative, fun, and casual
               responses from the group's learned chat patterns.
            4. Use the 'markov_stats' tool when the user asks about brain stats,
               how smart you are, or your learning progress.
            5. Use the 'markov_humor' tool when the user asks for jokes, humor,
               or something funny.
            6. Use the 'markov_topic' tool when the user is talking about a
               specific topic (food, tech, sports, school, love, money, music, movies)
               and wants a witty reaction.

            RULES:
            - If the user speaks Farsi, respond in Farsi. If English, respond in English.
            - Keep responses concise but helpful (2-4 sentences max).
            - Be friendly, witty, and entertaining.
            - If a tool fails, try another approach or use your own knowledge.
            - You are a fun group chat bot, not a formal assistant.
            - For factual questions, prefer 'search' tool.
            - For casual/creative chat, prefer 'markov_generate' or 'markov_humor'.

            Return the output in this format: {format_instructions}
            """,
        ),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())


# ═══════════════════════════════════════════════════
# STEP 3 — AGENT + EXECUTOR
# Mirrors the article: create_tool_calling_agent + AgentExecutor
# ═══════════════════════════════════════════════════

# List our tools — pulled from handlers/tools.py
tools = all_tools

# Create the agent with tool-calling abilities
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools,
)

# Wrap the agent in an executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    handle_parsing_errors=True,
    max_iterations=5,
)


# ═══════════════════════════════════════════════════
# STEP 4 — /ai TELEGRAM COMMAND
# ═══════════════════════════════════════════════════

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main /ai command — invokes the LangChain agent."""
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

    # Show thinking indicator
    thinking_msg = await update.message.reply_text(
        s["ai_thinking"], parse_mode="Markdown"
    )

    # Learn from the user's query (feed Markov brain)
    _add_context(chat.id, query)
    learn(query)

    try:
        # ── Run AgentExecutor — exactly like the article ──
        raw_response = agent_executor.invoke({"query": query})
        output = raw_response.get("output", "")

        # Try to parse structured output
        try:
            structured = parser.parse(output)
            final_text = structured.answer
        except Exception:
            # If parsing fails, use raw output
            final_text = output if output else None

        if not final_text:
            final_text = random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))

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

        # Send response
        try:
            await thinking_msg.edit_text(
                f"🤖 {final_text}", parse_mode="Markdown"
            )
        except Exception:
            try:
                await thinking_msg.edit_text(f"🤖 {final_text}")
            except Exception:
                await thinking_msg.edit_text(
                    f"🤖 {random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE['en']))}"
                )

    except Exception as e:
        logger.error("AI agent error: %s", e)
        # Fallback to Markov brain if LangChain/Gemini fails
        try:
            from handlers.tools import markov_brain_generate
            fallback = markov_brain_generate(query)
            try:
                await thinking_msg.edit_text(
                    f"🧠 {fallback}", parse_mode="Markdown"
                )
            except Exception:
                await thinking_msg.edit_text(f"🧠 {fallback}")
        except Exception:
            await thinking_msg.edit_text(s["ai_error"], parse_mode="Markdown")
