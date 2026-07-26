"""Casino public URL helpers."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Avoid importing full telegram app side effects where possible
os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("DISABLE_AIOHTTP_SERVER", "true")
os.environ.setdefault("DATABASE_URL", "")


def test_get_game_url_prefers_signed(monkeypatch):
    import app as bot_app

    monkeypatch.setenv("CASINO_SIGNED_URL", "https://8091-tok.example.eu")
    monkeypatch.delenv("WEB_URL", raising=False)
    url = bot_app._get_game_url()
    assert url == "https://8091-tok.example.eu/casino"


def test_get_game_url_web_url(monkeypatch):
    import app as bot_app

    monkeypatch.delenv("CASINO_SIGNED_URL", raising=False)
    monkeypatch.delenv("WEB_URL_SIGNED", raising=False)
    monkeypatch.setenv("WEB_URL", "https://8091-abc.daytonaproxy01.eu")
    url = bot_app._get_game_url()
    assert url.endswith("/casino")
    assert "8091-abc" in url


def test_create_web_app_routes():
    import app as bot_app

    web_app = bot_app.create_web_app()
    paths = sorted({r.resource.canonical for r in web_app.router.routes()})
    assert "/casino" in paths or any("casino" in p for p in paths)
    assert any("balance" in p for p in paths)
