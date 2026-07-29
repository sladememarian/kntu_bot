# ==========================================
# KNTU Bot 25 — BOB (/bob)
#   /bob         — redirects to @collabob25_bot
#   /bobstats    — disabled
# ==========================================

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("kntu_bot25.bob")


async def bob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text("@collabob25_bot")


async def bobstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text("")
