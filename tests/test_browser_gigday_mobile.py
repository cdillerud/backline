"""Gig Day acceptance at narrow and wide viewports, using authenticated synthetic band data."""
import datetime
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from test_collaboration import accounts
from test_browser_collaboration import account_server,sign_in

@pytest.mark.parametrize("width",[320,375,390,768,1280])
def test_gig_day_mobile_view_and_show_switch(account_server,accounts,width):
    _,client,_,_,base,_,headers,first_gig,_,_=accounts
    other=client.post(base+'/events',headers=headers['owner'],json={
        'kind':'Gig','title':'Second synthetic show','venue':'Sample Room',
        'date':str(datetime.date.today()+datetime.timedelta(days=24))})
    assert other.status_code==201,other.text
    second_gig=other.json()['id']
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':width,'height':760},device_scale_factor=1)
        failures=[]
        page.on('pageerror',lambda error:failures.append(str(error)))
        sign_in(page,account_server,'owner')
        snapshots=Path('artifacts/gigday')
        snapshots.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(snapshots/f'home-{width}.png'),full_page=True)
        page.evaluate('(id)=>openShowPacketGig(id,"gigday")',first_gig)
        gigday=page.get_by_role('region',name='Musician gig-day workspace')
        expect(gigday.get_by_role('region',name='Show-day call times')).to_be_visible()
        essentials=gigday.get_by_role('region',name='Your gig essentials')
        expect(essentials).to_be_visible()
        assert essentials.locator(':scope > div').count()==4
        if width<=650:
            assert page.locator('.mobileContextNav').count()==0
        expect(gigday.get_by_role('region',name='Day-of-show timeline')).to_be_visible()
        expect(gigday.get_by_role('region',name='Stage and audio setup')).to_be_visible()
        expect(gigday.get_by_role('region',name='My show availability')).to_be_visible()
        expect(gigday.get_by_role('region',name='Before you go')).to_be_visible()
        assert gigday.locator('.gigdayCall').count()==5
        if width==320:
            assert gigday.locator('.gigdayCallGrid').evaluate(
                '(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length')==2
        page.screenshot(path=str(snapshots/f'gigday-{width}.png'),full_page=True)
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        if width<=650:
            assert gigday.locator('.gigdayActionBar').evaluate(
                '(el)=>getComputedStyle(el).position==="sticky"')
            gigday.get_by_role('region',name='Personal lodging').scroll_into_view_if_needed()
            rail=gigday.locator('.gigdayActionBar')
            assert rail.evaluate('(el)=>{const r=el.getBoundingClientRect();return r.top>=-1&&r.top<70&&r.bottom>0}')
            page.screenshot(path=str(snapshots/f'gigday-scrolled-{width}.png'),full_page=False)
            assert gigday.get_by_role('button',name='My RSVP',exact=True).is_visible()
        checklist=gigday.get_by_role('region',name='Before you go')
        if checklist.locator('.gigdayMoreChecks').count():
            checklist.locator('.gigdayMoreChecks summary').click()
            assert checklist.locator('.gigdayMoreChecks').get_attribute('open') is not None
        if gigday.locator('.gigdayScheduleWarnings details').count():
            gigday.locator('.gigdayScheduleWarnings summary').click()
            assert gigday.locator('.gigdayScheduleWarnings details').get_attribute('open') is not None
        if checklist.locator('[data-gigday-jump]').count():
            checklist.locator('[data-gigday-jump]').first.click()
            assert page.get_by_role('heading',name='My Gig Day',exact=True).is_visible()
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        assert gigday.get_by_role('button',name='My RSVP',exact=True).is_visible()
        assert gigday.get_by_role('button',name='Refresh').is_visible()
        assert gigday.get_by_text('Show details last loaded',exact=False).is_visible()
        assert gigday.get_by_role('button',name='Print gig-day sheet').is_visible()
        page.evaluate("""() => {
          window.__gigdayPrintCalls=0;window.__gigdayPrintStacks=[];
          window.print=()=>{window.__gigdayPrintCalls++;window.__gigdayPrintStacks.push(new Error('Print call').stack)};
        }""")
        gigday.get_by_role('button',name='Print gig-day sheet').click()
        assert page.evaluate("window.__gigdayPrintCalls")==1, page.evaluate("({stacks:window.__gigdayPrintStacks,lastPrint:state.gigdayLastPrintMs,now:Date.now()})")
        if width==390:
            prior_closed=gigday.locator('details:not([open])').count()
            page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
            assert gigday.locator('details:not([open])').count()==0
            page.emulate_media(media='print')
            assert page.locator('.top').is_hidden()
            assert page.locator('.side').is_hidden()
            assert page.locator('.gigdayCallsPanel').is_visible()
            assert page.locator('.app').evaluate('(el)=>getComputedStyle(el).display')=='block'
            assert gigday.locator('.gigdayCallGrid').evaluate(
                '(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length')==3
            page.screenshot(path=str(snapshots/'gigday-print-390.png'),full_page=True)
            page.emulate_media(media='screen')
            page.evaluate("window.dispatchEvent(new Event('afterprint'))")
            assert gigday.locator('details:not([open])').count()==prior_closed
        assert gigday.get_by_role('button',name='Setlist',exact=True).is_visible()
        gigday.get_by_role('button',name='Setlist',exact=True).click()
        assert gigday.get_by_role('region',name='Show music').get_by_role('heading',name='Show music').evaluate(
            '(el)=>document.activeElement===el')
        assert page.get_by_role('heading',name='My Gig Day',exact=True).is_visible()
        gigday.get_by_role('button',name='My tasks',exact=True).click()
        assert gigday.get_by_role('region',name='My show tasks').get_by_role('heading',name='My assignments').evaluate(
            '(el)=>document.activeElement===el')
        gigday.get_by_role('button',name='Urgent changes',exact=True).click()
        assert gigday.get_by_role('region',name='Urgent show changes').get_by_role('heading',name='Urgent show changes').evaluate(
            '(el)=>document.activeElement===el')
        picker=page.get_by_role('combobox',name='Choose gig day show')
        picker.select_option(str(second_gig))
        expect(gigday.get_by_role('heading',name='Second synthetic show')).to_be_visible()
        expect(gigday.get_by_role('region',name='Show-day call times')).to_be_visible()
        assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        expect(picker).to_have_value(str(second_gig))
        page.get_by_role('button',name='My RSVP',exact=True).click()
        expect(page.locator('#gigdayRsvpResponse')).to_be_focused()
        # If the musician navigates away while a show fetch is in flight, the
        # completed network response must not force them back into Gig Day.
        remaining=page.evaluate("""(id) => {
            const pending=openShowPacketGig(id,'gigday');
            state.section='dashboard';
            render();
            return pending.then(()=>state.section);
        }""",first_gig)
        assert remaining=='dashboard'
        expect(page.get_by_role('heading',name='Home',exact=True)).to_be_visible()
        page.evaluate('(id)=>openShowPacketGig(id,"gigday")',first_gig)
        expect(gigday.get_by_role('region',name='Show-day call times')).to_be_visible()
        page.context.set_offline(True)
        expect(gigday.locator('#gigdayConnectivity')).to_be_visible()
        page.context.set_offline(False)
        expect(gigday.locator('#gigdayConnectivity')).to_be_hidden()
        assert not failures,failures
        browser.close()
