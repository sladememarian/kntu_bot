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
import json as _json

from config import BOT_TOKEN, DEBUG, BOT_NAME, AI_ENABLED
from storage import get_balance as _get_balance, add_balance as _add_balance

# Handlers
from handlers.general import start_cmd, help_cmd, help_callback, lang_cmd, debug_cmd, dumpdata_cmd, dbstatus_cmd, syncdata_cmd, loaddata_cmd
from handlers.fun import ship_cmd, lagab_cmd, rizz_cmd, gay_cmd, warn_handler, resetwarn_cmd
from handlers.jokes_stories import joke_cmd, story_cmd
from handlers.news import news_cmd, setnews_cmd, removenews_cmd
from handlers.ai_chat import ai_cmd
from handlers.markov_ai import markov_listen, crisis_listen
from handlers.ophelia_ai import ophelia_listen, ai3_cmd, ai3stats_cmd
from handlers.bob_ai import bob_cmd, bobstats_cmd, bob_listen
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
    donate_cmd, charity_cmd,
    realestate_cmd, buyproperty_cmd, sellproperty_cmd,
    economy_cmd,
    bounty_cmd, bounties_cmd,
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
from handlers.casino import casino_cmd, megaslots_cmd, blackjack_cmd, bj_callback, bar_cmd, coinflip_cmd, casinoleader_cmd, paytax_cmd
from handlers.places import places_cmd, date_cmd, giftpet_cmd, giftfood_cmd
from handlers.gacha import roll_cmd, collection_cmd, sellchar_cmd, tradechar_cmd, gacha_callback, trade_callback
from handlers.clan import clan_cmd
from handlers.drops import drop_counter, grab_callback

# ---- Logging ----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if DEBUG else logging.INFO,
)
logger = logging.getLogger(BOT_NAME)

# ═══════════════════════════════════════════════════════════════════════════
# WEB SERVER for HTML5 Games (served via aiohttp)
# ═══════════════════════════════════════════════════════════════════════════
GAME_SHORT_NAME = os.environ.get("GAME_SHORT_NAME", "casino")
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Daytona preview default (port 8091). Override with WEB_URL / RAILWAY_* env.
_DEFAULT_GAME_HOST = "8091-8365a2c3-5e86-45fc-bf95-6b58a1f6a309.daytonaproxy01.eu"


async def _serve_casino(request):
    """Serve the casino HTML5 game page."""
    path = os.path.join(_STATIC_DIR, "casino.html")
    if os.path.isfile(path):
        return web.FileResponse(path)
    return web.Response(text="Game not found", status=404)


# ── Wallet API for HTML5 game ─────────────────────────────────────────────
async def _api_get_balance(request):
    """GET /api/balance?chat_id=X&user_id=Y → returns wallet balance."""
    try:
        chat_id = int(request.query.get("chat_id", 0))
        user_id = int(request.query.get("user_id", 0))
        if not chat_id or not user_id:
            return web.json_response({"error": "missing chat_id or user_id"}, status=400)
        bal = _get_balance(chat_id, user_id)
        return web.json_response({"balance": bal})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def _api_update_balance(request):
    """POST /api/balance {chat_id, user_id, delta} → add/subtract from wallet.

    Validates delta, clamps losses so balance never goes negative, and reports
    the actual applied delta (so the client can resync exactly).
    """
    try:
        body = await request.json()
        chat_id = int(body.get("chat_id", 0))
        user_id = int(body.get("user_id", 0))
        try:
            delta = int(body.get("delta", 0))
        except (TypeError, ValueError):
            return web.json_response({"error": "delta must be int"}, status=400)
        if not chat_id or not user_id:
            return web.json_response({"error": "missing chat_id or user_id"}, status=400)
        # Sanity clamp on magnitude (anti-cheat / fat-finger)
        if abs(delta) > 1_000_000:
            return web.json_response({"error": "delta out of range"}, status=400)
        if delta == 0:
            bal = _get_balance(chat_id, user_id)
            return web.json_response({"balance": bal, "applied_delta": 0})

        bal_before = _get_balance(chat_id, user_id)
        if delta < 0 and bal_before <= 0:
            return web.json_response(
                {"error": "insufficient balance", "balance": bal_before, "applied_delta": 0},
                status=400,
            )
        # Clamp loss to current balance so wallet never goes negative mid-flight
        applied = delta
        if delta < 0 and abs(delta) > bal_before:
            applied = -bal_before

        new_bal = _add_balance(chat_id, user_id, applied)
        if applied < 0:
            try:
                from handlers.casino import _process_casino_loss
                _process_casino_loss(chat_id, abs(applied))
            except Exception:
                pass
        return web.json_response({
            "balance": new_bal,
            "applied_delta": applied,
            "requested_delta": delta,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ── Poker lobby API ───────────────────────────────────────────────────────
import asyncio
_poker_lobbies = {}  # chat_id -> lobby dict
_poker_lock = asyncio.Lock()


def _poker_active_players(lobby):
    folded = set(lobby.get("folded") or [])
    return [p for p in lobby["players"] if p["user_id"] not in folded]


def _poker_turn_user_id(lobby):
    active = _poker_active_players(lobby)
    if not active:
        return None
    turn = int(lobby.get("turn", 0)) % len(active)
    return active[turn]["user_id"]


def _poker_public_state(lobby, user_id=""):
    active = _poker_active_players(lobby)
    resp = {
        "state": lobby["state"],
        "players": lobby["players"],
        "count": len(lobby["players"]),
        "pot": lobby.get("pot", 0),
        "bet": lobby.get("bet", 50),
        "turn": lobby.get("turn", 0),
        "turn_user_id": _poker_turn_user_id(lobby) if lobby["state"] not in ("waiting", "finished", "no_lobby") else None,
        "round": lobby.get("round", 0),
        "community": lobby.get("community", []),
        "folded": lobby.get("folded", []),
        "active_count": len(active),
    }
    if user_id and user_id in lobby.get("hands", {}):
        resp["hand"] = lobby["hands"][user_id]
    if lobby.get("state") == "finished":
        if lobby.get("winner"):
            resp["winner"] = lobby["winner"]
        if lobby.get("all_hands"):
            resp["all_hands"] = lobby["all_hands"]
        if lobby.get("reason"):
            resp["reason"] = lobby["reason"]
    return resp


async def _api_poker_join(request):
    """POST /api/poker/join {chat_id, user_id, name, bet} → join a poker lobby."""
    try:
        body = await request.json()
        chat_id = str(body.get("chat_id", ""))
        user_id = str(body.get("user_id", ""))
        name = body.get("name", "Player")
        bet = int(body.get("bet", 50))
        if not chat_id or not user_id:
            return web.json_response({"error": "missing params"}, status=400)
        if bet < 1:
            return web.json_response({"error": "invalid bet"}, status=400)

        async with _poker_lock:
            lobby = _poker_lobbies.setdefault(chat_id, {
                "players": [], "state": "waiting", "bet": bet,
                "deck": [], "hands": {}, "community": [],
                "pot": 0, "turn": 0, "round": 0, "folded": [],
                "winner": None, "all_hands": {}, "reason": None,
            })
            if lobby["state"] == "finished":
                lobby.update({
                    "players": [], "state": "waiting", "bet": bet,
                    "deck": [], "hands": {}, "community": [],
                    "pot": 0, "turn": 0, "round": 0, "folded": [],
                    "winner": None, "all_hands": {}, "reason": None,
                })

            if any(p["user_id"] == user_id for p in lobby["players"]):
                resp = _poker_public_state(lobby, user_id)
                resp["status"] = "already_joined"
                return web.json_response(resp)

            if lobby["state"] != "waiting":
                return web.json_response({"error": "game already started"}, status=400)

            bal = _get_balance(int(chat_id), int(user_id))
            if bal < bet:
                return web.json_response({"error": "not enough kollars"}, status=400)

            # First joiner sets the table bet
            if not lobby["players"]:
                lobby["bet"] = bet

            lobby["players"].append({"user_id": user_id, "name": name})
            resp = _poker_public_state(lobby, user_id)
            resp["status"] = "joined"
            return web.json_response(resp)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def _api_poker_status(request):
    """GET /api/poker/status?chat_id=X&user_id=Y → get lobby/game state."""
    try:
        chat_id = request.query.get("chat_id", "")
        user_id = request.query.get("user_id", "")
        async with _poker_lock:
            lobby = _poker_lobbies.get(chat_id)
            if not lobby:
                return web.json_response({
                    "state": "no_lobby", "players": [], "count": 0,
                    "turn_user_id": None, "pot": 0, "folded": [],
                })
            return web.json_response(_poker_public_state(lobby, user_id))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def _make_deck():
    """Create and shuffle a standard 52-card deck."""
    import random as _r
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    deck = [{"rank": r, "suit": s} for s in suits for r in ranks]
    _r.shuffle(deck)
    return deck


async def _api_poker_start(request):
    """POST /api/poker/start {chat_id} → start the game if 4+ players."""
    try:
        body = await request.json()
        chat_id = str(body.get("chat_id", ""))

        async with _poker_lock:
            lobby = _poker_lobbies.get(chat_id)
            if not lobby or len(lobby["players"]) < 4:
                return web.json_response({"error": "need at least 4 players"}, status=400)
            if lobby["state"] != "waiting":
                return web.json_response({"error": "game already started"}, status=400)

            bet = lobby["bet"]
            # Deduct bet from all players (clamped)
            for p in lobby["players"]:
                uid = int(p["user_id"])
                bal = _get_balance(int(chat_id), uid)
                applied = -min(bet, bal)
                _add_balance(int(chat_id), uid, applied)
            lobby["pot"] = bet * len(lobby["players"])

            deck = _make_deck()
            lobby["deck"] = deck
            lobby["hands"] = {}
            for p in lobby["players"]:
                lobby["hands"][p["user_id"]] = [deck.pop(), deck.pop()]
            lobby["community"] = []
            lobby["state"] = "preflop"
            lobby["turn"] = 0
            lobby["round"] = 0
            lobby["folded"] = []
            lobby["winner"] = None
            lobby["all_hands"] = {}
            lobby["reason"] = None

            resp = _poker_public_state(lobby)
            resp["status"] = "started"
            return web.json_response(resp)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def _api_poker_action(request):
    """POST /api/poker/action {chat_id, user_id, action} → fold/check/raise."""
    try:
        body = await request.json()
        chat_id = str(body.get("chat_id", ""))
        user_id = str(body.get("user_id", ""))
        action = body.get("action", "check")  # fold, check, raise
        raise_amt = int(body.get("raise_amount", 0) or 0)

        async with _poker_lock:
            lobby = _poker_lobbies.get(chat_id)
            if not lobby or lobby["state"] in ("waiting", "finished"):
                return web.json_response({"error": "no active game"}, status=400)

            active = _poker_active_players(lobby)
            if not active:
                return web.json_response({"error": "no active players"}, status=400)

            # turn index is always over *current* active list
            turn_idx = int(lobby.get("turn", 0)) % len(active)
            current_player = active[turn_idx]
            if current_player["user_id"] != user_id:
                return web.json_response({
                    "error": "not your turn",
                    "turn_user_id": current_player["user_id"],
                }, status=400)

            if action == "fold":
                lobby["folded"].append(user_id)
                active = _poker_active_players(lobby)
                if len(active) == 1:
                    winner = active[0]
                    _add_balance(int(chat_id), int(winner["user_id"]), lobby["pot"])
                    lobby["state"] = "finished"
                    lobby["winner"] = winner
                    lobby["reason"] = "all_folded"
                    lobby["all_hands"] = {
                        p["user_id"]: lobby["hands"].get(p["user_id"], [])
                        for p in lobby["players"]
                    }
                    return web.json_response({
                        "status": "game_over",
                        "winner": winner,
                        "pot": lobby["pot"],
                        "reason": "all_folded",
                        "all_hands": lobby["all_hands"],
                        "community": lobby.get("community", []),
                        "state": "finished",
                        "turn_user_id": None,
                    })
                # After fold: keep turn index pointing at the next survivor.
                # The player who occupied turn_idx left, so the next player
                # slides into that same index — do NOT increment.
                if active:
                    lobby["turn"] = turn_idx % len(active)
            elif action == "raise" and raise_amt > 0:
                bal = _get_balance(int(chat_id), int(user_id))
                applied = min(raise_amt, bal)
                if applied > 0:
                    _add_balance(int(chat_id), int(user_id), -applied)
                    lobby["pot"] += applied
                # advance turn after raise
                active = _poker_active_players(lobby)
                lobby["turn"] = (turn_idx + 1) % max(1, len(active))
            else:
                # check / call — advance turn
                active = _poker_active_players(lobby)
                lobby["turn"] = (turn_idx + 1) % max(1, len(active))

            active = _poker_active_players(lobby)

            # Round complete when we've wrapped and everyone has acted once.
            # Track acts_this_round.
            lobby["acts"] = lobby.get("acts", 0) + 1
            if lobby["acts"] >= len(active) and lobby["state"] != "finished":
                lobby["acts"] = 0
                lobby["turn"] = 0
                lobby["round"] = lobby.get("round", 0) + 1
                deck = lobby["deck"]
                if lobby["state"] == "preflop":
                    lobby["community"] = [deck.pop(), deck.pop(), deck.pop()]
                    lobby["state"] = "flop"
                elif lobby["state"] == "flop":
                    lobby["community"].append(deck.pop())
                    lobby["state"] = "turn"
                elif lobby["state"] == "turn":
                    lobby["community"].append(deck.pop())
                    lobby["state"] = "river"
                elif lobby["state"] == "river":
                    lobby["state"] = "showdown"
                    winner = _evaluate_showdown(lobby, active)
                    _add_balance(int(chat_id), int(winner["user_id"]), lobby["pot"])
                    lobby["state"] = "finished"
                    lobby["winner"] = winner
                    lobby["reason"] = "showdown"
                    all_hands = {
                        p["user_id"]: lobby["hands"].get(p["user_id"], [])
                        for p in active
                    }
                    lobby["all_hands"] = all_hands
                    return web.json_response({
                        "status": "game_over",
                        "winner": winner,
                        "pot": lobby["pot"],
                        "reason": "showdown",
                        "all_hands": all_hands,
                        "community": lobby["community"],
                        "state": "finished",
                        "turn_user_id": None,
                    })

            resp = _poker_public_state(lobby, user_id)
            resp["status"] = "ok"
            return web.json_response(resp)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def _hand_rank(cards):
    """Evaluate a 5-7 card poker hand and return (rank, tiebreaker)."""
    import itertools

    def rank_val(r):
        vals = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
                "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
        return vals.get(r, 0)

    best = (0, [])
    for combo in itertools.combinations(cards, 5):
        ranks = sorted([rank_val(c["rank"]) for c in combo], reverse=True)
        suits = [c["suit"] for c in combo]
        is_flush = len(set(suits)) == 1
        is_straight = (ranks[0] - ranks[4] == 4 and len(set(ranks)) == 5)
        if set(ranks) == {14, 2, 3, 4, 5}:
            is_straight = True
            ranks = [5, 4, 3, 2, 1]

        counts = {}
        for r in ranks:
            counts[r] = counts.get(r, 0) + 1
        groups = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        pattern = tuple(g[1] for g in groups)

        if is_flush and is_straight and ranks[0] == 14:
            score = (9, ranks)
        elif is_flush and is_straight:
            score = (8, ranks)
        elif pattern[:1] == (4,):
            score = (7, [groups[0][0]] + ranks)
        elif pattern[:2] == (3, 2):
            score = (6, [groups[0][0], groups[1][0]])
        elif is_flush:
            score = (5, ranks)
        elif is_straight:
            score = (4, ranks)
        elif pattern[:1] == (3,):
            score = (3, [groups[0][0]] + ranks)
        elif pattern[:2] == (2, 2):
            score = (2, [groups[0][0], groups[1][0]] + ranks)
        elif pattern[:1] == (2,):
            score = (1, [groups[0][0]] + ranks)
        else:
            score = (0, ranks)

        if score > best:
            best = score
    return best


def _evaluate_showdown(lobby, active):
    """Find the winner among active players at showdown."""
    community = lobby.get("community", [])
    best_score = (-1, [])
    winner = active[0]
    for p in active:
        hand = lobby["hands"].get(p["user_id"], [])
        all_cards = hand + community
        score = _hand_rank(all_cards)
        if score > best_score:
            best_score = score
            winner = p
    return winner


def create_web_app() -> web.Application:
    """Build the aiohttp app (testable factory)."""
    web_app = web.Application()
    web_app.router.add_get("/", _serve_casino)
    web_app.router.add_get("/casino", _serve_casino)
    web_app.router.add_get("/api/balance", _api_get_balance)
    web_app.router.add_post("/api/balance", _api_update_balance)
    web_app.router.add_post("/api/poker/join", _api_poker_join)
    web_app.router.add_get("/api/poker/status", _api_poker_status)
    web_app.router.add_post("/api/poker/start", _api_poker_start)
    web_app.router.add_post("/api/poker/action", _api_poker_action)
    return web_app


async def _start_web_server(app):
    """Start aiohttp web server alongside the bot (for game hosting + API)."""
    if os.environ.get("DISABLE_AIOHTTP_SERVER", "").lower() == "true":
        logger.info("🌐 aiohttp server disabled via DISABLE_AIOHTTP_SERVER")
        return
    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(
        os.environ.get("PORT")
        or os.environ.get("WEBSITES_PORT")
        or os.environ.get("AIOHTTP_PORT")
        or 8091
    )
    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        app.bot_data["_web_runner"] = runner
        logger.info("🌐 Web server started on port %d", port)
    except OSError as e:
        logger.warning("🌐 Could not start web server on port %d: %s", port, e)
        logger.info("🌐 Bot will still work for Telegram commands.")


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
    """Public base URL for the HTML5 casino (no trailing path).

    Priority:
      1) CASINO_PROXY_URL  (Cloudflare Worker — skips Daytona warning page)
      2) CASINO_SIGNED_URL / WEB_URL_SIGNED  (Daytona signed preview — no auth headers)
      3) WEB_URL
      4) RAILWAY_* / default Daytona host
    """
    proxy = (os.environ.get("CASINO_PROXY_URL") or "").strip().rstrip("/")
    if proxy:
        if not proxy.startswith("http"):
            proxy = "https://" + proxy
        if proxy.endswith("/casino"):
            return proxy
        return proxy + "/casino"

    signed = (
        os.environ.get("CASINO_SIGNED_URL")
        or os.environ.get("WEB_URL_SIGNED")
        or ""
    ).strip().rstrip("/")
    if signed:
        if not signed.startswith("http"):
            signed = "https://" + signed
        if signed.endswith("/casino"):
            return signed
        return signed + "/casino"

    web_url = (os.environ.get("WEB_URL") or "").strip().rstrip("/")
    if web_url:
        if web_url.startswith("http://") or web_url.startswith("https://"):
            return web_url if web_url.endswith("/casino") else f"{web_url}/casino"
        return f"https://{web_url}/casino"

    domain = (
        os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        or os.environ.get("RAILWAY_STATIC_URL", "").replace("https://", "").replace("http://", "")
        or _DEFAULT_GAME_HOST
    )
    domain = domain.replace("https://", "").replace("http://", "").strip().strip("/")
    return f"https://{domain}/casino"


async def _mint_signed_casino_url() -> str | None:
    """Mint a Daytona signed preview URL for the casino port when credentials exist.

    Signed URLs embed the token in the host so Telegram's in-app browser does not
    need the x-daytona-preview-token header. Browser interstitial warning can still
    appear once unless Tier-3 / custom proxy / skip header (not available in TG WV).
    """
    api_key = (os.environ.get("DAYTONA_API_KEY") or "").strip()
    sandbox_id = (os.environ.get("DAYTONA_SANDBOX_ID") or "").strip()
    if not api_key or not sandbox_id:
        return None

    port = int(os.environ.get("PORT") or os.environ.get("CASINO_PORT") or 8091)
    expires = int(os.environ.get("DAYTONA_SIGNED_EXPIRES") or 3600)
    api_url = (os.environ.get("DAYTONA_API_URL") or "https://app.daytona.io/api").rstrip("/")

    cache = getattr(_mint_signed_casino_url, "_cache", None)
    now = __import__("time").time()
    if cache and cache.get("url") and cache.get("exp", 0) > now + 30:
        return cache["url"]

    import aiohttp as _aio

    endpoint = (
        f"{api_url}/sandbox/{sandbox_id}/ports/{port}/signed-preview-url"
        f"?expiresInSeconds={expires}"
    )
    try:
        timeout = _aio.ClientTimeout(total=15)
        async with _aio.ClientSession(timeout=timeout) as session:
            async with session.get(
                endpoint, headers={"Authorization": f"Bearer {api_key}"}
            ) as resp:
                body_text = await resp.text()
                if resp.status >= 300:
                    logger.warning(
                        "Daytona signed preview HTTP %s: %s",
                        resp.status,
                        body_text[:220],
                    )
                    return None
                try:
                    data = __import__("json").loads(body_text)
                except Exception:
                    logger.warning("Daytona signed preview non-JSON: %s", body_text[:220])
                    return None
        signed = data.get("url") or data.get("signedUrl") or data.get("previewUrl")
        if not signed:
            logger.warning("Daytona signed preview unexpected: %s", str(data)[:220])
            return None
        signed = str(signed).rstrip("/")
        if not signed.endswith("/casino"):
            signed = signed + "/casino"
        _mint_signed_casino_url._cache = {
            "url": signed,
            "exp": now + max(60, expires - 60),
        }
        logger.info("Minted Daytona signed casino URL (ttl~%ss)", expires)
        return signed
    except Exception as e:
        logger.warning("Daytona signed preview error: %s", e)
        return None


async def game_callback(update: Update, context):
    """Handle the 'Play' button click on a Telegram Game message."""
    query = update.callback_query
    if not query:
        return
    if not query.game_short_name:
        return

    # Priority: proxy (skips warning) > signed URL > static fallback
    base_url = (os.environ.get("CASINO_PROXY_URL") or "").strip().rstrip("/")
    if base_url:
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        if not base_url.endswith("/casino"):
            base_url = base_url + "/casino"
    else:
        base_url = await _mint_signed_casino_url()
        if not base_url:
            base_url = _get_game_url()

    chat_id = query.message.chat.id if query.message else 0
    user_id = query.from_user.id
    user_name = query.from_user.first_name or "Player"
    from urllib.parse import urlencode

    qs = urlencode({
        "chat_id": str(chat_id),
        "user_id": str(user_id),
        "name": user_name,
    })
    url = f"{base_url}?{qs}"
    logger.info("Game callback from %s: sending URL %s", user_id, url)
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

    # AI (disabled unless AI_ENABLED=true — handlers preserved for future use)
    if AI_ENABLED:
        app.add_handler(CommandHandler("ai", ai_cmd))

        # AI3 (OPHELIA)
        app.add_handler(CommandHandler("ai3", ai3_cmd))
        app.add_handler(CommandHandler("ai3stats", ai3stats_cmd))

    # BOB — son of Markov & Ophelia (always on, replaces the old AIs)
    app.add_handler(CommandHandler("bob", bob_cmd))
    app.add_handler(CommandHandler("bobstats", bobstats_cmd))

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

    # Help categories callback
    app.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help:"))

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

    # Charity & Real Estate & Economy
    app.add_handler(CommandHandler("donate", donate_cmd))
    app.add_handler(CommandHandler("charity", charity_cmd))
    app.add_handler(CommandHandler("realestate", realestate_cmd))
    app.add_handler(CommandHandler("buyproperty", buyproperty_cmd))
    app.add_handler(CommandHandler("sellproperty", sellproperty_cmd))
    app.add_handler(CommandHandler("economy", economy_cmd))

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
    app.add_handler(CommandHandler("casinoleader", casinoleader_cmd))
    app.add_handler(CommandHandler("paytax", paytax_cmd))

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

    # Gacha System
    app.add_handler(CommandHandler("roll", roll_cmd))
    app.add_handler(CommandHandler("collection", collection_cmd))
    app.add_handler(CommandHandler("sellchar", sellchar_cmd))
    app.add_handler(CommandHandler("tradechar", tradechar_cmd))
    app.add_handler(CallbackQueryHandler(gacha_callback, pattern=r"^gacha_claim:"))
    app.add_handler(CallbackQueryHandler(trade_callback, pattern=r"^trade_(accept|decline):"))

    # Clan System
    app.add_handler(CommandHandler("clan", clan_cmd))

    # Bounty System
    app.add_handler(CommandHandler("bounty", bounty_cmd))
    app.add_handler(CommandHandler("bounties", bounties_cmd))

    # Random Drops
    app.add_handler(CallbackQueryHandler(grab_callback, pattern=r"^grab:"))

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

    # ---- Crisis/suicide detection: always on, even when AI is disabled ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, crisis_listen), group=6)

    # ---- BOB: always learns from chat; speaks max 2-3x/day unprompted ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bob_listen), group=7)

    # ---- Markov AI: learn from all text messages (AI only) ----
    if AI_ENABLED:
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, markov_listen), group=2)

        # ---- OPHELIA AI: learn from all text messages (AI only) ----
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ophelia_listen), group=3)

    # ---- Game callback handler (separate group so it doesn't block other callbacks) ----
    app.add_handler(CallbackQueryHandler(game_callback), group=4)

    # ---- Random Drop counter ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, drop_counter), group=5)

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
