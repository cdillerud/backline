"""Unified scheduling and band-social navigation smoke coverage."""
import pytest
from playwright.sync_api import sync_playwright,expect
from test_collaboration import accounts
from test_browser_collaboration import account_server,sign_in

@pytest.mark.parametrize("width",[1280,390])
def test_schedule_and_band_hub_navigation(account_server,accounts,width):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={"width":width,"height":900})
        errors=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        sign_in(page,account_server,"owner")
        page.locator('[data-go="schedule"]:visible').first.click()
        expect(page.get_by_role("tab",name="Calendar",exact=True)).to_be_visible()
        page.get_by_role("tab",name="Shows",exact=True).click()
        expect(page.get_by_role("heading",name="Shows",exact=True)).to_be_visible()
        page.get_by_role("tab",name="Rehearsals",exact=True).click()
        expect(page.get_by_role("heading",name="Rehearsals",exact=True)).to_be_visible()
        page.get_by_role("tab",name="Agenda",exact=True).click()
        expect(page.get_by_role("tab",name="Agenda",exact=True)).to_have_attribute("aria-selected","true")
        page.locator('[data-go="collaboration"]:visible').first.click()
        expect(page.get_by_role("heading",name="Your band, connected")).to_be_visible()
        expect(page.get_by_role("button",name="Photos & albums")).to_be_visible()
        page.locator('[data-go="touring"]:visible').first.click()
        expect(page.get_by_role("tab",name="Itinerary",exact=True)).to_be_visible()
        page.get_by_role("tab",name="Day of show",exact=True).click()
        expect(page.get_by_role("heading",name="Tour day sheets")).to_be_visible()
        page.get_by_role("tab",name="Show production",exact=True).click()
        expect(page.get_by_role("button",name="All show packets")).to_be_visible()
        page.get_by_role("tab",name="Crew & logistics",exact=True).click()
        expect(page.get_by_role("button",name="All crew operations")).to_be_visible()
        assert not errors,errors
        browser.close()
