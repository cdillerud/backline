"""Adversarial role and identity coverage for approved private collaboration."""
import importlib
import time
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'collaboration.sqlite'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1');monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','1')
    import src.app as app
    importlib.reload(app)
    from src.accounts import hash_password,make_session
    with app.db() as con:
        b=con.execute("INSERT INTO bands(name) VALUES('Synthetic Collaboration')").lastrowid
        other=con.execute("INSERT INTO bands(name) VALUES('Isolated Band')").lastrowid
        users={};headers={}
        for role in ['owner','manager','member','viewer','treasurer','outsider']:
            uid=con.execute('INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)',
                (role+'@example.test',role.title(),hash_password('synthetic-password-123'))).lastrowid
            con.execute('INSERT INTO band_users VALUES(?,?,?)',(other if role=='outsider' else b,uid,'owner' if role=='outsider' else role))
            users[role]=uid;headers[role]={'Authorization':'Bearer '+make_session(con,uid)}
        member=con.execute("INSERT INTO members(band_id,name,instrument) VALUES(?,'Stage Name','Guitar')",(b,)).lastrowid
    c=TestClient(app.app);base=f'/api/bands/{b}'
    gig=c.post(base+'/events',headers=headers['owner'],json={'kind':'Gig','title':'Synthetic Show','date':'2026-11-15'}).json()['id']
    song=c.post(base+'/songs',headers=headers['owner'],json={'title':'Synthetic Song'}).json()['id']
    thread=c.post(base+'/discussions',headers=headers['owner'],json={'title':'Show planning','scope':'song','scope_id':song}).json()['id']
    yield app,c,b,other,base,users,headers,gig,member,thread

def test_rsvp_is_self_only_and_role_scoped(accounts):
    _,c,_,other,base,users,h,gig,_,_=accounts
    path=base+f'/events/{gig}/rsvp'
    assert c.put(path,json={'response':'yes'}).status_code==401
    for role in ['owner','manager','member']:
        assert c.put(path,headers=h[role],json={'response':'yes'}).status_code==200
    for role in ['viewer','treasurer','outsider']:
        assert c.put(path,headers=h[role],json={'response':'yes'}).status_code==403
    assert c.put(path,headers=h['member'],json={'response':'no','user_id':users['owner']}).status_code==422
    assert c.put(base+f'/events/{gig}/venue',headers=h['member'],json={'venue_id':1}).status_code==403
    assert c.post(base+f'/events/{gig}/rsvp-requests',headers=h['member']).status_code==403
    assert c.post(base+f'/events/{gig}/rsvp-requests',headers=h['manager']).status_code==200
    rows=c.get(base+f'/events/{gig}/rsvps',headers=h['member']).json()
    assert next(row for row in rows if row['user_id']==users['owner'])['response']=='yes'
    assert c.get(f'/api/bands/{other}/events/{gig}/rsvps',headers=h['member']).status_code==403

def test_discussion_mentions_edits_and_typing(accounts):
    app,c,_,_,base,users,h,_,_,thread=accounts
    path=base+f'/discussions/{thread}'
    made=c.post(path+'/posts',headers=h['member'],json={'body':'@Manager check the inputs','mention_user_ids':[users['manager']]})
    assert made.status_code==201,made.text
    post=made.json()['id']
    assert c.put(path+f'/posts/{post}',headers=h['manager'],json={'body':'Overwrite another author'}).status_code==403
    assert c.put(path+f'/posts/{post}',headers=h['member'],json={'body':'Revised own reply'}).status_code==200
    assert c.post(path+'/posts',headers=h['member'],json={'body':'Spoof','user_id':users['owner']}).status_code==422
    assert c.post(path+'/posts',headers=h['member'],json={'body':'Cross-band mention','mention_user_ids':[users['outsider']]}).status_code==422
    for role in ['viewer','treasurer','outsider']:
        assert c.post(path+'/posts',headers=h[role],json={'body':'Denied'}).status_code==403
    assert c.post(base+'/discussions',headers=h['member'],json={'title':'Unapproved thread'}).status_code==403
    assert c.post(path+'/typing',headers=h['member']).status_code==200
    typing=c.get(path+'/typing',headers=h['manager']).json()
    assert typing[0]['id']==users['member']
    with app.db() as con:con.execute('UPDATE typing_presence SET expires_at=0')
    assert c.get(path+'/typing',headers=h['manager']).json()==[]
    assert len(c.get('/api/me/notifications',headers=h['manager']).json())==1
    assert c.get(path+'/posts?after='+str(post),headers=h['member']).json()==[]

def test_roster_assignment_notifications_and_privacy(accounts):
    app,c,b,_,base,users,h,gig,member,_=accounts
    link=base+f'/members/{member}/account'
    assert c.put(link,headers=h['member'],json={'user_id':users['member']}).status_code==403
    assert c.put(link,headers=h['owner'],json={'user_id':users['outsider']}).status_code==422
    assert c.put(link,headers=h['owner'],json={'user_id':users['member']}).status_code==200
    task={'title':'Print setlists','assignee_id':member,'event_id':gig}
    made=c.post(base+'/tasks',headers=h['owner'],json=task)
    assert made.status_code==201,made.text
    assert c.put(base+'/tasks/'+str(made.json()['id']),headers=h['owner'],json=task).status_code==200
    notifications=c.get('/api/me/notifications',headers=h['member']).json()
    assert len(notifications)==1 and notifications[0]['category']=='task'
    notification_id=notifications[0]['id']
    assert c.post(f'/api/me/notifications/{notification_id}/read',headers=h['owner']).status_code==404
    assert c.post(f'/api/me/notifications/{notification_id}/read',headers=h['member']).status_code==200
    assert next(row for row in c.get(base+f'/events/{gig}/rsvps',headers=h['owner']).json() if row['user_id']==users['member'])['display_name']=='Stage Name'
    with app.db() as con:con.execute('DELETE FROM band_users WHERE band_id=? AND user_id=?',(b,users['member']))
    assert c.get('/api/me/notifications',headers=h['member']).json()==[]
    assert c.post(f'/api/me/notifications/{notification_id}/read',headers=h['member']).status_code==404

def test_email_preferences_queue_daily_digest_and_retry(accounts):
    app,c,b,_,_,users,h,_,_,_=accounts
    prefs={'task':'daily','rsvp':'none','mention':'immediate','timezone':'America/Chicago'}
    assert c.put('/api/me/notification-preferences',headers=h['member'],json=prefs).status_code==200
    assert c.put('/api/me/notification-preferences',headers=h['member'],json={**prefs,'user_id':users['owner']}).status_code==422
    from src.collaboration import notify,dispatch_outbox
    now=1793023200
    with app.db() as con:
        notify(con,b,users['member'],'task','Task 1','task:1',now)
        notify(con,b,users['member'],'task','Task 2','task:2',now)
        notify(con,b,users['member'],'rsvp','RSVP','event:1',now)
        notify(con,b,users['member'],'mention','Mention','post:1',now)
        sent=[]
        assert dispatch_outbox(con,lambda **message:sent.append(message),now)==1
        assert len(sent[0]['items'])==1
        available=con.execute("SELECT max(available_at) FROM email_outbox WHERE status='pending'").fetchone()[0]
        assert available>now
        assert dispatch_outbox(con,lambda **message:sent.append(message),available)==1
        assert len(sent[-1]['items'])==2
        assert dispatch_outbox(con,lambda **message:sent.append(message),available)==0
        notify(con,b,users['member'],'mention','Retry me','post:2',now)
        def failed(**message):raise OSError('Synthetic transport failure')
        with pytest.raises(OSError):dispatch_outbox(con,failed,available)
        assert dispatch_outbox(con,lambda **message:sent.append(message),available)==1
        assert dispatch_outbox(con,lambda **message:sent.append(message),available)==0
        assert all(message['idempotency_key'].startswith('backline-') for message in sent)

def test_session_events_share_calendar_and_rsvp_models(accounts):
    _,c,_,_,base,_,h,_,_,_=accounts
    made=c.post(base+'/events',headers=h['owner'],json={'kind':'Session','title':'Studio tracking','date':'2026-11-17'})
    assert made.status_code==201,made.text
    event_id=made.json()['id']
    assert next(e for e in c.get(base+'/events',headers=h['member']).json() if e['id']==event_id)['kind']=='Session'
    assert next(e for e in c.get(base+'/calendar/events',headers=h['member']).json() if e['id']==event_id)['kind']=='Session'
    assert c.put(base+f'/events/{event_id}/rsvp',headers=h['member'],json={'response':'yes'}).status_code==200
    assert c.get(base+f'/gigs/{event_id}/packet',headers=h['member']).status_code==404

def test_member_dashboard_and_calendar_do_not_expose_finance(accounts):
    _,c,_,_,base,_,h,gig,_,_=accounts
    for role in ['member','viewer']:
        dashboard=c.get(base+'/dashboard',headers=h[role]).json()
        assert 'finance' not in dashboard
        assert all('fee_cents' not in row for row in dashboard['upcoming'])
        assert all('fee_cents' not in row for row in c.get(base+'/events',headers=h[role]).json())
        assert all('fee_cents' not in row for row in c.get(base+'/calendar/events',headers=h[role]).json())
    for role in ['owner','manager','treasurer']:
        assert 'finance' in c.get(base+'/dashboard',headers=h[role]).json()

def test_due_tomorrow_reminders_are_personal_and_idempotent(accounts):
    import datetime
    from zoneinfo import ZoneInfo
    app,c,b,_,base,users,h,_,member,_=accounts
    c.put(base+f'/members/{member}/account',headers=h['owner'],json={'user_id':users['member']})
    now=int(time.time());local=datetime.datetime.fromtimestamp(now,ZoneInfo('America/Chicago')).date()
    task=c.post(base+'/tasks',headers=h['owner'],json={'title':'Print tomorrow’s set','assignee_id':member,'due_date':str(local+datetime.timedelta(days=1))}).json()['id']
    one=c.get('/api/me/notifications',headers=h['member']).json()
    two=c.get('/api/me/notifications',headers=h['member']).json()
    assert len(one)==len(two)==2
    assert any(n['title']=='Due tomorrow: Print tomorrow’s set' for n in one)
    assert c.get('/api/me/notifications',headers=h['owner']).json()==[]
    c.put('/api/me/notification-preferences',headers=h['member'],json={'task':'none'})
    with app.db() as con:
        assert con.execute("SELECT count(*) FROM email_outbox WHERE status='pending'").fetchone()[0]==0
