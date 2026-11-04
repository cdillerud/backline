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
        # Band-first landing page reuses existing authorized records and working routes.
        page.locator('[data-go="dashboard"]:visible').first.click()
        expect(page.get_by_text("Your band home")).to_be_visible()
        expect(page.locator(".bandHomeStats .bandHomeStat")).to_have_count(5)
        expect(page.get_by_role("heading",name="Recent conversations")).to_be_visible()
        expect(page.get_by_role("heading",name="Availability & RSVPs")).to_be_visible()
        expect(page.get_by_role("heading",name="Music & preparation")).to_be_visible()
        expect(page.get_by_role("heading",name="Next show preparation")).to_be_visible()
        if page.locator("[data-home-show-setlists]").count():
            page.locator("[data-home-show-setlists]").first.click()
            expect(page.get_by_role("heading",name="Setlist Studio",exact=True)).to_be_visible()
            page.locator('[data-go="dashboard"]:visible').first.click()
            page.locator("[data-home-show-tasks]").first.click()
            expect(page.get_by_role("heading",name="Tasks",exact=True)).to_be_visible()
            page.locator('[data-go="dashboard"]:visible').first.click()
        # Manager-facing show checklist is sourced from existing production records.
        if page.locator("[data-home-crew]").count():
            expect(page.get_by_text("Venue advance",exact=True)).to_be_visible()
            expect(page.get_by_text("Production documents",exact=True)).to_be_visible()
            expect(page.get_by_text("Stage & inputs",exact=True)).to_be_visible()
            expect(page.get_by_text("Guest requests",exact=True)).to_be_visible()
            expect(page.get_by_text("Lodging",exact=True)).to_be_visible()
            page.locator("[data-home-crew]").first.click()
            expect(page.get_by_text("Show Operations",exact=True).first).to_be_visible()
            page.locator('[data-go="dashboard"]:visible').first.click()
        expect(page.get_by_role("heading",name="Recent band activity")).to_be_visible()
        if page.locator("[data-home-thread]").count():
            page.locator("[data-home-thread]").first.click()
            expect(page.get_by_role("heading",name="Conversations",exact=True)).to_be_visible()
            page.locator('[data-go="dashboard"]:visible').first.click()
        if page.locator("[data-home-event]").count():
            page.locator("[data-home-event]").first.click()
            expect(page.get_by_role("dialog",name="Event details:",exact=False)).to_be_visible()
            expect(page.locator("#calendarAttendance")).to_be_visible()
            page.get_by_role("button",name="Close event details").click()
            page.locator('[data-go="dashboard"]:visible').first.click()
        expect(page.get_by_role("button",name="+ Add song")).to_be_visible()
        expect(page.get_by_role("button",name="+ Add event")).to_be_visible()
        page.locator(".bandHomeQuickActions [data-action='song']").click()
        expect(page.get_by_text("Add song",exact=True)).to_be_visible()
        page.locator("#entryForm [data-action='close']").click()
        page.locator('[data-go="schedule"]:visible').first.click()
        expect(page.locator("#calendarMonth")).to_be_visible()
        assert page.get_by_role("tablist",name="Schedule views").count()==0
        assert page.locator("[data-calendar-day]").count()>=28
        expect(page.get_by_role("button",name="+ Add event")).to_be_visible()
        # Single-tap event creation works in both desktop and mobile layouts.
        first_day=page.locator("[data-calendar-day]").first
        # Calendar supports keyboard day-to-day and week-to-week navigation.
        first_day.focus()
        first_day.press("ArrowRight")
        expect(page.locator("[data-calendar-day]").nth(1)).to_be_focused()
        page.locator("[data-calendar-day]").nth(1).press("ArrowDown")
        expect(page.locator("[data-calendar-day]").nth(8)).to_be_focused()
        page.locator("[data-calendar-day]").nth(8).press("ArrowUp")
        expect(page.locator("[data-calendar-day]").nth(1)).to_be_focused()
        first_day.focus()
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
