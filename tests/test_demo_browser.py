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
            page.evaluate("() => openShowPacketGig(Number(get('events').find(e => e.kind === 'Gig').id))")
            page.get_by_role("heading",name="Show workflow",exact=True).wait_for(state="visible",timeout=15000)
            assert page.locator(".showJourneySteps button").count()==5
            page.locator('[data-show-context="tasks"]').click()
            page.get_by_role("heading",name="Tasks",exact=True).wait_for(state="visible",timeout=15000)
            assert page.locator(".workspaceContext").is_visible()
            page.locator("[data-new-task]").click()
            assert page.get_by_role("dialog",name="Add task").locator("select[name='event_id']").input_value() == str(page.evaluate("state.showGig"))
            page.get_by_role("dialog",name="Add task").get_by_role("button",name="Cancel").click()
            page.locator("[data-return-show]").click()
            page.get_by_role("heading",name="Show workflow",exact=True).wait_for(state="visible",timeout=15000)
            page.locator('[data-show-context="setlists"]').click()
            assert page.locator(".workspaceContext").is_visible()
            page.locator("[data-return-show]").click()
            page.get_by_role("heading",name="Show workflow",exact=True).wait_for(state="visible",timeout=15000)
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
