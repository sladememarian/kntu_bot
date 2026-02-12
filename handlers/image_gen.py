# ==========================================
# KNTU Bot 25 — Image Generator (Google Gemini Imagen)
# ==========================================

import io
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from storage import get_lang, get_debug
from strings import STRINGS

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


async def imagine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang = get_lang(chat.id)
    s = STRINGS[lang]

    if not context.args:
        await update.message.reply_text(s["imagine_usage"], parse_mode="Markdown")
        return

    if not client:
        await update.message.reply_text(s["imagine_error"], parse_mode="Markdown")
        return

    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text(s["imagine_generating"], parse_mode="Markdown")

    try:
        response = await client.aio.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            await status_msg.delete()
            await update.message.reply_photo(
                photo=io.BytesIO(image_bytes),
                caption=f"🎨 {prompt}",
            )
        else:
            await status_msg.edit_text(s["imagine_error"], parse_mode="Markdown")
    except Exception as e:
        error_text = s["imagine_error"]
        if get_debug():
            error_text += f"\n\nDebug: `{str(e)[:200]}`"
        await status_msg.edit_text(error_text, parse_mode="Markdown")
