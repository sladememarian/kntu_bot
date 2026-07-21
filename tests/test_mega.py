"""Browser: mega slots."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")


def test_mega_spin(page):
    page.locator('[data-testid="nav-mega"]').click()
    page.fill('[data-testid="mega-bet"]', "50")
    before = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    page.click('[data-testid="mega-spin"]')
    page.wait_for_timeout(2200)
    after = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    result = page.locator('[data-testid="mega-result"]').inner_text()
    assert result
    assert after >= 0
    assert after <= before + 50 * 50  # sanity cap
