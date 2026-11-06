"""Cross-page professional design-system smoke tests on synthetic accounts."""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
from test_collaboration import accounts
from test_browser_collaboration import account_server, sign_in


@pytest.mark.parametrize("width", [390, 1280, 2560])
def test_shared_chrome_typography_cards_and_controls(account_server, accounts, width):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        sign_in(page, account_server, "owner")
        for section, title in [
            ("dashboard", "Home"), ("schedule", "Calendar"), ("songs", "Song Library"),
            ("collaboration", "Band"), ("manage", "Manage"),
        ]:
            # Navigate within the same authenticated, band-scoped workspace.
            page.evaluate("(section) => { state.section=section; render(); }", section)
            expect(page.locator(".top h1")).to_have_text(title)
            values = page.evaluate("""() => {
                const root = getComputedStyle(document.documentElement);
                const heading = getComputedStyle(document.querySelector('.top h1'));
                const content = getComputedStyle(document.querySelector('.content'));
                return {
                    token: root.getPropertyValue('--ui-control-radius').trim(),
                    titleSize: heading.fontSize,
                    bodySize: content.fontSize,
                    cards: [...document.querySelectorAll('.content .panel,.content .manageTile')].slice(0,8)
                        .map(el => getComputedStyle(el).borderRadius),
                };
            }""")
            assert values["token"] == "8px"
            assert values["titleSize"] == ("23px" if width <= 660 else "26px")
            assert values["bodySize"] == "14px"
            assert all(value == "11px" for value in values["cards"])
            if section == "manage":
                tiles = page.locator(".manageTile")
                assert tiles.count() >= 5
                assert page.evaluate("""() => [...document.querySelectorAll('.manageTile')].every(
                    el => el.getBoundingClientRect().height >= 88)""")
                assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth+1")
            if section in {"dashboard", "schedule", "manage"}:
                folder = Path("artifacts/design-system")
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"{section}-owner-{width}.png"), full_page=True)
        assert not errors, errors
        browser.close()
