"""Chromium smoke coverage for the strictly isolated authenticated demo account."""
import os, socket, subprocess, sys, time, urllib.request

def test_demo_account_browser_login_and_hub(tmp_path):
    from playwright.sync_api import sync_playwright
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    env={**os.environ,
         "BACKLINE_DB":str(tmp_path/"authenticated-demo.sqlite"),
         "BACKLINE_ACCOUNTS_ENABLED":"1",
         "BACKLINE_DEMO_SEED":"1",
         "BACKLINE_DEMO_ACCOUNTS":"1",
         "BACKLINE_DEMO_PASSWORD":"synthetic-browser-demo-password-123",
         "BACKLINE_LOCAL_DEV":"1"}
    server=subprocess.Popen([sys.executable,"-m","uvicorn","src.app:app",
        "--host","127.0.0.1","--port",str(port)],env=env,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            if server.poll() is not None:raise AssertionError("Synthetic demo server exited")
            try:
                with urllib.request.urlopen(url+"/api/health",timeout=1) as response:
                    if response.status==200:break
            except (OSError,TimeoutError):time.sleep(.2)
        else:raise AssertionError("Synthetic demo server did not become healthy")
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page()
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(url,wait_until="networkidle")
            page.locator("#loginForm").wait_for(state="visible",timeout=15000)
            page.locator("#loginEmail").fill("demo-owner@example.test")
            page.locator("#loginPassword").fill("synthetic-browser-demo-password-123")
            page.locator("#loginForm button[type='submit']").click()
            page.locator("nav[aria-label='Primary workspaces']").wait_for(state="visible",timeout=15000)
            page.get_by_text("Confirm showcase stage plot (demo)").first.wait_for(state="visible",timeout=15000)
            page.get_by_text("Finalize rehearsal set transitions (demo)").first.wait_for(state="visible",timeout=15000)
            assert page.locator("[data-show-gig]").count() >= 1
            # Home first presents the next gig's actionable context, not just metrics.
            spotlight=page.locator(".homeGigSpotlight")
            assert spotlight.count()==1
            assert spotlight.get_by_text("Regional showcase (demo)").is_visible()
            assert spotlight.get_by_role("button",name="My Gig Day").is_visible()
            assert spotlight.get_by_role("button",name="Details & RSVP").is_visible()
            assert page.locator(".bandHomeStat").count()==5
            readiness=page.locator(".homeReadinessDisclosure")
            assert readiness.count()==1
            assert readiness.get_attribute("open") is None
            assert page.get_by_text("Outstanding show tasks",exact=True).is_visible()
            readiness.locator("summary").click()
            assert readiness.get_attribute("open") is not None
            assert readiness.get_by_text("Venue advance",exact=True).is_visible()
            readiness.locator("summary").click()
            assert readiness.get_attribute("open") is None
            assert page.evaluate("""() => {
                const spot=document.querySelector('.homeGigSpotlight');
                const stat=document.querySelector('.bandHomeStats');
                const card=document.querySelector('.bandHomeGrid');
                return spot.compareDocumentPosition(stat)&Node.DOCUMENT_POSITION_FOLLOWING
                    && stat.compareDocumentPosition(card)&Node.DOCUMENT_POSITION_FOLLOWING;
            }""")
            for width in (320,390,768,1280):
                page.set_viewport_size({"width":width,"height":850})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"),f"Home overflow at {width}px"
                assert spotlight.get_by_role("button",name="My Gig Day").is_visible()
                assert page.locator(".bandHomeStat").count()==5
                if width==768:
                    # Tablet rail hides visible labels; explicit accessible names remain.
                    assert page.get_by_role("navigation",name="Primary workspaces").get_by_role("button",name="Shows & Tours").count()==1
                if width==320:
                    assert page.locator(".mobileNav [data-go='dashboard']").count()==1
            page.set_viewport_size({"width":1280,"height":850})
            page.locator("[data-go='collaboration']").first.click()
            page.get_by_text("Weekend show preparation (demo)").first.wait_for(state="visible",timeout=15000)
            page.get_by_role("heading",name="Conversations",exact=True).wait_for(state="visible",timeout=15000)
            assert page.locator(".hubChatWorkspace .threadChoice").count()==1
            assert page.get_by_role("navigation",name="Global tools").is_visible()
            assert page.get_by_role("button",name="Notifications").is_visible()
            assert page.get_by_role("button",name="My Tasks").is_visible()
            assert page.get_by_role("button",name="Band Settings").is_visible()
            assert page.locator(".hubQuickLinks, .hubSecondary").count()==0
            assert page.get_by_text("Demo: confirm stage plot and arrival time",exact=False).count()>0
            assert page.locator(".hubDisclosure[open]").count()==0
            page.evaluate("() => openCalendarEventDialog(Number(get('events')[0].id))")
            page.get_by_role("button",name="Availability & RSVPs").click()
            page.locator(".attendanceRoster .attendancePerson").first.wait_for(state="visible",timeout=15000)
            assert page.locator(".attendanceRoster .attendancePerson").count()==1
            page.get_by_role("button",name="Close event details").click()
            page.get_by_role("button",name="Close event details").count()
            page.get_by_role("button",name="Band Settings").click()
            page.locator(".hubDisclosure summary").filter(has_text="Band administration").click()
            assert page.locator("[data-link-roster]").count()==4
            page.locator("[data-go='schedule']").first.click()
            assert page.get_by_role("tablist",name="Schedule views").count()==0
            # Synthetic rehearsal is dated 22 days ahead; display its month directly.
            import datetime
            rehearsal_month=(datetime.date.today()+datetime.timedelta(days=22)).strftime("%Y-%m")
            page.locator("#calendarMonth").fill(rehearsal_month)
            page.locator("#calendarMonth").dispatch_event("change")
            page.locator("[data-calendar-event]").filter(has_text="Full-band rehearsal (demo)").wait_for(state="visible",timeout=15000)
            page.locator("[data-go='songs']").first.click()
            page.get_by_text("Example Opener").first.wait_for(state="visible",timeout=15000)
            page.locator("[data-go='schedule']").first.click()
            page.evaluate("() => openCalendarEventDialog(Number(get('events').find(e => e.kind === 'Gig').id))")
            event_dialog=page.get_by_role("dialog",name="Event details:",exact=False)
            assert event_dialog.get_by_role("button",name="My gig day").is_visible()
            event_dialog.get_by_role("button",name="My gig day").click()
            focused=page.get_by_role("region",name="Musician gig-day workspace")
            focused.wait_for(state="visible",timeout=15000)
            assert page.get_by_role("heading",name="My Gig Day",exact=True).is_visible()
            focused.get_by_role("region",name="Show-day call times").wait_for(state="visible",timeout=15000)
            assert focused.get_by_text("Load-in",exact=True).is_visible()
            assert focused.get_by_text("Soundcheck",exact=True).is_visible()
            assert focused.get_by_text("Showtime",exact=True).is_visible()
            assert focused.get_by_text("My assignments",exact=True).is_visible()
            assert focused.get_by_text("Confirm showcase stage plot (demo)").is_visible()
            assert focused.get_by_text("My lodging",exact=True).is_visible()
            directions=focused.get_by_role("link",name="Venue directions")
            assert directions.is_visible()
            assert directions.get_attribute("href").startswith("https://www.google.com/maps/search/?api=1&query=")
            assert directions.get_attribute("rel")=="noopener noreferrer"
            assert focused.get_by_role("region",name="Urgent show changes").is_visible()
            timeline=focused.get_by_role("region",name="Day-of-show timeline")
            assert timeline.is_visible()
            assert timeline.get_by_role("button",name="Open full call sheet").is_visible()
            stage=focused.get_by_role("region",name="Stage and audio setup")
            assert stage.is_visible()
            stage.get_by_text("View stage plot and numbered inputs").click()
            assert stage.locator("details").get_attribute("open") is not None
            assert stage.get_by_text("No audio input list recorded.").count() <= 1
            assert focused.get_by_role("region",name="Show music").get_by_text("Example Opener").is_visible()
            assert focused.get_by_role("region",name="Show music").get_by_text("Example Closer").is_visible()
            assert focused.get_by_role("button",name="My RSVP",exact=True).is_visible()
            own_rsvp=focused.get_by_role("region",name="My show availability")
            assert own_rsvp.is_visible()
            own_rsvp.get_by_label("Response").select_option("maybe")
            own_rsvp.get_by_label("Note to bandmates").fill("Synthetic demo arrival check")
            own_rsvp.get_by_role("button",name="Save my RSVP").click()
            own_rsvp.locator(".tag").get_by_text("Maybe",exact=True).wait_for(state="visible",timeout=15000)
            assert own_rsvp.get_by_label("Response").input_value()=="maybe"
            assert own_rsvp.get_by_label("Note to bandmates").input_value()=="Synthetic demo arrival check"
            focused.get_by_role("button",name="My RSVP",exact=True).click()
            assert own_rsvp.get_by_label("Response").evaluate("(node)=>document.activeElement===node")
            focused.get_by_role("button",name="Refresh").click()
            own_rsvp.locator(".tag").get_by_text("Maybe",exact=True).wait_for(state="visible",timeout=15000)
            assert focused.get_by_role("button",name="Urgent changes",exact=True).is_visible()
            assert focused.get_by_role("button",name="Setlist",exact=True).is_visible()
            focused.get_by_role("button",name="Detailed production").click()
            page.get_by_role("heading",name="Show workflow",exact=True).wait_for(state="visible",timeout=15000)
            assert page.locator(".showJourneySteps button").count()==5
            essentials = page.get_by_role("region",name="Gig essentials")
            assert essentials.is_visible()
            assert essentials.get_by_text("When & where").is_visible()
            assert essentials.get_by_text("Show calls").is_visible()
            assert essentials.get_by_text("Contact",exact=True).is_visible()
            assert essentials.get_by_role("button",name="My RSVP").is_visible()
            gig_day=page.get_by_role("region",name="My gig day")
            assert gig_day.is_visible()
            assert gig_day.get_by_text("Load-in",exact=True).is_visible()
            assert gig_day.get_by_text("Soundcheck",exact=True).is_visible()
            assert gig_day.get_by_text("Doors",exact=True).is_visible()
            assert gig_day.get_by_text("Showtime",exact=True).is_visible()
            assert gig_day.get_by_text("My lodging",exact=True).is_visible()
            assert gig_day.get_by_text("Details subject to confirmation",exact=True).count() <= 1
            assert gig_day.get_by_text("1 assigned open task",exact=False).is_visible()
            assert gig_day.get_by_text("Confirm showcase stage plot (demo)").is_visible()
            assert gig_day.get_by_role("button",name="Show tasks").is_visible()
            assert gig_day.get_by_role("button",name="Show setlists").is_visible()
            assert page.get_by_role("region",name="Show setlists").is_visible()
            assert page.locator(".showMusicSummary [data-show-context='setlists']").is_visible()
            page.locator('.showJourneySteps [data-show-context="tasks"]').click()
            page.get_by_role("heading",name="Tasks",exact=True).wait_for(state="visible",timeout=15000)
            assert page.locator(".workspaceContext").is_visible()
            page.locator("[data-new-task]").click()
            assert page.get_by_role("dialog",name="Add task").locator("select[name='event_id']").input_value() == str(page.evaluate("state.showGig"))
            page.get_by_role("dialog",name="Add task").get_by_role("button",name="Cancel").click()
            page.locator("[data-return-show]").click()
            page.get_by_role("heading",name="Show workflow",exact=True).wait_for(state="visible",timeout=15000)
            page.locator('.showJourneySteps [data-show-context="setlists"]').click()
            assert page.locator(".workspaceContext").is_visible()
            page.locator("[data-return-show]").click()
            page.get_by_role("heading",name="Show workflow",exact=True).wait_for(state="visible",timeout=15000)
            page.locator('.showJourneySteps [data-show-context="tasks"]').click()
            assert page.locator(".workspaceContext").is_visible()
            page.get_by_role("button",name="My Tasks").click()
            assert page.locator(".workspaceContext").count()==0
            page.evaluate("""() => {
              state.musicGig = null;
              state.section = 'setlists';
              state.data.setlists = [{
                id: 99999, title: 'Browser performance check',
                event_id: null,
                songs: [
                  {id: 10001, title: 'Opening number', song_key: 'G', bpm: 110, duration_seconds: 180},
                  {id: 10002, title: 'Second number', song_key: 'D', bpm: 120, duration_seconds: 200}
                ]
              }];
              render();
            }""")
            page.locator('[data-perform-setlist="99999"]').click()
            performance = page.get_by_role("dialog",name="Performance view: Browser performance check")
            performance.get_by_role("heading",name="Opening number").wait_for(state="visible")
            assert performance.get_by_text("Second number",exact=True).is_visible()  # Up next
            performance.get_by_role("button",name="Increase stage font size").click()
            assert performance.evaluate("(el)=>Number(el.style.getPropertyValue('--stage-font-scale'))") > 1
            performance.get_by_role("button",name="Show running order").click()
            order=performance.get_by_role("navigation",name="Setlist running order")
            assert order.get_by_role("button",name="1. Opening number").is_visible()
            order.get_by_role("button",name="2. Second number").click()
            performance.get_by_role("heading",name="Second number").wait_for(state="visible")
            assert performance.get_by_text("End of set").is_visible()
            performance.get_by_role("button",name="Previous").click()
            performance.get_by_role("heading",name="Opening number").wait_for(state="visible")
            performance.get_by_role("button",name="Next").click()
            performance.get_by_role("heading",name="Second number").wait_for(state="visible")
            performance.get_by_role("button",name="Close performance view").click()
            assert not errors,errors
            page.locator("#logoutButton").click()
            page.locator("#loginForm").wait_for(state="visible",timeout=15000)
            page.reload(wait_until="networkidle")
            page.locator("#loginForm").wait_for(state="visible",timeout=15000)
            mobile=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
            mobile_errors=[]
            mobile.on("pageerror",lambda error:mobile_errors.append(str(error)))
            mobile.goto(url,wait_until="networkidle")
            mobile.locator("#loginEmail").fill("demo-owner@example.test")
            mobile.locator("#loginPassword").fill("synthetic-browser-demo-password-123")
            mobile.locator("#loginForm button[type='submit']").click()
            mobile.locator(".mobileNav [data-go='collaboration']").wait_for(state="visible",timeout=15000)
            mobile.locator(".mobileNav [data-go='collaboration']").click()
            mobile.get_by_text("Weekend show preparation (demo)").first.wait_for(state="visible",timeout=15000)
            assert not mobile_errors,mobile_errors
            mobile.close()
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()
