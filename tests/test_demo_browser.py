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
            page.locator("[data-go='collaboration']").first.click()
            page.get_by_text("Weekend show preparation (demo)").first.wait_for(state="visible",timeout=15000)
            assert page.get_by_text("Demo: confirm stage plot and arrival time",exact=False).count()>0
            assert not errors,errors
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()
