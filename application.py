# ==========================================
# WSGI Entry Point for Azure App Service (fallback)
# Preferred startup: python3 app.py
# Gunicorn command: gunicorn --bind=0.0.0.0 --timeout 600 --workers 1 application:app
# ==========================================

import logging
import threading
import os
import sys
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kntu_bot25.wsgi")

_bot_started = False
_bot_lock = threading.Lock()


def _start_bot():
    global _bot_started
    with _bot_lock:
        if _bot_started:
            return
        _bot_started = True

    logger.info("WSGI: Bot thread starting...")
    sys.path.insert(0, os.path.dirname(__file__))

    try:
        from app import main
        logger.info("WSGI: Calling main()...")
        main()
    except Exception as e:
        logger.error("WSGI: Failed to start bot: %s", e)
        logger.error(traceback.format_exc())


logger.info("WSGI: Starting bot background thread...")
_thread = threading.Thread(target=_start_bot, daemon=False)
_thread.start()


def app(environ, start_response):
    status = "200 OK"
    headers = [("Content-Type", "text/plain")]
    start_response(status, headers)
    return [b"KNTU Bot 25 is running"]
