"""Browser: slots win/lose paths with seeded PRNG."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")


def test_slots_spin_changes_balance(page):
    page.locator('[data-testid="nav-slots"]').click()
    before = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    page.fill('[data-testid="slots-bet"]', "10")
    page.click('[data-testid="slots-spin"]')
    # wait for spin animation + settle
    page.wait_for_timeout(2000)
    after = int(page.locator('[data-testid="balance"]').inner_text().replace(",", ""))
    # either lost 10 or won something — must not stay exactly same only if still spinning
    result = page.locator('[data-testid="slots-result"]').inner_text()
    assert result
    assert after >= 0
    # balance should have been touched (bet escrowed at minimum)
    assert after != before or "WIN" in result
