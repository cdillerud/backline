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
            page.locator("[data-go='studio']").first.click()
            assert page.get_by_text("AI Gig Studio").count()>0
            page.locator("[data-go='schedule']").first.click()
            page.get_by_role("heading",name="Schedule",exact=True).wait_for(state="visible",timeout=15000)
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
            assert page.get_by_role("heading",name="Tours",exact=True).count()>0
            assert not errors,errors
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()
