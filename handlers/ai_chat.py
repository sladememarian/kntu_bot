# ==========================================
# KNTU Bot 25 — AI Agent (Google Gemini + Function Calling)
#
# Uses google-genai SDK directly — no langchain.
# Handles function calling loop manually.
# ==========================================

import logging
import random

from google import genai
from google.genai import types

from telegram import Update
from telegram.ext import ContextTypes

from config import GEMINI_API_KEY
from storage import get_lang
from strings import STRINGS

from handlers.tools import (
    search,
    scrape_website,
    markov_brain_generate,
    markov_brain_stats,
    markov_humor,
    markov_topic_react,
)
from handlers.markov_ai import (
    learn,
    _add_context,
    _KNOWLEDGE,
    _detect_gif_trigger,
    _search_gif,
)

logger = logging.getLogger("kntu_bot25.ai_agent")

# ═══════════════════════════════════════════════════
# GEMINI CLIENT
# ═══════════════════════════════════════════════════
client = genai.Client(api_key=GEMINI_API_KEY)

# ═══════════════════════════════════════════════════
# TOOL DEFINITIONS (for Gemini function calling)
# ═══════════════════════════════════════════════════

TOOL_MAP = {
    "search": search,
    "scrape_website": scrape_website,
    "markov_brain_generate": markov_brain_generate,
    "markov_brain_stats": markov_brain_stats,
    "markov_humor": markov_humor,
    "markov_topic_react": markov_topic_react,
}

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search",
        description="Search the web using DuckDuckGo for current information, facts, news, or answers to questions.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The search query",
                ),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="scrape_website",
        description="Scrape the text content of a website URL to get detailed information.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "url": types.Schema(
                    type=types.Type.STRING,
                    description="The website URL to scrape",
                ),
            },
            required=["url"],
        ),
    ),
    types.FunctionDeclaration(
        name="markov_brain_generate",
        description="Generate a creative response using the Markov chain brain trained on group chat messages. Good for casual conversation, creative text, and fun responses.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The user's message to generate a response for",
                ),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="markov_brain_stats",
        description="Get the current statistics of the Markov brain — number of patterns, transitions, and vocabulary size.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={},
        ),
    ),
    types.FunctionDeclaration(
        name="markov_humor",
        description="Generate a joke or absurd fact from the Markov brain vocabulary. Use when the user asks for humor, jokes, or something funny.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The user's message requesting humor",
                ),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="markov_topic_react",
        description="Detect the topic of the user's message (food, tech, sports, school, love, money, music, movies) and give a witty reaction.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The user's message to detect topic and react to",
                ),
            },
            required=["query"],
        ),
    ),
]

# ═══════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = """You are KNTU Bot 25, a smart AI assistant in a Telegram group chat.
You have access to several tools you can use to answer questions:

1. Use the 'search' tool to look up current information, facts, news,
   or anything the user is asking about from the web.
2. Use the 'scrape_website' tool if you need detailed content from a
   specific website URL.
3. Use the 'markov_brain_generate' tool to generate creative, fun, and casual
   responses from the group's learned chat patterns.
4. Use the 'markov_brain_stats' tool when the user asks about brain stats,
   how smart you are, or your learning progress.
5. Use the 'markov_humor' tool when the user asks for jokes, humor,
   or something funny.
6. Use the 'markov_topic_react' tool when the user is talking about a
   specific topic (food, tech, sports, school, love, money, music, movies)
   and wants a witty reaction.

RULES:
- If the user speaks Farsi, respond in Farsi. If English, respond in English.
- Keep responses concise but helpful (2-4 sentences max).
- Be friendly, witty, and entertaining.
- If a tool fails, try another approach or use your own knowledge.
- You are a fun group chat bot, not a formal assistant.
- For factual questions, prefer 'search' tool.
- For casual/creative chat, prefer 'markov_brain_generate' or 'markov_humor'.
"""

# ═══════════════════════════════════════════════════
# AGENT LOOP
# ═══════════════════════════════════════════════════

MAX_ITERATIONS = 5


def run_agent(query: str) -> str:
    """Run the Gemini function-calling agent loop."""
    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=query)],
        )
    ]

    for _ in range(MAX_ITERATIONS):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
                ),
            )
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return ""

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return ""

        has_function_calls = False

        for part in candidate.content.parts:
            if part.function_call:
                has_function_calls = True
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args) if part.function_call.args else {}

                logger.info("Tool call: %s(%s)", fn_name, fn_args)

                # Execute the tool
                fn = TOOL_MAP.get(fn_name)
                if fn:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        result = f"Tool error: {e}"
                else:
                    result = f"Unknown tool: {fn_name}"

                # Append model's function call + function response to conversation
                contents.append(candidate.content)
                contents.append(
                    types.Content(
                        role="function",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=fn_name,
                                    response={"result": str(result)},
                                )
                            )
                        ],
                    )
                )

        if not has_function_calls:
            # Extract final text response
            text_parts = [
                p.text for p in candidate.content.parts if p.text
            ]
            return "\n".join(text_parts) if text_parts else ""

    return ""


# ═══════════════════════════════════════════════════
# /ai TELEGRAM COMMAND
# ═══════════════════════════════════════════════════

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main /ai command — invokes the Gemini agent."""
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
        # Run the agent
        final_text = run_agent(query)

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
        # Fallback to Markov brain if Gemini fails
        try:
            fallback = markov_brain_generate(query)
            try:
                await thinking_msg.edit_text(
                    f"🧠 {fallback}", parse_mode="Markdown"
                )
            except Exception:
                await thinking_msg.edit_text(f"🧠 {fallback}")
        except Exception:
            await thinking_msg.edit_text(s["ai_error"], parse_mode="Markdown")
