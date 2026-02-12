import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
NEWS_CHANNELS = [x.strip() for x in os.getenv("NEWS_CHANNELS", "").split(",") if x.strip()]
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "fa")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

BOT_NAME = "kntu_bot25"
