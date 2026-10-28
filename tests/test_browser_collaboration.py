"""Synthetic signed-in browser acceptance for approved privacy workflows."""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from test_collaboration import accounts

@pytest.fixture
def account_server(accounts):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'BACKLINE_LOCAL_DEV':'1','BACKLINE_ACCOUNTS_ENABLED':'1',
         'BACKLINE_DEMO_SEED':'0','BACKLINE_PUBLIC_SHARING_ENABLED':'1'}
    server=subprocess.Popen([sys.executable,'-m','uvicorn','src.app:app','--host','127.0.0.1','--port',str(port)],
                            env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if server.poll() is not None:raise AssertionError('Synthetic account server exited')
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1):break
            except OSError:time.sleep(.1)
        else:raise AssertionError('Server did not start')
        yield url
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)

def sign_in(page,url,role):
    page.goto(url,wait_until='networkidle')
    page.get_by_label('Email',exact=True).fill(role+'@example.test')
    page.get_by_label('Password',exact=True).fill('synthetic-password-123')
    page.get_by_role('button',name='Sign in',exact=True).click()
    expect(page.get_by_role('heading',name='Overview',exact=True)).to_be_visible()

def navigate(page,key):
    target=page.locator('[data-go="'+key+'"]:visible')
    if target.count()==0:
        # v0.5 groups related tools inside their primary workspace.
        groups={
            'media':'collaboration','notifications':'collaboration',
            'tasks':'collaboration','members':'collaboration',
            'calendars':'schedule','events':'schedule',
            'venues':'touring','bookings':'touring','showops':'touring','operations':'touring',
            'setlists':'songs','studio':'songs'}
        if key in groups:
            page.locator('[data-go="'+groups[key]+'"]:visible').first.click()
    page.locator('[data-go="'+key+'"]:visible').first.click()

@pytest.mark.parametrize('width',[1280,390])
def test_member_collaboration_live_updates_and_notifications(account_server,accounts,width):
    _,client,_,_,base,users,headers,_,member,_=accounts
    with sync_playwright() as p:
        browser=p.chromium.launch()
        owner=browser.new_page(viewport={'width':width,'height':900});person=browser.new_page(viewport={'width':width,'height':900})
        errors=[];owner.on('pageerror',lambda error:errors.append(str(error)));person.on('pageerror',lambda error:errors.append(str(error)))
        sign_in(owner,account_server,'owner');navigate(owner,'collaboration')
        owner.get_by_text('Band administration',exact=True).click()
        owner.get_by_role('button',name='Link account',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Link roster account')
        dialog.get_by_label('Band account',exact=True).select_option(label='Member')
        dialog.get_by_role('button',name='Save',exact=True).click()
        owner.get_by_text('Band administration',exact=True).click()
        expect(owner.get_by_role('button',name='Change account link',exact=True)).to_be_visible()
        owner.get_by_text('Availability and RSVP',exact=True).click()
        owner.get_by_role('button',name='Request responses',exact=True).click()
        sign_in(person,account_server,'member');navigate(person,'collaboration')
        person.get_by_text('Availability and RSVP',exact=True).click()
        person.get_by_label('My RSVP',exact=True).select_option('yes')
        person.get_by_label('Availability note',exact=True).fill('Available after 5')
        person.get_by_role('button',name='Save my RSVP',exact=True).click()
        expect(person.get_by_text('Your RSVP saved',exact=True)).to_be_visible()
        assert person.get_by_role('button',name='New discussion',exact=True).count()==0
        editor=person.get_by_label('Message',exact=True)
        editor.fill('First line')
        editor.press('Shift+Enter')
        editor.type('Second line')
        assert editor.input_value()=='First line\nSecond line'
        editor.fill('Confirming the monitor plan')
        person.get_by_text('@ Mention bandmates',exact=True).click()
        person.get_by_label('@Owner',exact=True).check()
        person.get_by_role('button',name='Send message',exact=True).click()
        expect(person.locator('#threadPosts')).to_contain_text('Confirming the monitor plan')
        expect(owner.locator('#threadPosts')).to_contain_text('Confirming the monitor plan',timeout=10000)
        person.get_by_role('button',name='Edit message',exact=True).click()
        dialog=person.get_by_role('dialog',name='Edit my reply')
        dialog.get_by_label('Reply',exact=True).fill('Updated monitor plan')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(owner.locator('#threadPosts')).to_contain_text('Updated monitor plan',timeout=10000)
        navigate(owner,'notifications')
        expect(owner.get_by_text('Mention in Show planning',exact=True)).to_be_visible()
        owner.get_by_label('Task assignments',exact=True).select_option('daily')
        owner.get_by_role('button',name='Save preferences',exact=True).click()
        expect(owner.get_by_text('Preferences saved',exact=True)).to_be_visible()
        assert client.post(base+'/tasks',headers=headers['owner'],json={'title':'Pack spare cables','assignee_id':member}).status_code==201
        navigate(person,'notifications')
        expect(person.get_by_text('Task assigned: Pack spare cables',exact=True)).to_be_visible()
        person.get_by_role('button',name='Mark read',exact=True).first.click()
        expect(person.get_by_text('Read',exact=True)).to_have_count(1)
        assert person.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not errors,errors
        browser.close()

@pytest.mark.parametrize('width',[1280,390])
def test_gallery_profile_publication_and_revocation(account_server,accounts,width,tmp_path):
    _,client,_,_,base,_,headers,_,_,_=accounts
    image_path=tmp_path/'synthetic.png';Image.new('RGB',(120,80),'green').save(image_path)
    with sync_playwright() as p:
        browser=p.chromium.launch();owner=browser.new_page(viewport={'width':width,'height':900})
        errors=[];owner.on('pageerror',lambda error:errors.append(str(error)))
        sign_in(owner,account_server,'owner');navigate(owner,'media')
        owner.get_by_role('button',name='+ Album',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Create album')
        dialog.get_by_label('Album name',exact=True).fill('Synthetic show photos')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(owner.get_by_role('heading',name='Synthetic show photos',exact=True)).to_be_visible()
        owner.get_by_role('button',name='Upload photo or recording',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Upload band media')
        dialog.get_by_label('File',exact=True).set_input_files(image_path)
        dialog.get_by_label('Add photo to album',exact=True).select_option(label='Synthetic show photos')
        dialog.get_by_label('Use as roster profile photo',exact=True).select_option(label='Stage Name')
        dialog.get_by_role('button',name='Upload',exact=True).click()
        expect(owner.get_by_text('Media uploaded privately',exact=True)).to_be_visible()
        owner.get_by_role('button',name='Open photo',exact=True).click()
        viewer=owner.get_by_role('dialog',name='Photo viewer');expect(viewer.locator('img')).to_be_visible()
        viewer.get_by_role('button',name='Close',exact=True).click()
        owner.get_by_role('button',name='Photo library',exact=True).click()
        expect(owner.get_by_role('button',name='Open photo',exact=True)).to_be_visible()
        owner.locator('[data-album]:not([data-album="library"])').first.click()
        owner.get_by_role('button',name='Album privacy and name',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Edit album')
        dialog.get_by_label('Album visibility',exact=True).select_option('1')
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(dialog).to_have_count(0)
        owner.get_by_role('button',name='Build page draft',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Build public band page')
        dialog.get_by_label('Public address slug',exact=True).fill('synthetic-show-band')
        dialog.get_by_label('Public band bio',exact=True).fill('A synthetic band for acceptance testing.')
        show_date=client.get(base+'/events',headers=headers['owner']).json()[0]['date']
        dialog.get_by_label('Synthetic Show · '+show_date,exact=True).check()
        dialog.get_by_label('Synthetic show photos',exact=True).check()
        dialog.get_by_role('button',name='Save',exact=True).click()
        expect(dialog).to_have_count(0)
        owner.get_by_role('button',name='Preview public page',exact=True).click()
        preview=owner.get_by_role('dialog',name='Public page preview')
        expect(preview.get_by_text('A synthetic band for acceptance testing.',exact=True)).to_be_visible()
        preview.get_by_role('button',name='Close',exact=True).click()
        owner.once('dialog',lambda d:d.accept())
        owner.get_by_role('button',name='Publish selected content',exact=True).click()
        expect(owner.get_by_text('Status: Published',exact=False)).to_be_visible()
        anonymous=browser.new_page();anonymous.goto(account_server+'/public/bands/synthetic-show-band')
        expect(anonymous.get_by_role('heading',name='Synthetic Collaboration',exact=True)).to_be_visible()
        expect(anonymous.get_by_text('Synthetic Show',exact=True)).to_be_visible()
        assert anonymous.locator('img').count()==1
        owner.get_by_role('button',name='Revoke public page',exact=True).click()
        expect(owner.get_by_text('Public page revoked',exact=True)).to_be_visible()
        assert anonymous.request.get(account_server+'/public/bands/synthetic-show-band').status==404
        # The PWA has a network-only worker and stores no private data in Cache Storage.
        assert owner.evaluate("async()=>{await navigator.serviceWorker.ready;return (await caches.keys()).length}")==0
        assert owner.request.get(account_server+'/static/manifest.webmanifest').status==200
        owner.get_by_role('button',name='Sign out',exact=True).click()
        expect(owner.get_by_role('button',name='Sign in',exact=True)).to_be_visible()
        assert owner.evaluate('sessionStorage.getItem("backline_session")') is None
        assert not errors,errors
        browser.close()

@pytest.mark.parametrize('width',[1280,390])
def test_shared_venue_and_calendar_subscription_ui(account_server,accounts,width):
    app,client,band,other,base,users,headers,gig,_,_=accounts
    with app.db() as con:con.execute("INSERT INTO band_users VALUES(?,?,'manager')",(other,users['owner']))
    venue=client.post(base+'/venues',headers=headers['owner'],json={'name':'Synthetic Shared Hall','address':'123 Example Road',
        'contacts':[{'name':'Private Engineer','phone':'DO NOT SHARE'}],'load_in_notes':'PRIVATE ACCESS NOTE'}).json()['id']
    calendar=client.post(base+'/calendars',headers=headers['owner'],json={'name':'Selected dates'}).json()['id']
    client.put(base+f'/events/{gig}/calendar',headers=headers['owner'],json={'calendar_id':calendar})
    with sync_playwright() as p:
        browser=p.chromium.launch();owner=browser.new_page(viewport={'width':width,'height':900})
        sign_in(owner,account_server,'owner');navigate(owner,'venues')
        owner.get_by_role('button',name='Manage venue sharing',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Share venue with another band')
        dialog.get_by_label('Destination band',exact=True).select_option(label='Isolated Band')
        dialog.get_by_label('Address',exact=True).check()
        dialog.get_by_role('button',name='Preview selected fields',exact=True).click()
        expect(dialog.locator('#sharePreview')).to_contain_text('123 Example Road')
        expect(dialog.locator('#sharePreview')).not_to_contain_text('DO NOT SHARE')
        dialog.get_by_role('button',name='Confirm sharing',exact=True).click()
        expect(dialog.get_by_role('button',name='Revoke',exact=True)).to_be_visible()
        dialog.get_by_role('button',name='Close',exact=True).click()
        owner.locator('#bandPicker:visible,#mobileBandPicker:visible').select_option(str(other))
        expect(owner.get_by_role('heading',name='Overview',exact=True)).to_be_visible()
        navigate(owner,'venues')
        expect(owner.get_by_text('Synthetic Shared Hall',exact=True)).to_be_visible()
        assert 'DO NOT SHARE' not in owner.locator('body').inner_text()
        owner.locator('#bandPicker:visible,#mobileBandPicker:visible').select_option(str(band))
        navigate(owner,'schedule')
        owner.get_by_role('button',name='Subscriptions',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Calendar subscriptions')
        dialog.get_by_label('Calendar',exact=True).select_option(label='Selected dates')
        owner.once('dialog',lambda message:message.accept())
        dialog.get_by_role('button',name='Create secret subscription URL',exact=True).click()
        url=dialog.get_by_label('Secret calendar URL',exact=True)
        expect(url).to_be_visible()
        secret_url=url.input_value()
        assert owner.request.get(secret_url).status==200
        dialog.get_by_role('button',name='Revoke',exact=True).click()
        expect(dialog.get_by_text('Subscription 1 · Revoked',exact=True)).to_be_visible()
        assert owner.request.get(secret_url).status==404
        browser.close()
