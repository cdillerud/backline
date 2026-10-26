"""Desktop/mobile acceptance for crew changes, guest approvals, hotels and reviewed imports."""
import datetime
from io import BytesIO
import pytest
from pypdf import PdfReader
from playwright.sync_api import sync_playwright,expect
from test_collaboration import accounts
from test_browser_collaboration import account_server,sign_in,navigate

@pytest.mark.parametrize('width',[1280,390])
def test_guest_request_approval_and_box_office_pdf(account_server,accounts,width,tmp_path):
    _,c,_,_,base,_,h,gig,_,_=accounts
    with sync_playwright() as p:
        browser=p.chromium.launch();owner=browser.new_page(viewport={'width':width,'height':900});member=browser.new_page(viewport={'width':width,'height':900})
        errors=[];owner.on('pageerror',lambda e:errors.append(str(e)));member.on('pageerror',lambda e:errors.append(str(e)))
        sign_in(owner,account_server,'owner');navigate(owner,'operations')
        owner.get_by_role('tab',name='Guests & passes',exact=True).click()
        owner.get_by_role('button',name='Edit cutoff, passes and limit',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Guest-list policy')
        dialog.get_by_label('Maximum approved guests',exact=True).fill('2')
        dialog.get_by_label('Pass types (comma separated)',exact=True).fill('Guest, VIP')
        dialog.get_by_role('button',name='Save',exact=True).click();expect(dialog).to_have_count(0)
        sign_in(member,account_server,'member');navigate(member,'operations')
        member.get_by_role('tab',name='Guests & passes',exact=True).click()
        member.get_by_role('button',name='Request guest passes',exact=True).click()
        dialog=member.get_by_role('dialog',name='Request guest passes')
        dialog.get_by_label('Guest name',exact=True).fill('Synthetic Guest')
        dialog.get_by_label('Number of guests',exact=True).fill('2')
        dialog.get_by_label('Pass type',exact=True).select_option('VIP')
        dialog.get_by_label('Private note to the manager',exact=True).fill('PRIVATE GUEST NOTE')
        dialog.get_by_role('button',name='Save',exact=True).click();expect(dialog).to_have_count(0)
        expect(member.get_by_text('Synthetic Guest',exact=True)).to_be_visible()
        assert member.get_by_role('button',name='Download box-office PDF',exact=True).count()==0
        owner.get_by_role('button',name='Refresh operations',exact=True).click()
        owner.get_by_role('button',name='Review request',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Review guest request')
        dialog.get_by_label('Decision',exact=True).select_option('approved')
        dialog.get_by_label('Decision note',exact=True).fill('Promoter approved')
        dialog.get_by_role('button',name='Save',exact=True).click();expect(dialog).to_have_count(0)
        with owner.expect_download() as downloaded:owner.get_by_role('button',name='Download box-office PDF',exact=True).click()
        path=tmp_path/'guests.pdf';downloaded.value.save_as(path)
        text=' '.join(page.extract_text() for page in PdfReader(path).pages)
        assert 'Synthetic Guest' in text and 'VIP' in text and 'PRIVATE GUEST NOTE' not in text
        member.get_by_role('button',name='Refresh operations',exact=True).click()
        expect(member.get_by_text('Promoter approved',exact=True)).to_be_visible()
        member.once('dialog',lambda d:d.accept());member.get_by_role('button',name='Cancel my request',exact=True).click()
        expect(member.get_by_text('cancelled',exact=False)).to_be_visible()
        assert not errors,errors
        browser.close()

@pytest.mark.parametrize('width',[1280,390])
def test_urgent_change_acknowledgement_and_history(account_server,accounts,width):
    app,c,_,_,base,_,h,gig,_,_=accounts
    with app.db() as con:con.execute('UPDATE events SET date=? WHERE id=?',(datetime.datetime.now(datetime.timezone.utc).date().isoformat(),gig))
    c.put(base+f'/gigs/{gig}/advance',headers=h['owner'],json={'timezone':'UTC','load_in':'15:00','show_time':'20:00'})
    with sync_playwright() as p:
        browser=p.chromium.launch();owner=browser.new_page(viewport={'width':width,'height':900});member=browser.new_page(viewport={'width':width,'height':900})
        sign_in(member,account_server,'member');navigate(member,'operations')
        sign_in(owner,account_server,'owner');navigate(owner,'showops')
        owner.get_by_role('tab',name='Advances & riders',exact=True).click()
        owner.locator('[data-advance-field="load_in"]').fill('16:00')
        owner.locator('[data-advance-field="change_reason"]').fill('Promoter moved load-in')
        owner.get_by_role('button',name='Save advancement',exact=True).click()
        expect(owner.get_by_text('Venue advancement saved',exact=True)).to_be_visible()
        expect(member.get_by_role('button',name='Acknowledge change',exact=True)).to_be_visible(timeout=15000)
        member.get_by_role('button',name='Acknowledge change',exact=True).click()
        expect(member.get_by_text('Change acknowledged',exact=True)).to_be_visible()
        navigate(owner,'operations')
        expect(owner.locator('.operationsAlert')).to_contain_text('1/5 acknowledgements')
        history=owner.locator('.operationHistory').first
        history.locator('summary').click()
        expect(history).to_contain_text('Promoter moved load-in')
        expect(history).to_contain_text('15:00');expect(history).to_contain_text('16:00')
        assert member.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        browser.close()

@pytest.mark.parametrize('width',[1280,390])
def test_rooming_privacy_and_reviewed_import_ui(account_server,accounts,width,tmp_path):
    _,c,_,_,base,_,h,_,_,_=accounts
    tour=c.post(base+'/tours',headers=h['owner'],json={'name':'Reviewed Tour'}).json()['id']
    start=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=3)
    source='date,city,venue,arrival_time\n'+start.date().isoformat()+',Minneapolis,Synthetic Hall,16:00\ninvalid,Madison,Bad date,16:00\n'+(start.date()+datetime.timedelta(days=1)).isoformat()+',Chicago,Fictional Club,17:00\n'
    file=tmp_path/'synthetic-tour.csv';file.write_text(source)
    with sync_playwright() as p:
        browser=p.chromium.launch();owner=browser.new_page(viewport={'width':width,'height':900});member=browser.new_page(viewport={'width':width,'height':900})
        errors=[];owner.on('pageerror',lambda e:errors.append(str(e)));member.on('pageerror',lambda e:errors.append(str(e)))
        sign_in(owner,account_server,'owner');navigate(owner,'operations')
        owner.get_by_role('tab',name='Hotels & rooming',exact=True).click()
        owner.get_by_role('button',name='+ Hotel stay',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Add hotel stay')
        dialog.get_by_label('Hotel name',exact=True).fill('Synthetic Hotel')
        dialog.get_by_label('Hotel address',exact=True).fill('123 Example Street')
        dialog.get_by_label('Check-in including UTC offset',exact=True).fill(start.isoformat())
        dialog.get_by_label('Check-out including UTC offset',exact=True).fill((start+datetime.timedelta(days=1)).isoformat())
        dialog.get_by_label('Private confirmation reference',exact=True).fill('PRIVATE CONFIRMATION')
        dialog.get_by_label('Private manager notes',exact=True).fill('PRIVATE MANAGER NOTES')
        dialog.get_by_role('button',name='Save',exact=True).click();expect(dialog).to_have_count(0)
        owner.get_by_role('button',name='+ Room assignment',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Add room assignment')
        dialog.get_by_label('Room number or label',exact=True).fill('101')
        dialog.get_by_label('Room type',exact=True).select_option('twin')
        dialog.get_by_label('Room capacity',exact=True).fill('2')
        dialog.get_by_label('Owner',exact=True).check();dialog.get_by_label('Member',exact=True).check()
        dialog.get_by_role('button',name='Save',exact=True).click();expect(dialog).to_have_count(0)
        with owner.expect_download() as downloaded:owner.get_by_role('button',name='Download rooming PDF',exact=True).click()
        path=tmp_path/'rooms.pdf';downloaded.value.save_as(path)
        text=' '.join(page.extract_text() for page in PdfReader(path).pages)
        assert 'Owner' in text and 'Member' in text and 'PRIVATE CONFIRMATION' not in text
        sign_in(member,account_server,'member');navigate(member,'operations')
        member.get_by_role('tab',name='My hotel details',exact=True).click()
        expect(member.get_by_role('heading',name='Synthetic Hotel',exact=True)).to_be_visible()
        assert 'PRIVATE' not in member.locator('body').inner_text()
        assert member.get_by_role('button',name='Edit room',exact=True).count()==0
        owner.get_by_role('tab',name='Itinerary imports',exact=True).click()
        owner.get_by_role('button',name='+ Review CSV itinerary',exact=True).click()
        dialog=owner.get_by_role('dialog',name='Review CSV itinerary')
        dialog.get_by_label('Destination tour',exact=True).select_option(label='Reviewed Tour')
        dialog.get_by_label('CSV file',exact=True).set_input_files(file)
        dialog.get_by_role('button',name='Create review draft',exact=True).click();expect(dialog).to_have_count(0)
        expect(owner.get_by_text('Draft created — no tour stops added',exact=True)).to_be_visible()
        assert c.get(base+f'/tours/{tour}/route',headers=h['owner']).json()['stops']==[]
        owner.get_by_text('Source evidence',exact=True).click()
        with owner.expect_download() as review_download:
            owner.get_by_role('button',name='Download review CSV',exact=True).click()
        review_path=tmp_path/'itinerary-review.csv'
        review_download.value.save_as(review_path)
        review_text=review_path.read_text()
        assert 'Source line' in review_text and 'Invalid' not in review_text[:75]
        assert 'Duplicate existing' in review_text and 'Fictional Club' in review_text
        owner.get_by_role('button',name='View original CSV',exact=True).click()
        source_dialog=owner.get_by_role('dialog',name='Original itinerary source')
        expect(source_dialog.get_by_label('Original CSV',exact=True)).to_have_value(source)
        source_dialog.get_by_role('button',name='Close',exact=True).click()
        owner.get_by_label('Select import row 1',exact=True).check()
        expect(owner.get_by_label('Select import row 2',exact=True)).to_be_disabled()
        owner.get_by_label('Select import row 3',exact=True).check()
        owner.get_by_label('I reviewed these rows and want to add the selected stops.',exact=True).check()
        owner.get_by_role('button',name='Apply selected rows',exact=True).click()
        expect(owner.get_by_text('Reviewed stops added to the tour',exact=True)).to_be_visible()
        assert len(c.get(base+f'/tours/{tour}/route',headers=h['owner']).json()['stops'])==2
        assert owner.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not errors,errors
        browser.close()

def test_delayed_private_operations_response_cannot_restore_data_after_logout(account_server,accounts):
    _,_,_,_,base,_,_,_,_,_=accounts
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        sign_in(page,account_server,'owner')
        held=[]
        page.route('**'+base+'/lodging',lambda route:held.append(route))
        navigate(page,'operations')
        # This wait also pumps Playwright route callbacks without an arbitrary sleep.
        page.wait_for_function("document.querySelector('h1').textContent==='Overview'")
        for _ in range(50):
            if held:break
            page.wait_for_timeout(50)
        assert held,'Private lodging request was not intercepted'
        page.get_by_role('button',name='Sign out',exact=True).click()
        expect(page.get_by_role('button',name='Sign in',exact=True)).to_be_visible()
        held[0].fulfill(status=200,content_type='application/json',body='{"items":[{"hotel":"PRIVATE STALE HOTEL"}],"can_manage":true}')
        page.wait_for_load_state('networkidle')
        expect(page.get_by_role('button',name='Sign in',exact=True)).to_be_visible()
        assert 'PRIVATE STALE HOTEL' not in page.locator('body').inner_text()
        assert page.evaluate('state.data.ops===undefined')
        browser.close()
