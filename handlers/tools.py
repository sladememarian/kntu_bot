# ==========================================
# KNTU Bot 25 — AI Agent Tools
#
# Following "Building a Simple AI Agent With
# Python and Langchain" article:
#   Tool(name, func, description)
#
# Tools:
#   1. search — DuckDuckGo web search
#   2. scrape — Scrape a website for content
#   3. markov_generate — Generate text from
#      the Markov brain trained on chat
#   4. markov_stats — Get brain statistics
# ==========================================

import re
import logging
import requests
from bs4 import BeautifulSoup

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import Tool

from handlers.markov_ai import (
    generate as markov_generate_text,
    get_brain_stats,
    _detect_emotion,
    _detect_topic,
    _make_chain_joke,
    _make_absurd_fact,
    _KNOWLEDGE,
    _strategy_topic_reaction,
)

logger = logging.getLogger("kntu_bot25.tools")


# ═══════════════════════════════════════════════════
# TOOL FUNCTIONS
# ═══════════════════════════════════════════════════

def scrape_website(url: str) -> str:
    """Scrape raw text from a website URL."""
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:5000]
    except Exception as e:
        return f"Error scraping website: {e}"


def markov_brain_generate(query: str) -> str:
    """Generate a response using the Markov chain brain trained on group messages."""
    keys, _, vocab = get_brain_stats()
    if keys < 10:
        import random
        lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in query) else "en"
        return random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))

    result = markov_generate_text(query, max_words=45, num_candidates=8)
    if result:
        return result

    import random
    lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in query) else "en"
    return random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))


def markov_brain_stats(query: str = "") -> str:
    """Get current Markov brain statistics — keys, transitions, vocabulary size."""
    keys, transitions, vocab = get_brain_stats()
    return (
        f"Brain Stats: {keys:,} pattern keys, "
        f"{transitions:,} transitions, "
        f"{vocab:,} vocabulary words"
    )


def markov_humor(query: str) -> str:
    """Generate a joke or absurd fact from the Markov brain vocabulary."""
    import random
    lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in query) else "en"

    roll = random.random()
    if roll < 0.5:
        joke = _make_chain_joke(lang)
        if joke:
            return joke
    fact = _make_absurd_fact(lang)
    if fact:
        return fact
    return random.choice(_KNOWLEDGE.get(lang, _KNOWLEDGE["en"]))


def markov_topic_react(query: str) -> str:
    """Detect the topic of the query and give a witty reaction."""
    import random
    lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in query) else "en"
    topic = _detect_topic(query)
    if topic:
        reaction = _strategy_topic_reaction(query, lang)
        if reaction:
            return reaction
    return markov_brain_generate(query)


# ═══════════════════════════════════════════════════
# LANGCHAIN TOOL DEFINITIONS
# Exactly like the article: Tool(name, func, description)
# ═══════════════════════════════════════════════════

search = DuckDuckGoSearchRun()

search_tool = Tool(
    name="search",
    func=search.run,
    description="Search the web using DuckDuckGo for current information, facts, news, or answers to questions.",
)

scrape_tool = Tool(
    name="scrape_website",
    func=scrape_website,
    description="Scrape the text content of a website URL to get detailed information.",
)

markov_tool = Tool(
    name="markov_generate",
    func=markov_brain_generate,
    description="Generate a creative response using the Markov chain brain that has been trained on group chat messages. Good for casual conversation, creative text, and fun responses.",
)

markov_stats_tool = Tool(
    name="markov_stats",
    func=markov_brain_stats,
    description="Get the current statistics of the Markov brain — number of patterns, transitions, and vocabulary size.",
)

markov_humor_tool = Tool(
    name="markov_humor",
    func=markov_humor,
    description="Generate a joke or absurd fact from the Markov brain vocabulary. Use when the user asks for humor, jokes, or something funny.",
)

markov_topic_tool = Tool(
    name="markov_topic",
    func=markov_topic_react,
    description="Detect the topic of the user's message (food, tech, sports, school, love, money, music, movies) and give a witty reaction.",
)

# All tools list — passed to the agent
all_tools = [
    search_tool,
    scrape_tool,
    markov_tool,
    markov_stats_tool,
    markov_humor_tool,
    markov_topic_tool,
]
