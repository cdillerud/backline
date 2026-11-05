"""Synthetic schedule, overnight, PDF and authorization regressions."""
import importlib
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

@pytest.fixture
def show(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'schedule.db'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','0')
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    band=client.post('/api/bands',json={'name':'Synthetic Touring Band'}).json()['id']
    other=client.post('/api/bands',json={'name':'Isolated Band'}).json()['id']
    gig=client.post(f'/api/bands/{band}/events',json={'kind':'Gig','title':'Synthetic late show',
        'date':'2026-11-15','venue':'Fictional Hall'}).json()['id']
    body={'timezone':'America/Chicago','venue_contact':'Pat Example','production_contact':'Alex Example',
          'contact_phone':'555-0100','load_in':'17:00','soundcheck':'18:00','doors':'19:00',
          'show_time':'23:00','curfew':'01:00','day_offsets':{'curfew':1},'status':'confirmed',
          'venue_address':'123 Fictional Street','lodging':'Synthetic Hotel',
          'parking':'Rear loading dock','hospitality':'Meal at 18:30','settlement':'Office after show',
          'schedule':[{'title':'Merch count','time':'00:30','day_offset':1,'owner':'Sam Example',
                       'location':'Lobby','notes':'Count shirts & posters <together>'}]}
    return module,client,band,other,gig,body

def test_overnight_schedule_and_confirmed_pdf(show):
    module,client,band,other,gig,body=show
    path=f'/api/bands/{band}/gigs/{gig}'
    assert client.put(path+'/advance',json=body).status_code==200
    timeline=client.get(path+'/timeline').json()
    assert timeline['warnings']==[]
    assert [e['title'] for e in timeline['entries']]==['Load-in','Soundcheck','Doors','Show time','Merch count','Curfew']
    assert timeline['entries'][-1]['day_offset']==1
    # API export must use the saved advance even without generated template documents.
    response=client.get(path+'/packet.pdf')
    assert response.status_code==200
    text=' '.join(' '.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages).split())
    for expected in ['America/Chicago','Pat Example','555-0100','Rear loading dock','Synthetic Hotel',
                     'Merch count','Sam Example','Lobby','Count shirts & posters <together>','01:00 (+1)']:
        assert expected in text
    body['venue_contact']='Updated contact'
    assert client.put(path+'/advance',json=body).status_code==200
    refreshed=client.get(path+'/packet.pdf')
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(refreshed.content)).pages)
    assert 'Updated contact' in text and 'Pat Example' not in text
    assert client.get(f'/api/bands/{other}/gigs/{gig}/timeline').status_code==404
    assert client.get(f'/api/bands/{other}/gigs/{gig}/packet.pdf').status_code==404

@pytest.mark.parametrize('change',[
    {'load_in':'25:00'},{'soundcheck':'6pm'},{'timezone':'Not/AZone'},
    {'timezone':''},{'doors':'16:00'},{'day_offsets':{'curfew':0}},
    {'day_offsets':{'doors':-1}},{'day_offsets':{'unknown':1}},
    {'schedule':[{'title':' ','time':'12:00'}]},
    {'schedule':[{'title':'Call','time':'00:30','day_offset':3}]},
])
def test_schedule_rejects_bad_or_unconfirmed_times(show,change):
    _,client,band,_,gig,body=show
    assert client.put(f'/api/bands/{band}/gigs/{gig}/advance',json={**body,**change}).status_code==422

def test_provisional_schedule_and_rehearsal_scope(show):
    _,client,band,_,_,body=show
    gig=client.post(f'/api/bands/{band}/events',json={'kind':'Rehearsal','title':'Practice','date':'2026-11-15'}).json()['id']
    assert client.get(f'/api/bands/{band}/gigs/{gig}/timeline').status_code==404
    from src.show_schedule import show_timeline
    result=show_timeline({'load_in':'legacy time','status':'draft'})
    assert result['entries']==[] and len(result['warnings'])>=3

def test_schedule_permissions_with_real_sessions(show,monkeypatch):
    module,client,band,other,gig,body=show
    from src.accounts import hash_password,make_session
    with module.db() as con:
        user=con.execute('INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)',
                         ('reader@example.test','Reader',hash_password('synthetic-password-123'))).lastrowid
        con.execute('INSERT INTO band_users VALUES(?,?,?)',(band,user,'viewer'))
        token=make_session(con,user)
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','1')
    path=f'/api/bands/{band}/gigs/{gig}'
    headers={'Authorization':'Bearer '+token}
    assert client.get(path+'/timeline').status_code==401
    assert client.get(path+'/timeline',headers=headers).status_code==200
    assert client.put(path+'/advance',json=body,headers=headers).status_code==403
    assert client.put(path+'/stage',json={},headers=headers).status_code==403
    assert client.get(f'/api/bands/{other}/gigs/{gig}/timeline',headers=headers).status_code==403
    assert client.get(f'/api/bands/{other}/gigs/{gig}/packet.pdf',headers=headers).status_code==403
