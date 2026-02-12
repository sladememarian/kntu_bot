# ==========================================
# KNTU Bot 25 — XO (Tic-Tac-Toe) Game
# ==========================================

import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_lang, get_balance, add_balance
from strings import STRINGS

# Active games: key = f"{chat_id}:{msg_id}" -> game state
_games = {}

EMPTY = "⬜"
X_MARK = "❌"
O_MARK = "⭕"

BET_AMOUNT = 100


def _new_board():
    return [[EMPTY] * 3 for _ in range(3)]


def _board_buttons(board, game_key):
    buttons = []
    for r in range(3):
        row = []
        for c in range(3):
            cell = board[r][c]
            cb_data = f"xo:{game_key}:{r}:{c}"
            row.append(InlineKeyboardButton(cell, callback_data=cb_data))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _check_winner(board):
    """Return X_MARK, O_MARK, 'draw', or None."""
    for mark in (X_MARK, O_MARK):
        # Rows
        for r in range(3):
            if all(board[r][c] == mark for c in range(3)):
                return mark
        # Cols
        for c in range(3):
            if all(board[r][c] == mark for r in range(3)):
                return mark
        # Diagonals
        if all(board[i][i] == mark for i in range(3)):
            return mark
        if all(board[i][2 - i] == mark for i in range(3)):
            return mark
    # Draw?
    if all(board[r][c] != EMPTY for r in range(3) for c in range(3)):
        return "draw"
    return None


# --------- /xo (start game) ---------
async def xo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]
    user = update.effective_user

    if not update.message.reply_to_message:
        await update.message.reply_text(s["xo_usage"], parse_mode="Markdown")
        return

    opponent = update.message.reply_to_message.from_user
    if opponent.id == user.id:
        await update.message.reply_text(s["xo_self"], parse_mode="Markdown")
        return
    if opponent.is_bot:
        await update.message.reply_text(s["xo_bot"], parse_mode="Markdown")
        return

    # Check balances
    user_bal = get_balance(chat.id, user.id)
    opp_bal = get_balance(chat.id, opponent.id)

    has_bet = user_bal >= BET_AMOUNT and opp_bal >= BET_AMOUNT

    board = _new_board()

    # Randomly decide who goes first
    if random.random() < 0.5:
        x_player = {"id": user.id, "name": user.first_name or "User"}
        o_player = {"id": opponent.id, "name": opponent.first_name or "User"}
    else:
        x_player = {"id": opponent.id, "name": opponent.first_name or "User"}
        o_player = {"id": user.id, "name": user.first_name or "User"}

    # Send board message
    if lang == "fa":
        text = (
            f"🎮 *بازی XO*\n\n"
            f"{X_MARK} {x_player['name']}\n"
            f"{O_MARK} {o_player['name']}\n\n"
            f"نوبت: *{x_player['name']}* {X_MARK}"
        )
        if has_bet:
            text += f"\n💰 شرط: *{BET_AMOUNT}* $"
    else:
        text = (
            f"🎮 *XO Game*\n\n"
            f"{X_MARK} {x_player['name']}\n"
            f"{O_MARK} {o_player['name']}\n\n"
            f"Turn: *{x_player['name']}* {X_MARK}"
        )
        if has_bet:
            text += f"\n💰 Bet: *{BET_AMOUNT}* $"

    # Temporary key, will update after message is sent
    msg = await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=_board_buttons(board, "TEMP"),
    )

    game_key = f"{chat.id}:{msg.message_id}"
    game = {
        "board": board,
        "x": x_player,
        "o": o_player,
        "turn": "x",
        "chat_id": chat.id,
        "msg_id": msg.message_id,
        "has_bet": has_bet,
    }
    _games[game_key] = game

    # Update buttons with correct key
    await msg.edit_reply_markup(reply_markup=_board_buttons(board, game_key))


# --------- XO callback handler ---------
async def xo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data  # xo:chat_id:msg_id:row:col

    parts = data.split(":")
    if len(parts) != 5 or parts[0] != "xo":
        await query.answer()
        return

    game_key = f"{parts[1]}:{parts[2]}"
    row, col = int(parts[3]), int(parts[4])

    game = _games.get(game_key)
    if not game:
        await query.answer("Game expired!" if get_lang(int(parts[1])) == "en" else "بازی تموم شده!", show_alert=True)
        return

    lang = get_lang(game["chat_id"])
    user_id = query.from_user.id

    # Check it's the right player's turn
    current = game["x"] if game["turn"] == "x" else game["o"]
    if user_id != current["id"]:
        msg = "It's not your turn!" if lang == "en" else "نوبت تو نیست!"
        await query.answer(msg, show_alert=True)
        return

    board = game["board"]
    if board[row][col] != EMPTY:
        msg = "Cell taken!" if lang == "en" else "این خونه پر شده!"
        await query.answer(msg, show_alert=True)
        return

    # Place mark
    mark = X_MARK if game["turn"] == "x" else O_MARK
    board[row][col] = mark

    winner = _check_winner(board)

    if winner:
        # Game over
        del _games[game_key]

        if winner == "draw":
            if lang == "fa":
                text = (
                    f"🎮 *بازی XO — مساوی!*\n\n"
                    f"{X_MARK} {game['x']['name']}\n"
                    f"{O_MARK} {game['o']['name']}\n\n"
                    f"🤝 بازی مساوی شد!"
                )
            else:
                text = (
                    f"🎮 *XO Game — Draw!*\n\n"
                    f"{X_MARK} {game['x']['name']}\n"
                    f"{O_MARK} {game['o']['name']}\n\n"
                    f"🤝 It's a draw!"
                )
        else:
            w = game["x"] if winner == X_MARK else game["o"]
            l = game["o"] if winner == X_MARK else game["x"]

            if game["has_bet"]:
                add_balance(game["chat_id"], w["id"], BET_AMOUNT)
                add_balance(game["chat_id"], l["id"], -BET_AMOUNT)
                w_bal = get_balance(game["chat_id"], w["id"])

            if lang == "fa":
                text = (
                    f"🎮 *بازی XO — تموم شد!*\n\n"
                    f"{X_MARK} {game['x']['name']}\n"
                    f"{O_MARK} {game['o']['name']}\n\n"
                    f"🏆 برنده: *{w['name']}*! {winner}"
                )
                if game["has_bet"]:
                    text += f"\n💰 +{BET_AMOUNT}$ (موجودی: {w_bal}$)"
            else:
                text = (
                    f"🎮 *XO Game — Finished!*\n\n"
                    f"{X_MARK} {game['x']['name']}\n"
                    f"{O_MARK} {game['o']['name']}\n\n"
                    f"🏆 Winner: *{w['name']}*! {winner}"
                )
                if game["has_bet"]:
                    text += f"\n💰 +{BET_AMOUNT}$ (Balance: {w_bal}$)"

        # Show final board (disabled buttons)
        buttons = []
        for r in range(3):
            row_btns = []
            for c in range(3):
                row_btns.append(InlineKeyboardButton(board[r][c], callback_data="xo_done"))
            buttons.append(row_btns)

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        # Switch turn
        game["turn"] = "o" if game["turn"] == "x" else "x"
        next_player = game["x"] if game["turn"] == "x" else game["o"]
        next_mark = X_MARK if game["turn"] == "x" else O_MARK

        if lang == "fa":
            text = (
                f"🎮 *بازی XO*\n\n"
                f"{X_MARK} {game['x']['name']}\n"
                f"{O_MARK} {game['o']['name']}\n\n"
                f"نوبت: *{next_player['name']}* {next_mark}"
            )
            if game["has_bet"]:
                text += f"\n💰 شرط: *{BET_AMOUNT}* $"
        else:
            text = (
                f"🎮 *XO Game*\n\n"
                f"{X_MARK} {game['x']['name']}\n"
                f"{O_MARK} {game['o']['name']}\n\n"
                f"Turn: *{next_player['name']}* {next_mark}"
            )
            if game["has_bet"]:
                text += f"\n💰 Bet: *{BET_AMOUNT}* $"

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=_board_buttons(board, game_key),
        )

    await query.answer()
