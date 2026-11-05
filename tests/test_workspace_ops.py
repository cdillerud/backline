"""Synthetic private workspace parity regressions."""
import datetime
import importlib
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'workspace.sqlite'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','0')
    import src.app as module
    importlib.reload(module)
    c=TestClient(module.app)
    b=c.post('/api/bands',json={'name':'Synthetic Workspace'}).json()['id']
    other=c.post('/api/bands',json={'name':'Other Workspace'}).json()['id']
    base=f'/api/bands/{b}'
    gig=c.post(base+'/events',json={'kind':'Gig','title':'Synthetic Show','date':'2026-11-15'}).json()['id']
    song=c.post(base+'/songs',json={'title':'Opening song','duration_seconds':180}).json()['id']
    member=c.post(base+'/members',json={'name':'Synthetic Player'}).json()['id']
    return module,c,b,other,base,gig,song,member

def test_venue_contacts_tags_and_gig_link(workspace):
    _,c,b,other,base,gig,_,_=workspace
    body={'name':'Fictional Club','contacts':[{'name':'Pat Example','role':'Engineer','phone':'555-0101'}],
          'load_in_notes':'Side door on Example Road','curfew_notes':'Hard 23:00 curfew','tags':['club','club','midwest'],'favourite':True}
    made=c.post(base+'/venues',json=body)
    assert made.status_code==201,made.text
    venue=made.json()['id']
    assert c.get(base+'/venues').json()[0]['tags']==['club','midwest']
    assert c.put(base+f'/events/{gig}/venue',json={'venue_id':venue}).status_code==200
    assert c.get(base+f'/events/{gig}/venue').json()['contacts'][0]['role']=='Engineer'
    assert c.put(f'/api/bands/{other}/events/{gig}/venue',json={'venue_id':venue}).status_code==404
    othergig=c.post(f'/api/bands/{other}/events',json={'kind':'Gig','title':'Other','date':'2026-11-15'}).json()['id']
    assert c.put(f'/api/bands/{other}/events/{othergig}/venue',json={'venue_id':venue}).status_code==404
    assert c.put(base+f'/venues/{venue}',json={**body,'curfew_notes':'Updated curfew'}).status_code==200
    assert c.get(base+f'/events/{gig}/venue').json()['curfew_notes']=='Updated curfew'
    pdf=c.get(base+f'/gigs/{gig}/packet.pdf')
    text=' '.join(' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages).split())
    assert 'Side door on Example Road' in text and 'Updated curfew' in text and 'Pat Example' in text

def test_task_assignment_links_reminders_and_completion(workspace):
    _,c,_,other,base,gig,song,member=workspace
    body={'title':'Print setlists','event_id':gig,'song_id':song,'assignee_id':member,
          'due_date':str(datetime.date.today()+datetime.timedelta(days=1))}
    made=c.post(base+'/tasks',json=body)
    assert made.status_code==201,made.text
    task=made.json()['id']
    assert c.get(base+'/tasks').json()[0]['reminder']=='due_tomorrow'
    assert c.put(base+f'/tasks/{task}',json={**body,'completed':True}).status_code==200
    assert c.get(base+'/tasks').json()[0]['reminder']=='completed'
    assert c.post(f'/api/bands/{other}/tasks',json=body).status_code==404
    assert c.put(f'/api/bands/{other}/tasks/{task}',json={'title':'Denied'}).status_code==404
    assert c.post(base+'/tasks',json={'title':' '}).status_code==422
    assert c.post(base+'/tasks',json={'title':'Bad date','due_date':'tomorrow'}).status_code==422

def test_repertoire_order_runtime_and_setlist_pdf(workspace):
    _,c,_,other,base,gig,song,_=workspace
    data={'title':'Opening song','artist':'Synthetic Artist','song_key':'Am','bpm':120,
          'duration_seconds':180,'tags':['opener'],'reference_url':'https://example.test/arrangement.mp3'}
    assert c.put(base+f'/songs/{song}',json=data).status_code==200
    assert c.get(base+'/song-details').json()[0]['tags']==['opener']
    assert c.put(base+f'/songs/{song}',json={**data,'reference_url':'javascript:alert(1)'}).status_code==422
    assert c.put(f'/api/bands/{other}/songs/{song}',json=data).status_code==404
    song2=c.post(base+'/songs',json={'title':'Closing song','duration_seconds':240}).json()['id']
    setlist=c.post(base+'/setlists',json={'title':'Set one','event_id':gig,'song_ids':[song,song2]}).json()['id']
    assert c.put(base+f'/setlists/{setlist}',json={'title':'Revised set','song_ids':[song2,song]}).status_code==200
    songs=c.get(base+'/setlists').json()[0]['songs']
    assert [s['id'] for s in songs]==[song2,song]
    assert sum(s['duration_seconds'] for s in songs)==420
    response=c.get(base+f'/setlists/{setlist}/pdf')
    text=' '.join(' '.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages).split())
    assert 'Runtime 7:00' in text and 'Am / 120' in text and 'Closing song' in text
    assert c.get(f'/api/bands/{other}/setlists/{setlist}/pdf').status_code==404
    other_song=c.post(f'/api/bands/{other}/songs',json={'title':'Other'}).json()['id']
    assert c.put(base+f'/setlists/{setlist}',json={'title':'Bad links','song_ids':[other_song]}).status_code==404
    assert c.get(base+'/setlists').json()[0]['title']=='Revised set' # Transaction retains prior order after rejected edit.

def test_calendars_colour_assignment_and_ical(workspace):
    _,c,b,other,base,gig,_,_=workspace
    calendar=c.post(base+'/calendars',json={'name':'Tour dates','color':'#93c5fd'}).json()['id']
    assert c.post(base+'/calendars',json={'name':'Unsafe','color':'red;script'}).status_code==422
    assert c.put(base+f'/events/{gig}/calendar',json={'calendar_id':calendar}).status_code==200
    events=c.get(base+'/calendar/events').json()
    assert events[0]['calendar_name']=='Tour dates' and events[0]['calendar_color']=='#93c5fd'
    assert c.put(f'/api/bands/{other}/events/{gig}/calendar',json={'calendar_id':calendar}).status_code==404
    advance={'timezone':'America/Chicago','show_time':'23:00','load_in':'17:00','doors':'19:00'}
    assert c.put(base+f'/gigs/{gig}/advance',json=advance).status_code==200
    response=c.get(base+'/calendar.ics')
    assert response.headers['cache-control']=='no-store'
    assert 'DTSTART:20261116T050000Z' in response.text # 23:00 CST, next UTC date.
    assert 'Load-in: 17:00' in response.text and 'Doors: 19:00' in response.text
    assert f'UID:backline-{b}-{gig}@backline.local' in response.text
    from src.calendars import fold_line,ical_escape
    assert max(len(line.encode()) for line in fold_line('SUMMARY:'+'音'*100).split('\r\n'))<=75
    assert '\r\n' not in ical_escape('title\r\nBEGIN:VEVENT')

def test_private_features_keep_existing_account_boundaries(workspace,monkeypatch):
    module,c,b,other,base,gig,song,_=workspace
    from src.accounts import make_session,hash_password
    with module.db() as con:
        user=con.execute('INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)',
            ('viewer@example.test','Viewer',hash_password('synthetic-password-123'))).lastrowid
        con.execute('INSERT INTO band_users VALUES(?,?,?)',(b,user,'viewer'))
        token=make_session(con,user)
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','1')
    h={'Authorization':'Bearer '+token}
    for resource in ['venues','tasks','song-details','calendar/events','calendar.ics']:
        assert c.get(base+'/'+resource).status_code==401
        assert c.get(base+'/'+resource,headers=h).status_code==200
        assert c.get(f'/api/bands/{other}/'+resource,headers=h).status_code==403
    for resource in ['venues','tasks','calendars']:
        assert c.post(base+'/'+resource,headers=h,json={}).status_code==403
    assert c.put(base+f'/songs/{song}',headers=h,json={}).status_code==403
