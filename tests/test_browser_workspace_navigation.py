"""Authenticated four-destination musician UX smoke test at practical device widths.

Uses disposable synthetic test accounts; does not access the live Fly preview.
"""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
from test_collaboration import accounts
from test_browser_collaboration import account_server, sign_in


@pytest.mark.parametrize("width", [320, 390, 768, 1280])
def test_primary_workspaces_are_navigable_without_document_overflow(
        account_server, accounts, width):
    labels = [
        ("dashboard", "Home"),
        ("schedule", "Calendar"),
        ("songs", "Song Library"),
        ("collaboration", "Bandmates"),
    ]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 850})
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        sign_in(page, account_server, "owner")
        if width == 320:
            # All global actions sit on the same narrow header tools row.
            assert page.evaluate("""() => {
                const picker=document.querySelector('#mobileBandPicker').getBoundingClientRect();
                const menu=document.querySelector('.accountMenu summary').getBoundingClientRect();
                return Math.abs(picker.top-menu.top)<16 && menu.right <= innerWidth + 1;
            }""")
        output = Path("artifacts/gigday")
        output.mkdir(parents=True, exist_ok=True)
        for route, heading in labels:
            if route != "dashboard":
                # Mobile navigation switches via the bottom rail, tablet and
                # desktop use the primary sidebar; both share the same data-go.
                nav = page.locator('[data-go="' + route + '"]:visible').first
                expect(nav).to_be_visible()
                nav.click()
            expect(page.locator(".top h1")).to_have_text(heading)
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), f"Document overflows at {width}px in {route}"
            assert page.evaluate(
                "() => [...document.querySelectorAll('.mobileNav button')].every("
                "b => b.getBoundingClientRect().width >= 0)"
            )
            if route in ("dashboard", "songs", "schedule", "collaboration"):
                page.screenshot(path=str(output / f"workspace-{route}-{width}.png"), full_page=True)
        # Management is a separate, authorized surface, never a fifth primary tab.
        assert page.locator('nav[aria-label="Primary workspaces"] > button').count()==4
        page.locator('.accountMenu summary').click()
        page.locator('.accountMenu [data-go="manage"]').click()
        expect(page.locator('.top h1')).to_have_text('Manage')
        assert page.locator('.manageTool[data-go="touring"]').count()==1
        assert page.locator('.manageTool[data-go="finance"]').count()==1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        ), f"Management overflows at {width}px"
        assert not failures, f"Client JavaScript errors at {width}px: {failures}"
        browser.close()


def test_member_workspace_navigation_does_not_offer_finance(account_server, accounts):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 850})
        sign_in(page, account_server, "member")
        expect(page.locator(".top h1")).to_have_text("Home")
        assert page.locator('.mobileNav [data-go="finance"]').count() == 0
        page.locator('.mobileNav [data-go="schedule"]').click()
        expect(page.locator('.top h1')).to_have_text('Calendar')
        assert page.locator('[data-action="event"]').count() == 0
        assert page.locator('nav[aria-label="Primary workspaces"] [data-go="finance"]').count() == 0
        assert page.locator('[data-go="manage"]').count() == 0
        assert page.locator('.calendarDayAdd').count() == 0
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        browser.close()
