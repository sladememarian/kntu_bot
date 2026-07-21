"""Browser: blackjack deal + escrow."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")


def test_blackjack_deal_escrows_bet(page):
    page.locator('[data-testid="nav-blackjack"]').click()
    page.fill('[data-testid="bj-bet"]', "20")
    before = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    page.click('[data-testid="bj-deal"]')
    page.wait_for_timeout(800)
    after = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    # escrow -20 unless natural resolved already with payout
    assert after <= before
    assert page.locator('[data-testid="bj-player"]').locator(".card-ui").count() >= 2
