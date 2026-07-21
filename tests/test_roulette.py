"""Browser: roulette spin + number grid."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")


def test_roulette_grid_and_spin(page):
    page.locator('[data-testid="nav-roulette"]').click()
    # number grid 0..36
    assert page.locator('[data-testid="roul-num-0"]').count() == 1
    assert page.locator('[data-testid="roul-num-36"]').count() == 1
    page.click('[data-testid="roul-red"]')
    page.fill('[data-testid="roul-bet"]', "15")
    before = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    page.click('[data-testid="roul-spin"]')
    # animation ~3s
    page.wait_for_timeout(3800)
    after = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    result = page.locator('[data-testid="roul-result"]').inner_text()
    assert result
    assert after >= 0
    # bet was at least attempted
    assert after != before or "WIN" in result
