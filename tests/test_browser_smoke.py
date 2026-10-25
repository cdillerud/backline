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
    from playwright.sync_api import sync_playwright
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    env={**os.environ,"BACKLINE_DB":str(tmp_path/"browser.sqlite"),
         "BACKLINE_LOCAL_DEV":"1","BACKLINE_ACCOUNTS_ENABLED":"0",
         "BACKLINE_AI_COPY_ENABLED":"0","BACKLINE_MARKET_DISCOVERY_ENABLED":"0"}
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
            page.locator("[data-go='studio']").first.click()
            assert page.get_by_text("AI Gig Studio").count()>0
            page.locator("[data-go='events']").first.click()
            assert page.get_by_text("Shows & Rehearsals").count()>0
            page.locator("[data-go='showops']").first.click()
            assert page.get_by_text("Show Packets").count()>0
            page.locator("[data-go='touring']").first.click()
            assert page.get_by_text("Tour Routing").count()>0
            assert not errors,errors
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()
