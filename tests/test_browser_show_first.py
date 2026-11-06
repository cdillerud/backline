"""Show-first UX acceptance with isolated band accounts; never touches live Fly."""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
from test_collaboration import accounts
from test_browser_collaboration import account_server, sign_in


@pytest.mark.parametrize("role,width", [("owner",320),("owner",390),("owner",768),("owner",1280),("member",320),("member",390),("member",1280)])
def test_calendar_opens_role_aware_show_overview(account_server, accounts, role, width):
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={"width":width,"height":850})
        errors=[]
        page.on("pageerror",lambda error: errors.append(str(error)))
        sign_in(page,account_server,role)
        assert page.locator(".mobileNav > button").count()==4
        # The compact navigation must remain usable at the smallest supported phone width.
        if width <= 660:
            expect(page.locator(".mobileNav")).to_be_visible()
            for destination in ("Home", "Calendar", "Music", "Band"):
                expect(page.locator(".mobileNav").get_by_role("button", name=destination)).to_be_visible()
        else:
            expect(page.locator(".mobileNav")).to_be_hidden()
        page.locator('[data-go="schedule"]:visible').first.click()
        expect(page.locator(".top h1")).to_have_text("Calendar")
        agenda=page.get_by_role("region",name="Upcoming dates")
        expect(agenda).to_be_visible()
        show_link=agenda.locator("[data-show-overview]").first
        expect(show_link).to_be_visible()
        show_link.click()
        overview=page.get_by_role("region",name="Show overview")
        expect(overview).to_be_visible()
        expect(page.locator(".top h1")).to_have_text("Show")
        assert overview.locator(".showFirstFact").count()==4
        expect(overview.get_by_role("button",name="Open Gig Day")).to_be_visible()
        expect(overview.get_by_role("button",name="My RSVP:",exact=False)).to_be_visible()
        expect(overview.get_by_role("button",name="Open setlists")).to_be_visible()
        expect(overview.get_by_role("button",name="See my tasks")).to_be_visible()
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth+1")
        if role=="owner":
            expect(overview.locator(".showFirstManage summary")).to_be_visible()
            overview.locator(".showFirstManage summary").click()
            expect(overview.locator("[data-show-gig]")).to_be_visible()
        else:
            assert overview.locator(".showFirstManage").count()==0
            assert page.locator(".manageNav [data-go='manage']").count()==0
            assert page.locator(".accountMenuItems [data-go='manage']").count()==0
        output=Path("artifacts/gigday")
        output.mkdir(exist_ok=True,parents=True)
        page.screenshot(path=str(output/f"show-first-{role}-{width}.png"),full_page=True)
        overview.get_by_role("button",name="Open Gig Day").click()
        expect(page.get_by_role("region",name="Musician gig-day workspace")).to_be_visible()
        assert not errors,errors
        browser.close()
