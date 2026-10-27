"""Desktop and mobile regression of production workflows using disposable seed data."""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import pytest
from playwright.sync_api import sync_playwright, expect

def navigate(page,key):
    groups={'showops':'touring','venues':'touring','tasks':'collaboration',
            'setlists':'songs'}
    target=page.locator('[data-go="'+key+'"]:visible')
    if target.count()==0 and key in groups:
        page.locator('[data-go="'+groups[key]+'"]:visible').first.click()
    page.locator('[data-go="'+key+'"]:visible').first.click()

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
        navigate(page,'showops')
        page.get_by_role('tab',name='Stage & inputs').wait_for()
        page.get_by_role('button',name='Edit stage setup').click()
        expect(page.get_by_role('dialog',name='Stage Designer')).to_be_visible()
        assert page.locator('.stageDesigner').evaluate('(n)=>n.scrollWidth <= n.clientWidth'), 'Stage editor overflows horizontally'
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
        navigate(page,'touring')
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

@pytest.mark.parametrize('width',[1280,390])
def test_venue_tasks_and_setlist_builder(preview_url,width,tmp_path):
    import datetime
    from pypdf import PdfReader
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':width,'height':900})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(preview_url,wait_until='networkidle')
        navigate(page,'venues')
        page.get_by_role('button',name='+ Add venue',exact=True).click()
        dialog=page.get_by_role('dialog',name='Add venue')
        dialog.get_by_label('Venue name',exact=True).fill('Synthetic Venue Book Hall')
        dialog.get_by_label('Tags (comma separated)',exact=True).fill('club, midwest')
        dialog.get_by_role('button',name='+ Contact',exact=True).click()
        dialog.get_by_label('Contact name 1',exact=True).fill('Synthetic Engineer')
        dialog.get_by_label('Contact role 1',exact=True).fill('Sound engineer')
        dialog.get_by_label('Contact phone 1',exact=True).fill('555-0110')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(page.get_by_text('Synthetic Venue Book Hall',exact=True)).to_be_visible()
        navigate(page,'showops')
        page.get_by_role('tab',name='Advances & riders',exact=True).click()
        page.locator('#showVenueLink').select_option(label='Synthetic Venue Book Hall')
        page.get_by_role('button',name='Link venue to show',exact=True).click()
        expect(page.get_by_text('Venue linked to show',exact=True)).to_be_visible()
        expect(page.get_by_text('Synthetic Engineer · Sound engineer · 555-0110',exact=True)).to_be_visible()
        navigate(page,'tasks')
        page.get_by_role('button',name='+ Add task',exact=True).click()
        dialog=page.get_by_role('dialog',name='Add task')
        dialog.get_by_label('Task title',exact=True).fill('Print synthetic setlists')
        dialog.get_by_label('Due date',exact=True).fill(str(datetime.date.today()+datetime.timedelta(days=1)))
        dialog.get_by_label('Assignee',exact=True).select_option(index=1)
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(page.get_by_text('Print synthetic setlists',exact=True)).to_be_visible()
        expect(page.get_by_text('due tomorrow',exact=True)).to_be_visible()
        task_row=page.locator('.entry').filter(has_text='Print synthetic setlists')
        task_row.get_by_role('button',name='Complete',exact=True).click()
        expect(task_row.get_by_role('button',name='Reopen',exact=True)).to_be_visible()
        navigate(page,'songs')
        page.get_by_role('button',name='Edit song',exact=True).first.click()
        song_dialog=page.get_by_role('dialog',name='Edit song')
        song_dialog.get_by_label('Song tags (comma separated)',exact=True).fill('cover, acoustic')
        song_dialog.get_by_label('Reference recording HTTPS URL',exact=True).fill('https://example.test/arrangement.mp3')
        song_dialog.get_by_role('button',name='Save',exact=True).click()
        expect(page.get_by_role('link',name='Reference recording',exact=True)).to_be_visible()
        expect(page.get_by_text('cover · acoustic',exact=True)).to_be_visible()
        navigate(page,'setlists')
        page.get_by_role('button',name='+ Create setlist',exact=True).click()
        dialog=page.get_by_role('dialog',name='Create setlist')
        dialog.get_by_label('Setlist title',exact=True).fill('Synthetic running order')
        dialog.get_by_role('button',name='+ Add song',exact=True).click()
        dialog.get_by_label('Song to add',exact=True).select_option(index=1)
        dialog.get_by_role('button',name='+ Add song',exact=True).click()
        before=dialog.locator('.setlistOrderRow span').all_text_contents()
        dialog.locator('.setlistOrderRow').nth(1).drag_to(dialog.locator('.setlistOrderRow').nth(0))
        assert dialog.locator('.setlistOrderRow span').all_text_contents()==list(reversed(before))
        dialog.get_by_role('button',name='Move song up 2',exact=True).click()
        assert dialog.locator('.setlistOrderRow span').all_text_contents()==before
        expect(dialog.locator('#setlistRuntime')).to_contain_text('2 songs')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(page.get_by_text('Synthetic running order',exact=True)).to_be_visible()
        card=page.locator('.panel').filter(has=page.get_by_role('heading',name='Synthetic running order',exact=True)).last
        with page.expect_download() as exported:
            card.get_by_role('button',name='Download setlist PDF',exact=True).click()
        path=tmp_path/'setlist.pdf';exported.value.save_as(path)
        assert 'Synthetic running order' in PdfReader(path).pages[0].extract_text()
        navigate(page,'schedule')
        page.get_by_role('button',name='+ Calendar',exact=True).click()
        dialog=page.get_by_role('dialog',name='Create calendar')
        dialog.get_by_label('Calendar name',exact=True).fill('Synthetic tour dates')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(dialog).to_have_count(0)
        demo=next(b for b in page.request.get(preview_url+'/api/bands').json() if b['name']=='The Drunk Uncles (Demo)')
        month=page.request.get(preview_url+'/api/bands/'+str(demo['id'])+'/events').json()[0]['date'][:7]
        page.locator('#calendarMonth').fill(month)
        page.locator('#calendarMonth').dispatch_event('change')
        page.locator('[data-calendar-event]').first.click()
        page.get_by_role('button',name='Choose calendar',exact=True).first.click()
        dialog=page.get_by_role('dialog',name='Choose event calendar')
        dialog.get_by_label('Calendar',exact=True).select_option(label='Synthetic tour dates')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(dialog).to_have_count(0)
        expect(page.locator('.calendarEvent').filter(has_text='Synthetic tour dates')).to_have_count(1)
        with page.expect_download() as downloaded:
            page.get_by_role('button',name='Download iCal',exact=True).click()
        path=tmp_path/'calendar.ics';downloaded.value.save_as(path)
        assert 'BEGIN:VCALENDAR' in path.read_text()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not errors,errors
        browser.close()
