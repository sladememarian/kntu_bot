"""Browser: wallet load + offline lockout."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")


def test_balance_loads_online(page):
    bal = page.locator('[data-testid="balance"]').inner_text()
    assert bal.replace(",", "") == "1000"
    assert "online" in page.locator('[data-testid="sync-dot"]').get_attribute("class")


def test_offline_locks_buttons(page):
    page.route("**/api/balance**", lambda route: route.abort())
    page.evaluate("() => fetchBalance()")
    page.wait_for_timeout(500)
    banner = page.locator('[data-testid="offline-banner"]')
    # may take a moment for class
    page.wait_for_function(
        "() => document.getElementById('offlineBanner')?.classList.contains('show')",
        timeout=5000,
    )
    assert banner.is_visible()
    # spin should be disabled via data-need-online
    page.locator('[data-testid="nav-slots"]').click()
    btn = page.locator('[data-testid="slots-spin"]')
    assert btn.is_disabled()


def test_bet_over_balance_no_negative(page):
    page.locator('[data-testid="nav-slots"]').click()
    page.fill('[data-testid="slots-bet"]', "99999")
    page.click('[data-testid="slots-spin"]')
    page.wait_for_timeout(300)
    text = page.locator('[data-testid="slots-result"]').inner_text().lower()
    assert "enough" in text or "not" in text
    bal = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    assert bal == 1000
