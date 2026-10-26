"""Desktop and mobile regression of production workflows using disposable seed data."""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import pytest
from playwright.sync_api import sync_playwright, expect

@pytest.fixture
def preview_url(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    env={**os.environ,'BACKLINE_DB':str(tmp_path/'preview.sqlite'),'BACKLINE_LOCAL_DEV':'1',
         'BACKLINE_ACCOUNTS_ENABLED':'0','BACKLINE_DEMO_SEED':'1',
         'BACKLINE_AI_COPY_ENABLED':'0','BACKLINE_MARKET_DISCOVERY_ENABLED':'0'}
    server=subprocess.Popen([sys.executable,'-m','uvicorn','src.app:app','--host','127.0.0.1','--port',str(port)],
                            env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if server.poll() is not None:raise AssertionError('Synthetic preview exited')
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1):break
            except OSError:time.sleep(.1)
        else:raise AssertionError('Preview did not start')
        yield url
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)

@pytest.mark.parametrize('width',[1280,390])
def test_stage_advancement_and_overnight_calls(preview_url,width):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':width,'height':900})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(preview_url,wait_until='networkidle')
        page.locator('[data-go="showops"]:visible').first.click()
        page.get_by_role('tab',name='Stage & inputs').wait_for()
        page.get_by_role('button',name='Edit stage setup').click()
        expect(page.get_by_role('dialog',name='Stage Designer')).to_be_visible()
        page.get_by_role('button',name='+ Equipment',exact=True).click()
        page.get_by_label('Equipment label',exact=True).fill('Keyboard guitar')
        page.get_by_label('Equipment label',exact=True).press('Tab')
        equipment=page.get_by_role('button',name='Keyboard guitar, x 50, y 50',exact=True)
        equipment.focus();equipment.press('ArrowRight')
        expect(page.get_by_role('button',name='Keyboard guitar, x 51, y 50',exact=True)).to_be_focused()
        page.get_by_label('Audio source 1',exact=True).fill('Synthetic vocal')
        page.get_by_label('Stand 1',exact=True).fill('Tall boom')
        page.get_by_label('Channel notes 1',exact=True).fill('Needs phantom power')
        page.get_by_role('button',name='Save stage setup',exact=True).click()
        expect(page.get_by_role('dialog',name='Stage Designer')).to_have_count(0)
        page.get_by_role('button',name='Edit stage setup').click()
        expect(page.get_by_label('Stand 1',exact=True)).to_have_value('Tall boom')
        expect(page.get_by_label('Channel notes 1',exact=True)).to_have_value('Needs phantom power')
        page.get_by_role('button',name='✕ Close',exact=True).click()
        page.get_by_role('tab',name='Advances & riders').click()
        page.locator('[data-advance-field="timezone"]').fill('America/Chicago')
        page.locator('[data-advance-field="venue_contact"]').fill('Synthetic venue manager')
        for field,value in {'load_in':'17:00','soundcheck':'18:00','doors':'19:00','show_time':'23:00','curfew':'01:00'}.items():
            page.locator(f'[data-advance-field="{field}"]').fill(value)
        page.locator('[data-advance-day="curfew"]').select_option('1')
        page.locator('[data-advance-field="open_questions"]').fill('')
        page.get_by_label('Advancement status',exact=True).select_option('confirmed')
        page.get_by_role('button',name='Save advancement',exact=True).click()
        expect(page.get_by_text('Venue advancement saved',exact=True)).to_be_visible()
        page.get_by_role('tab',name='Day of show',exact=True).click()
        expect(page.locator('.callTime').last).to_contain_text('Day +1')
        expect(page.locator('.callContacts')).to_contain_text('Synthetic venue manager')
        page.get_by_role('button',name='Edit crew calls').click()
        page.get_by_role('button',name='+ Crew call',exact=True).click()
        page.get_by_label('Activity 1',exact=True).fill('Merch count')
        page.get_by_label('Local time 1',exact=True).fill('00:30')
        page.get_by_label('Day offset 1',exact=True).fill('1')
        page.get_by_label('Owner 1',exact=True).fill('Synthetic crew')
        page.get_by_label('Location 1',exact=True).fill('Lobby')
        page.get_by_role('button',name='Save crew calls',exact=True).click()
        expect(page.get_by_role('dialog',name='Edit crew calls')).to_have_count(0)
        expect(page.locator('.showTimeline')).to_contain_text('Merch count')
        expect(page.locator('.scheduleWarning')).to_contain_text('provisional')
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows horizontally'
        # Tab navigation must work without pointing input.
        page.get_by_role('tab',name='Day of show',exact=True).focus()
        page.keyboard.press('ArrowLeft')
        expect(page.get_by_role('tab',name='Advances & riders')).to_be_focused()
        expect(page.get_by_label('Advancement status',exact=True)).to_have_value('draft')
        assert not errors,errors
        browser.close()


def test_tour_stop_editor_round_trip(preview_url):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':390,'height':844})
        page.goto(preview_url,wait_until='networkidle')
        page.locator('[data-go="touring"]:visible').first.click()
        page.get_by_role('button',name='Edit stop',exact=True).first.click()
        dialog=page.get_by_role('dialog',name='Edit tour stop')
        dialog.get_by_label('Lodging',exact=True).fill('Fictional Touring Hotel')
        dialog.get_by_label('Arrival time',exact=True).fill('16:30')
        dialog.get_by_role('button',name='Save stop',exact=True).click()
        expect(dialog).to_have_count(0)
        expect(page.get_by_text('Fictional Touring Hotel',exact=True)).to_be_visible()
        expect(page.get_by_text('Arrive 16:30',exact=False)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        browser.close()
