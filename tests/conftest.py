"""Shared fixtures for casino API + browser e2e tests."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest

# Point storage at a temp JSON file BEFORE importing app/storage.
_TMPDIR = tempfile.mkdtemp(prefix="kntu_casino_test_")
_DATA = os.path.join(_TMPDIR, "data.json")
os.environ["DATABASE_URL"] = ""
os.environ["DATA_FILE"] = _DATA
os.environ["DISABLE_AIOHTTP_SERVER"] = "true"  # we start our own runner
os.environ.setdefault("BOT_TOKEN", "test-token-not-used")

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiohttp import web  # noqa: E402
from storage import set_balance, get_balance  # noqa: E402
import app as bot_app  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server_base_url():
    """Run create_web_app() on a random localhost port in a background thread."""
    port = _free_port()
    web_app = bot_app.create_web_app()
    runner = web.AppRunner(web_app)
    loop_ready = threading.Event()
    holder = {"loop": None, "error": None}

    def _run():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        holder["loop"] = loop

        async def _start():
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", port)
            await site.start()

        try:
            loop.run_until_complete(_start())
            loop_ready.set()
            loop.run_forever()
        except Exception as e:
            holder["error"] = e
            loop_ready.set()
        finally:
            try:
                loop.run_until_complete(runner.cleanup())
            except Exception:
                pass

    t = threading.Thread(target=_run, name="aiohttp-test", daemon=True)
    t.start()
    if not loop_ready.wait(10):
        raise RuntimeError("test server failed to start")
    if holder["error"]:
        raise RuntimeError(f"test server error: {holder['error']}")
    base = f"http://127.0.0.1:{port}"
    # warm-up
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(base + "/casino", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
    yield base
    if holder["loop"]:
        holder["loop"].call_soon_threadsafe(holder["loop"].stop)


@pytest.fixture
def seed_wallet():
    def _seed(chat_id: int, user_id: int, amount: int):
        set_balance(chat_id, user_id, amount)
        return get_balance(chat_id, user_id)
    return _seed


# Seeded PRNG injected into every browser page for deterministic outcomes.
MULBERRY32 = """
(() => {
  let a = 0xC0FFEE;
  function mulberry32(){
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
  Math.random = mulberry32;
})();
"""


@pytest.fixture(scope="session")
def browser_type_launch_args():
    return {"headless": True}


@pytest.fixture
def page(server_base_url, seed_wallet):
    """Playwright page pointed at casino with seeded wallet + PRNG."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    chat_id, user_id = 9001, 42
    seed_wallet(chat_id, user_id, 1000)
    url = f"{server_base_url}/casino?chat_id={chat_id}&user_id={user_id}&name=Tester"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 420, "height": 800})
        page = context.new_page()
        page.add_init_script(MULBERRY32)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector('[data-testid="balance"]')
        # wait until online
        page.wait_for_function(
            "() => document.getElementById('syncDot')?.classList.contains('online')",
            timeout=5000,
        )
        yield page
        context.close()
        browser.close()
