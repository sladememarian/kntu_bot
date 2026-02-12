# ==========================================
# KNTU Bot 25 — Music Finder (actual audio)
# ==========================================

import io
import random
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes

from storage import get_lang
from strings import STRINGS


async def music_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /music <name> — Search for a song and send it as audio.
    If no argument, suggest a random song.
    """
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if not context.args:
        song = random.choice(SUGGESTIONS[lang])
        if lang == "fa":
            text = (
                f"🎵 *{song['title']}*\n"
                f"🎤 خواننده: {song['artist']}\n"
                f"📂 ژانر: {song['genre']}\n\n"
                f"🔎 برای دانلود بنویس: `/music {song['artist']} {song['title']}`"
            )
        else:
            text = (
                f"🎵 *{song['title']}*\n"
                f"🎤 Artist: {song['artist']}\n"
                f"📂 Genre: {song['genre']}\n\n"
                f"🔎 To download, type: `/music {song['artist']} {song['title']}`"
            )
        await update.message.reply_text(
            s["music_prefix"] + "\n" + text,
            parse_mode="Markdown",
        )
        return

    query = " ".join(context.args)
    if lang == "fa":
        wait_msg = await update.message.reply_text("🔍 در حال جستجو...")
    else:
        wait_msg = await update.message.reply_text("🔍 Searching...")

    audio_url = None
    title = None
    artist = None
    duration = 0
    deezer_link = ""

    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.deezer.com/search"
            params = {"q": query, "limit": 5}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("data", [])
                    if results:
                        track = results[0]
                        audio_url = track.get("preview")
                        title = track.get("title", "Unknown")
                        artist = track.get("artist", {}).get("name", "Unknown")
                        duration = track.get("duration", 0)
                        deezer_link = track.get("link", "")
    except Exception:
        pass

    if audio_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        audio_bytes = await resp.read()

                        if lang == "fa":
                            caption = (
                                f"🎵 *{title}*\n"
                                f"🎤 {artist}\n"
                                f"⏱ {duration // 60}:{duration % 60:02d}\n"
                            )
                            if deezer_link:
                                caption += f"🔗 [لینک کامل]({deezer_link})"
                        else:
                            caption = (
                                f"🎵 *{title}*\n"
                                f"🎤 {artist}\n"
                                f"⏱ {duration // 60}:{duration % 60:02d}\n"
                            )
                            if deezer_link:
                                caption += f"🔗 [Full track]({deezer_link})"

                        audio_file = io.BytesIO(audio_bytes)
                        audio_file.name = f"{artist} - {title}.mp3"

                        await update.message.reply_audio(
                            audio=audio_file,
                            title=title,
                            performer=artist,
                            duration=min(duration, 30),
                            caption=caption,
                            parse_mode="Markdown",
                        )
                        await wait_msg.delete()
                        return
        except Exception:
            pass

    if title and artist:
        if lang == "fa":
            text = (
                f"🎵 *{title}*\n"
                f"🎤 {artist}\n\n"
                f"⚠️ نتونستم فایل صوتی رو بفرستم.\n"
            )
            if deezer_link:
                text += f"🔗 [گوش بده در Deezer]({deezer_link})"
        else:
            text = (
                f"🎵 *{title}*\n"
                f"🎤 {artist}\n\n"
                f"⚠️ Couldn't send audio file.\n"
            )
            if deezer_link:
                text += f"🔗 [Listen on Deezer]({deezer_link})"
        await wait_msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        if lang == "fa":
            await wait_msg.edit_text("❌ آهنگی پیدا نشد! دوباره با اسم دیگه امتحان کن.")
        else:
            await wait_msg.edit_text("❌ No music found! Try a different name.")


SUGGESTIONS = {
    "fa": [
        {"title": "سلطان قلبها", "artist": "ابی", "genre": "پاپ"},
        {"title": "پرنده", "artist": "مهراد هیدن", "genre": "رپ"},
        {"title": "بارون", "artist": "شادمهر عقیلی", "genre": "پاپ"},
        {"title": "دلقک", "artist": "محسن یگانه", "genre": "پاپ"},
        {"title": "دریا", "artist": "گوگوش", "genre": "کلاسیک پاپ"},
        {"title": "دوست دارم", "artist": "سیروان خسروی", "genre": "پاپ"},
        {"title": "عشق من", "artist": "فرامرز اصلانی", "genre": "کلاسیک پاپ"},
    ],
    "en": [
        {"title": "Bohemian Rhapsody", "artist": "Queen", "genre": "Rock"},
        {"title": "Blinding Lights", "artist": "The Weeknd", "genre": "Pop"},
        {"title": "Lose Yourself", "artist": "Eminem", "genre": "Hip-Hop"},
        {"title": "Shape of You", "artist": "Ed Sheeran", "genre": "Pop"},
        {"title": "Hotel California", "artist": "Eagles", "genre": "Rock"},
        {"title": "Levitating", "artist": "Dua Lipa", "genre": "Pop"},
        {"title": "As It Was", "artist": "Harry Styles", "genre": "Pop"},
        {"title": "Rolling in the Deep", "artist": "Adele", "genre": "Pop/Soul"},
    ],
}
