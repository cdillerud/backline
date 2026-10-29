"""Real Chromium smoke test of the Backline preview UI against an isolated DB.

Run via: BACKLINE_LOCAL_DEV=1 python -m pytest tests/test_browser_smoke.py -q
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

def test_browser_navigation_and_gig_studio(tmp_path):
    from playwright.sync_api import sync_playwright, expect
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    env={**os.environ,"BACKLINE_DB":str(tmp_path/"browser.sqlite"),
         "BACKLINE_LOCAL_DEV":"1","BACKLINE_ACCOUNTS_ENABLED":"0",
         "BACKLINE_AI_COPY_ENABLED":"0","BACKLINE_MARKET_DISCOVERY_ENABLED":"0",
         "BACKLINE_DEMO_SEED":"1"}
    server=subprocess.Popen([sys.executable,"-m","uvicorn","src.app:app",
        "--host","127.0.0.1","--port",str(port)],env=env,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            if server.poll() is not None:raise AssertionError("Test server exited")
            try:
                with urllib.request.urlopen(url+"/api/health",timeout=1) as response:
                    if response.status==200:break
            except (OSError,TimeoutError):time.sleep(.2)
        else:raise AssertionError("Test server did not start")
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page()
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(url,wait_until="networkidle")
            assert page.locator("#app").is_visible()
            assert page.get_by_text("Dashboard",exact=True).count()>0
            assert page.locator("nav[aria-label='Primary workspaces'] > button").count()==6
            page.get_by_role("heading",name="What needs attention",exact=True).wait_for(state="visible")
            page.locator("[data-go='collaboration']").first.click()
            page.get_by_role("heading",name="Band Hub",exact=True).wait_for(state="visible")
            page.locator("[data-go='dashboard']").first.click()
            page.locator("[data-go='collaboration']").first.click()
            page.get_by_role("heading",name="Band Hub",exact=True).wait_for(state="visible")
            page.get_by_role("heading",name="Conversations",exact=True).wait_for(state="visible")
            page.get_by_text("Conversations stay private",exact=True).wait_for(state="visible")
            page.locator("[data-go='songs']").first.click()
            page.locator("[data-go='studio']").first.click()
            assert page.get_by_text("AI Gig Studio").count()>0
            page.locator("[data-go='schedule']").first.click()
            page.get_by_role("heading",name="Schedule",exact=True).wait_for(state="visible",timeout=15000)
            assert page.get_by_role("tablist",name="Schedule views").count()==0
            assert page.locator("[data-calendar-day]").count()>=28
            assert page.locator("[data-action='event']").count()>=1
            # Calendar day creation mirrors desktop calendar double-click.
            day=page.locator("[data-calendar-day]").first
            selected_date=day.get_attribute("data-calendar-day")
            day.dblclick(position={"x":18,"y":18})
            page.locator("#entryForm input[name='date']").wait_for(state="visible")
            assert page.locator("#entryForm input[name='date']").input_value()==selected_date
            assert page.get_by_label("Event type").locator("option",has_text="Meeting").count()==1
            page.locator("#entryForm select[name='kind']").select_option("Meeting")
            assert page.locator("#entryForm select[name='kind']").input_value()=="Meeting"

            # Create an event on the visible month so the test is independent of
            # whether seeded gigs happen to fall in the current month.
            page.locator("#entryForm input[name='title']").fill("Synthetic calendar move test")
            page.locator("#entryForm button[type='submit']").click()
            page.get_by_text("Synthetic calendar move test",exact=True).first.wait_for(state="visible",timeout=15000)
            # Moving a real saved entry must repaint both cells without reload.
            calendar_entry=page.locator("[data-calendar-event]").filter(has_text="Synthetic calendar move test").first
            moved_id=calendar_entry.get_attribute("data-calendar-event")
            # The unified calendar opens a native details dialog, supports Escape,
            # and returns keyboard focus to the selected event after dismissal.
            calendar_entry.click()
            details=page.locator("#calendarEventDialog")
            details.wait_for(state="visible")
            assert details.get_attribute("aria-label")=="Event details: Synthetic calendar move test"
            details.get_by_role("button",name="Change date").wait_for(state="visible")
            page.keyboard.press("Escape")
            details.wait_for(state="detached")
            assert page.evaluate("document.activeElement?.getAttribute('data-calendar-event')")==moved_id
            source=calendar_entry.locator("xpath=ancestor::*[@data-calendar-day]").first
            old_date=source.get_attribute("data-calendar-day")
            destination=page.locator("[data-calendar-day]").last
            new_date=destination.get_attribute("data-calendar-day")
            if new_date==old_date:destination=page.locator("[data-calendar-day]").first
            new_date=destination.get_attribute("data-calendar-day")
            page.once("dialog",lambda dialog:dialog.accept())
            # Dispatch a complete native HTML5 drag sequence with a shared
            # DataTransfer, avoiding headless Chromium's flaky pointer drags.
            page.evaluate("""({eventId, targetDate}) => {
                const source=document.querySelector('[data-calendar-event="'+eventId+'"]');
                const target=document.querySelector('[data-calendar-day="'+targetDate+'"]');
                const transfer=new DataTransfer();
                source.dispatchEvent(new DragEvent('dragstart',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                target.dispatchEvent(new DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                target.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                source.dispatchEvent(new DragEvent('dragend',{bubbles:true,dataTransfer:transfer}));
            }""",{"eventId":moved_id,"targetDate":new_date})
            try:
                page.locator('[data-calendar-day="'+new_date+'"] [data-calendar-event="'+moved_id+'"]').wait_for(state="visible",timeout=15000)
            except Exception:
                print("Calendar drag diagnostic",page.locator("[data-calendar-day]").evaluate_all("(els) => els.filter(x => x.querySelector('[data-calendar-event]')).map(x => ({day:x.dataset.calendarDay,ids:[...x.querySelectorAll('[data-calendar-event]')].map(y=>y.dataset.calendarEvent)}))"))
                print("Calendar page messages",page.locator(".toast,[role='alert']").all_text_contents())
                raise
            assert page.locator('[data-calendar-day="'+old_date+'"] [data-calendar-event="'+moved_id+'"]').count()==0
            # Navigating the month must not require a browser reload.
            month_before=page.locator("#calendarMonth").input_value()
            page.get_by_role("button",name="Next month").click()
            assert page.locator("#calendarMonth").input_value()!=month_before
            page.get_by_role("button",name="Previous month").click()
            assert page.locator("#calendarMonth").input_value()==month_before
            page.reload(wait_until="networkidle")
            page.locator("[data-go='schedule']").first.click()
            page.locator('[data-calendar-day="'+new_date+'"] [data-calendar-event="'+moved_id+'"]').wait_for(state="visible",timeout=15000)
            # Rejecting a second proposed move must leave the saved date unchanged.
            page.once("dialog",lambda dialog:dialog.dismiss())
            page.evaluate("""({eventId, targetDate}) => {
                const source=document.querySelector('[data-calendar-event="'+eventId+'"]');
                const target=document.querySelector('[data-calendar-day="'+targetDate+'"]');
                const transfer=new DataTransfer();
                source.dispatchEvent(new DragEvent('dragstart',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                target.dispatchEvent(new DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                target.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                source.dispatchEvent(new DragEvent('dragend',{bubbles:true,dataTransfer:transfer}));
            }""",{"eventId":moved_id,"targetDate":old_date})
            assert page.locator('[data-calendar-day="'+new_date+'"] [data-calendar-event="'+moved_id+'"]').count()==1
            assert page.locator('[data-calendar-day="'+old_date+'"] [data-calendar-event="'+moved_id+'"]').count()==0



            # A selected event opens a prefilled editor and refreshes on save.
            page.locator('[data-calendar-event="'+moved_id+'"]').click()
            details=page.get_by_role("dialog",name="Event details: Synthetic calendar move test")
            details.wait_for(state="visible")
            assert details.get_by_text("Meeting",exact=True).count()>0
            assert details.get_by_role("button",name="Change date").count()==1
            assert details.get_by_role("button",name="Availability & RSVPs").count()==1
            details.get_by_role("button",name="Edit event").click()
            editor=page.locator("#entryForm")
            assert editor.locator('[name="title"]').input_value()=="Synthetic calendar move test"
            assert editor.locator('[name="date"]').input_value()==new_date
            assert editor.locator('[name="kind"]').input_value()=="Meeting"
            editor.locator('[name="title"]').fill("Edited calendar meeting")
            editor.locator('[name="notes"]').fill("Bring the updated setlist and stage notes")
            editor.locator('button[type="submit"]').click()
            page.locator('[data-calendar-event="'+moved_id+'"]').filter(has_text="Edited calendar meeting").wait_for(state="visible",timeout=15000)
            page.locator('[data-calendar-event="'+moved_id+'"]').click()
            page.get_by_role("dialog",name="Event details: Edited calendar meeting").get_by_text("Bring the updated setlist and stage notes").wait_for(state="visible",timeout=15000)
            refreshed=page.get_by_role("dialog",name="Event details: Edited calendar meeting")
            refreshed.wait_for(state="visible",timeout=15000)
            assert refreshed.get_by_text("Edited calendar meeting").count()>0
            refreshed.get_by_role("button",name="Close event details").click()
            assert page.get_by_role("dialog",name="Event details: Edited calendar meeting").count()==0
            expect(page.locator('[data-calendar-event="'+moved_id+'"]')).to_be_focused()


            page.locator("[data-go='touring']").first.click()
            page.locator("[data-go='showops']").first.click()
            assert page.get_by_text("Show Packets").count()>0
            page.get_by_role('tab',name='Stage & inputs').wait_for(state='visible',timeout=10000)
            page.get_by_role('tab',name='Advances & riders').click()
            assert page.get_by_text('Show documents').count()>0
            page.locator('[data-edit-packet]').first.click()
            page.locator('#packetTitle').wait_for(state='visible')
            page.locator('#packetTitle').fill('Revised production rider')
            page.locator('#packetSave').click()
            page.locator('#packetEditor').wait_for(state='detached')
            expect(page.get_by_text('Revised production rider',exact=True)).to_be_visible()
            with page.expect_popup() as printed:
                page.locator('[data-print-packet]').click()
            packet_window=printed.value
            packet_window.wait_for_load_state('domcontentloaded')
            assert 'Revised production rider' in packet_window.locator('body').inner_text()
            packet_window.close()
            page.get_by_role('tab',name='Contracts & files').click()
            assert page.get_by_text('Contracts and show files').count()>0
            page.locator("[data-go='touring']").first.click()
            page.get_by_role("heading",name="Tour Routing",exact=True).wait_for(state="visible",timeout=15000)
            page.get_by_role("tab",name="Day of show").click()
            expect(page.get_by_text("Tour day sheets",exact=True)).to_be_visible()
            expect(page.get_by_text("Show days and travel stops in chronological order",exact=False)).to_be_visible()
            # The day sheet must reuse the existing itinerary editor for both show and travel stops.
            edit_buttons=page.locator("[data-edit-stop]")
            if edit_buttons.count():
                edit_buttons.first.click()
                expect(page.get_by_role("dialog")).to_be_visible()
                expect(page.get_by_role("dialog").get_by_text("Edit tour stop")).to_be_visible()
                page.get_by_role("dialog").press("Escape")
            page.get_by_role("tab",name="Itinerary",exact=True).click()
            assert not errors,errors
            mobile=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
            mobile_errors=[]
            mobile.on("pageerror",lambda error:mobile_errors.append(str(error)))
            mobile.goto(url,wait_until="networkidle")
            mobile.locator(".mobileNav").wait_for(state="visible")
            assert mobile.locator(".mobileNav > button").count()==6
            mobile.locator(".mobileNav [data-go='songs']").click()
            mobile.get_by_role("heading",name="Song Library",exact=True).wait_for(state="visible",timeout=15000)
            mobile.locator(".mobileNav [data-go='touring']").click()
            mobile.get_by_role("heading",name="Tour Routing",exact=True).wait_for(state="visible",timeout=15000)
            assert not mobile_errors,mobile_errors
            mobile.close()
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()
