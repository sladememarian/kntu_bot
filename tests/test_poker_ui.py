"""Browser: 4-context poker fold-to-win flow."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

from tests.conftest import MULBERRY32


def test_poker_four_players_fold_winner(server_base_url, seed_wallet):
    chat_id = 4242
    players = [
        (501, "Alice"),
        (502, "Bob"),
        (503, "Cara"),
        (504, "Dan"),
    ]
    for uid, _ in players:
        seed_wallet(chat_id, uid, 500)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pages = []
        for uid, name in players:
            ctx = browser.new_context(viewport={"width": 420, "height": 800})
            page = ctx.new_page()
            page.add_init_script(MULBERRY32)
            url = f"{server_base_url}/casino?chat_id={chat_id}&user_id={uid}&name={name}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector('[data-testid="balance"]')
            page.locator('[data-testid="nav-poker"]').click()
            page.wait_for_timeout(300)
            page.fill('[data-testid="poker-bet"]', "50")
            page.click('[data-testid="poker-join"]')
            page.wait_for_timeout(400)
            pages.append((uid, name, page, ctx))

        # last page should show start
        last = pages[-1][2]
        last.wait_for_selector('[data-testid="poker-start"]', timeout=5000)
        last.click('[data-testid="poker-start"]')
        last.wait_for_timeout(800)

        # fold until winner
        guard = 0
        winner_text = ""
        while guard < 30:
            guard += 1
            progressed = False
            for uid, name, page, _ in pages:
                # refresh status via poll
                page.evaluate("() => pollPokerStatus && pollPokerStatus()")
                page.wait_for_timeout(200)
                w = page.locator('[data-testid="poker-winner"]')
                if w.count() and w.is_visible():
                    winner_text = w.inner_text()
                    progressed = True
                    break
                fold = page.locator('[data-testid="poker-fold"]')
                if fold.count() and fold.is_visible() and fold.is_enabled():
                    fold.click()
                    page.wait_for_timeout(300)
                    progressed = True
            if winner_text:
                break
            if not progressed:
                pages[0][2].wait_for_timeout(500)

        assert winner_text, "expected poker-winner banner"
        assert "Winner" in winner_text or "🏆" in winner_text

        for _, _, _, ctx in pages:
            ctx.close()
        browser.close()
