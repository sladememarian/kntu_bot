# ==========================================
#  KNTU Bot 25 — Main Entry Point
#  A fun Persian/English Telegram group bot
# ==========================================

import logging
import os
from telegram import Update
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatMemberHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    filters,
)
from aiohttp import web
from telegram import InlineQueryResultGame

from config import BOT_TOKEN, DEBUG, BOT_NAME

# Handlers
from handlers.general import start_cmd, help_cmd, lang_cmd, debug_cmd, dumpdata_cmd, dbstatus_cmd, syncdata_cmd, loaddata_cmd
from handlers.fun import ship_cmd, lagab_cmd, rizz_cmd, gay_cmd, warn_handler, resetwarn_cmd
from handlers.jokes_stories import joke_cmd, story_cmd
from handlers.news import news_cmd, setnews_cmd, removenews_cmd
from handlers.ai_chat import ai_cmd
from handlers.markov_ai import markov_listen, ai2_cmd, ai2stats_cmd, ai2test_cmd
from handlers.ophelia_ai import ophelia_listen, ai3_cmd, ai3stats_cmd
from handlers.books import book_cmd
from handlers.image_gen import imagine_cmd
from handlers.welcome import greet_new_member, greet_via_message, track_message_members
from handlers.family import family_cmd, family_callback
from handlers.music import music_cmd
from handlers.suggest import anime_cmd, movie_cmd, game_cmd
from handlers.economy import (
    wallet_cmd, daily_cmd, leaderboard_cmd, bet_cmd,
    slots_cmd, dice_cmd, rob_cmd, give_cmd, rps_cmd,
    work_cmd, spin_cmd, invest_cmd, sell_cmd, portfolio_cmd, event_cmd,
    jail_list_cmd, profit_cmd, bail_cmd, jailbreak_cmd,
    fish_cmd, mine_cmd, quest_cmd,
)
from handlers.xo import xo_cmd, xo_callback
from handlers.riddle import riddle_cmd, riddle_callback
from handlers.howallbot import (
    howmuch_cmd, eight_ball_cmd, whois_cmd,
    truth_cmd, dare_cmd, quote_cmd, advice_cmd, profile_cmd,
)
from handlers.shop import shop_cmd, shop_callback, buy_cmd, inventory_cmd, gift_cmd
from handlers.petshop import petshop_cmd, buypet_cmd
from handlers.foodshop import foodshop_cmd, buyfood_cmd, eat_cmd, drink_cmd
from handlers.abilities import abilities_cmd, buyability_cmd, use_ability_cmd
from handlers.calendar import calendar_cmd
from handlers.bank import bank_cmd, loan_cmd, bankmanager_cmd, embezzle_cmd, investigate_cmd, bankrob_cmd
from handlers.casino import casino_cmd, megaslots_cmd, blackjack_cmd, bj_callback, bar_cmd, coinflip_cmd
from handlers.places import places_cmd, date_cmd, giftpet_cmd, giftfood_cmd

# ---- Logging ----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if DEBUG else logging.INFO,
)
logger = logging.getLogger(BOT_NAME)

# ═══════════════════════════════════════════════════
# WEB SERVER for HTML5 Games (served via aiohttp)
# ═══════════════════════════════════════════════════
GAME_SHORT_NAME = os.environ.get("GAME_SHORT_NAME", "casino")
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


async def _serve_casino(request):
    """Serve the casino HTML5 game page."""
    path = os.path.join(_STATIC_DIR, "casino.html")
    if os.path.isfile(path):
        return web.FileResponse(path)
    return web.Response(text="Game not found", status=404)


async def _start_web_server(app):
    """Start aiohttp web server alongside the bot (for game hosting)."""
    web_app = web.Application()
    web_app.router.add_get("/", _serve_casino)
    web_app.router.add_get("/casino", _serve_casino)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    app.bot_data["_web_runner"] = runner
    logger.info("🌐 Web server started on port %d", port)


async def _stop_web_server(app):
    """Stop the web server."""
    runner = app.bot_data.get("_web_runner")
    if runner:
        await runner.cleanup()
        logger.info("🌐 Web server stopped")


async def casinogame_cmd(update: Update, context):
    """
    /casinogame — Launch the HTML5 Casino game in Telegram.
    Requires game to be registered via @BotFather first.
    """
    try:
        await context.bot.send_game(
            chat_id=update.effective_chat.id,
            game_short_name=GAME_SHORT_NAME,
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ بازی هنوز تنظیم نشده! / Game not set up!\n"
            "ادمین باید بازی رو در @BotFather ثبت کنه.\n"
            "Admin: /newgame in @BotFather → short_name = casino\n"
            f"Error: {e}"
        )


def _get_game_url():
    domain = (
        os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        or os.environ.get("RAILWAY_STATIC_URL", "").replace("https://", "").replace("http://", "")
        or os.environ.get("WEB_URL", "").replace("https://", "").replace("http://", "")
        or "kntubot-production.up.railway.app"
    )
    return f"https://{domain}/casino"


async def game_callback(update: Update, context):
    """Handle the 'Play' button click on a Telegram Game message."""
    query = update.callback_query
    if not query:
        return
    # Only handle game callbacks (not regular button callbacks)
    if not query.game_short_name:
        return
    url = _get_game_url()
    logger.info("Game callback from %s: sending URL %s", query.from_user.id, url)
    try:
        await query.answer(url=url)
    except Exception as e:
        logger.error("Game callback error: %s", e)


async def game_inline(update: Update, context):
    """Handle inline queries — lets users send casino game via @bot casino."""
    query = update.inline_query
    if not query:
        return
    results = [
        InlineQueryResultGame(id="casino", game_short_name=GAME_SHORT_NAME)
    ]
    try:
        await query.answer(results)
    except Exception as e:
        logger.error("Inline game error: %s", e)


def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("=" * 50)
        print("  ERROR: Please set your BOT_TOKEN in .env file!")
        print("  1. Copy .env.example to .env")
        print("  2. Get a token from @BotFather on Telegram")
        print("  3. Paste it in the .env file")
        print("=" * 50)
        return

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(_start_web_server)
        .post_shutdown(_stop_web_server)
        .build()
    )

    # ---- Command Handlers ----
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("debug", debug_cmd))
    app.add_handler(CommandHandler("dumpdata", dumpdata_cmd))
    app.add_handler(CommandHandler("dbstatus", dbstatus_cmd))
    app.add_handler(CommandHandler("syncdata", syncdata_cmd))
    app.add_handler(CommandHandler("loaddata", loaddata_cmd))

    # Fun
    app.add_handler(CommandHandler("ship", ship_cmd))
    app.add_handler(CommandHandler("lagab", lagab_cmd))
    app.add_handler(CommandHandler("rizz", rizz_cmd))
    app.add_handler(CommandHandler("gay", gay_cmd))

    # Jokes & Stories
    app.add_handler(CommandHandler("joke", joke_cmd))
    app.add_handler(CommandHandler("story", story_cmd))

    # News
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("setnews", setnews_cmd))
    app.add_handler(CommandHandler("removenews", removenews_cmd))

    # AI
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler("ai2", ai2_cmd))
    app.add_handler(CommandHandler("ai2stats", ai2stats_cmd))
    app.add_handler(CommandHandler("ai2test", ai2test_cmd))

    # AI3 (OPHELIA)
    app.add_handler(CommandHandler("ai3", ai3_cmd))
    app.add_handler(CommandHandler("ai3stats", ai3stats_cmd))

    # Books
    app.add_handler(CommandHandler("book", book_cmd))

    # Suggestions
    app.add_handler(CommandHandler("anime", anime_cmd))
    app.add_handler(CommandHandler("movie", movie_cmd))
    app.add_handler(CommandHandler("game", game_cmd))
    app.add_handler(CommandHandler("music", music_cmd))

    # Family tree
    app.add_handler(CommandHandler("family", family_cmd))
    app.add_handler(CallbackQueryHandler(family_callback, pattern=r"^fam_(accept|reject):"))

    # Image Generation
    app.add_handler(CommandHandler("imagine", imagine_cmd))

    # Economy
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("bet", bet_cmd))
    app.add_handler(CommandHandler("slots", slots_cmd))
    app.add_handler(CommandHandler("dice", dice_cmd))
    app.add_handler(CommandHandler("rob", rob_cmd))
    app.add_handler(CommandHandler("give", give_cmd))
    app.add_handler(CommandHandler("rps", rps_cmd))
    app.add_handler(CommandHandler("work", work_cmd))
    app.add_handler(CommandHandler("spin", spin_cmd))
    app.add_handler(CommandHandler("invest", invest_cmd))
    app.add_handler(CommandHandler("sell", sell_cmd))
    app.add_handler(CommandHandler("portfolio", portfolio_cmd))
    app.add_handler(CommandHandler("event", event_cmd))
    app.add_handler(CommandHandler("jail", jail_list_cmd))
    app.add_handler(CommandHandler("profit", profit_cmd))
    app.add_handler(CommandHandler("bail", bail_cmd))
    app.add_handler(CommandHandler("jailbreak", jailbreak_cmd))
    app.add_handler(CommandHandler("fish", fish_cmd))
    app.add_handler(CommandHandler("mine", mine_cmd))
    app.add_handler(CommandHandler("quest", quest_cmd))

    # Shop system
    app.add_handler(CommandHandler("shop", shop_cmd))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^shop_cat:"))
    app.add_handler(CommandHandler("buy", buy_cmd))
    app.add_handler(CommandHandler("inventory", inventory_cmd))
    app.add_handler(CommandHandler("gift", gift_cmd))

    # Pet Shop
    app.add_handler(CommandHandler("petshop", petshop_cmd))
    app.add_handler(CommandHandler("buypet", buypet_cmd))

    # Food Shop
    app.add_handler(CommandHandler("foodshop", foodshop_cmd))
    app.add_handler(CommandHandler("buyfood", buyfood_cmd))
    app.add_handler(CommandHandler("eat", eat_cmd))
    app.add_handler(CommandHandler("drink", drink_cmd))

    # Abilities
    app.add_handler(CommandHandler("abilities", abilities_cmd))
    app.add_handler(CommandHandler("buyability", buyability_cmd))
    app.add_handler(CommandHandler("punch", use_ability_cmd))
    app.add_handler(CommandHandler("hug", use_ability_cmd))
    app.add_handler(CommandHandler("kiss", use_ability_cmd))
    app.add_handler(CommandHandler("kill", use_ability_cmd))
    app.add_handler(CommandHandler("slap", use_ability_cmd))
    app.add_handler(CommandHandler("tickle", use_ability_cmd))
    app.add_handler(CommandHandler("poke", use_ability_cmd))
    app.add_handler(CommandHandler("bite", use_ability_cmd))
    app.add_handler(CommandHandler("pat", use_ability_cmd))
    app.add_handler(CommandHandler("highfive", use_ability_cmd))
    app.add_handler(CommandHandler("revive", use_ability_cmd))

    # Bank System
    app.add_handler(CommandHandler("bank", bank_cmd))
    app.add_handler(CommandHandler("loan", loan_cmd))
    app.add_handler(CommandHandler("bankmanager", bankmanager_cmd))
    app.add_handler(CommandHandler("embezzle", embezzle_cmd))
    app.add_handler(CommandHandler("investigate", investigate_cmd))
    app.add_handler(CommandHandler("bankrob", bankrob_cmd))

    # Casino & Bar
    app.add_handler(CommandHandler("casino", casino_cmd))
    app.add_handler(CommandHandler("megaslots", megaslots_cmd))
    app.add_handler(CommandHandler("blackjack", blackjack_cmd))
    app.add_handler(CallbackQueryHandler(bj_callback, pattern=r"^bj:"))
    app.add_handler(CommandHandler("bar", bar_cmd))
    app.add_handler(CommandHandler("coinflip", coinflip_cmd))

    # Casino HTML5 Game
    app.add_handler(CommandHandler("casinogame", casinogame_cmd))
    app.add_handler(CommandHandler("playcasino", casinogame_cmd))

    # Places & Dates
    app.add_handler(CommandHandler("places", places_cmd))
    app.add_handler(CommandHandler("date", date_cmd))
    app.add_handler(CommandHandler("giftpet", giftpet_cmd))
    app.add_handler(CommandHandler("giftfood", giftfood_cmd))

    # Persian Calendar
    app.add_handler(CommandHandler("calendar", calendar_cmd))

    # XO (Tic-Tac-Toe)
    app.add_handler(CommandHandler("xo", xo_cmd))
    app.add_handler(CallbackQueryHandler(xo_callback, pattern=r"^xo:"))

    # Riddles
    app.add_handler(CommandHandler("riddle", riddle_cmd))
    app.add_handler(CallbackQueryHandler(riddle_callback, pattern=r"^riddle:"))

    # HowAllBot-style fun
    app.add_handler(CommandHandler("howmuch", howmuch_cmd))
    app.add_handler(CommandHandler("8ball", eight_ball_cmd))
    app.add_handler(CommandHandler("whois", whois_cmd))
    app.add_handler(CommandHandler("truth", truth_cmd))
    app.add_handler(CommandHandler("dare", dare_cmd))
    app.add_handler(CommandHandler("quote", quote_cmd))
    app.add_handler(CommandHandler("advice", advice_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))

    # Language toggle
    app.add_handler(CommandHandler("lang", lang_cmd))

    # ---- Welcome / Greet ----
    app.add_handler(ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_via_message))

    # Warn system
    app.add_handler(CommandHandler("resetwarn", resetwarn_cmd))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^اخطار$'), warn_handler))
    #
    # ---- Track members for /ship ----
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, track_message_members), group=1)

    # ---- Markov AI: learn from all text messages ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, markov_listen), group=2)

    # ---- OPHELIA AI: learn from all text messages ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ophelia_listen), group=3)

    # ---- Game callback handler (separate group so it doesn't block other callbacks) ----
    app.add_handler(CallbackQueryHandler(game_callback), group=4)

    # ---- Inline query handler for games ----
    app.add_handler(InlineQueryHandler(game_inline))

    # ---- Error handler ----
    async def error_handler(update, context):
        if isinstance(context.error, (TimedOut, NetworkError)):
            logger.warning("Network issue: %s", context.error)
            return
        logger.error("Unhandled exception:", exc_info=context.error)

    app.add_error_handler(error_handler)

    # ---- Start Polling ----
    logger.info(f"🤖 {BOT_NAME} is starting...")
    print(f"🤖 {BOT_NAME} is running! Press Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
