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
        expect(page.locator("#calendarMonth")).to_be_visible()
        assert page.get_by_role("tablist",name="Schedule views").count()==0
        assert page.locator("[data-calendar-day]").count()>=28
        expect(page.get_by_role("button",name="+ Add event")).to_be_visible()
        # Single-tap event creation works in both desktop and mobile layouts.
        first_day=page.locator("[data-calendar-day]").first
        selected_date=first_day.get_attribute("data-calendar-day")
        first_day.get_by_role("button",name="Add event on "+selected_date).click()
        expect(page.locator("#entryForm input[name='date']")).to_have_value(selected_date)
        page.locator("#entryForm [data-action='close']").click()
        # All event types are available directly on the single calendar.
        page.get_by_role("button",name="+ Add event").click()
        expect(page.get_by_label("Event type")).to_be_visible()
        page.locator("#entryForm [data-action='close']").click()
        page.locator('[data-go="collaboration"]:visible').first.click()
        expect(page.get_by_role("heading",name="Conversations",exact=True)).to_be_visible()
        expect(page.locator(".hubChatWorkspace")).to_be_visible()
        assert page.locator(".hubDisclosure[open]").count()==0
        # Discussions use a vertically scrolling conversation and a bottom composer.
        conversation=page.locator(".messenger")
        if conversation.count():
            expect(conversation.locator("#threadPosts[role='log']")).to_be_visible()
            expect(conversation.locator(".messengerHeader")).to_be_visible()
            if conversation.locator("#discussionForm").count():
                expect(conversation.locator("#discussionReply")).to_be_visible()
                assert conversation.locator(".messengerComposer").evaluate(
                    "(el) => el.getBoundingClientRect().top >= document.querySelector('#threadPosts').getBoundingClientRect().bottom"
                )
        expect(page.get_by_role("navigation",name="Global tools")).to_be_visible()
        expect(page.get_by_role("button",name="My Tasks")).to_be_visible()
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
