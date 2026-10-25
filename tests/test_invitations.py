import importlib
from fastapi.testclient import TestClient
from src.accounts import hash_password

def test_invitation_auth_and_single_use(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'invite.db'))
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','1')
    import src.app as module
    importlib.reload(module)
    with module.db() as db:
        owner=db.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
          ('owner@example.test','Owner',hash_password('long-owner-password-123'))).lastrowid
        band=db.execute("INSERT INTO bands(name) VALUES('Invitation Test')").lastrowid
        db.execute("INSERT INTO band_users VALUES(?,?,?)",(band,owner,'owner'))
    with TestClient(module.app) as c:
        token=c.post('/api/auth/login',json={'email':'owner@example.test',
            'password':'long-owner-password-123'}).json()['access_token']
        headers={'Authorization':'Bearer '+token}
        r=c.post(f'/api/bands/{band}/invitations',headers=headers,
            json={'email':'new@example.test','role':'member'})
        assert r.status_code==201,r.text
        invite=r.json()['invite_token']
        assert c.get(f'/api/bands/{band}/invitations',headers=headers).status_code==405
        payload={'token':invite,'email':'wrong@example.test','display_name':'Member',
            'password':'strong-member-password'}
        assert c.post('/api/auth/accept-invite',json=payload).status_code==400
        payload['email']='new@example.test'
        accepted=c.post('/api/auth/accept-invite',json=payload)
        assert accepted.status_code==201,accepted.text
        assert accepted.json()['band_id']==band
        assert c.post('/api/auth/accept-invite',json=payload).status_code==400
        member_login=c.post('/api/auth/login',json={'email':'new@example.test',
            'password':'strong-member-password'})
        assert member_login.status_code==200
        mh={'Authorization':'Bearer '+member_login.json()['access_token']}
        assert c.get(f'/api/bands/{band}/members',headers=mh).status_code==200
        assert c.post(f'/api/bands/{band}/invitations',headers=mh,
            json={'email':'third@example.test','role':'member'}).status_code==403

def test_existing_user_invitation_requires_matching_identity(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'existing.db'))
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','1')
    import src.app as module
    importlib.reload(module)
    with module.db() as db:
        owner=db.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('owner@example.test','Owner',hash_password('very-long-owner-password'))).lastrowid
        invited=db.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('invited@example.test','Invited',hash_password('very-long-invite-password'))).lastrowid
        stranger=db.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('stranger@example.test','Stranger',hash_password('very-long-stranger-pass'))).lastrowid
        band=db.execute("INSERT INTO bands(name) VALUES('Other Band')").lastrowid
        db.execute("INSERT INTO band_users VALUES(?,?,?)",(band,owner,'owner'))
    with TestClient(module.app) as client:
        def header(email,password):
            login=client.post('/api/auth/login',json={'email':email,'password':password})
            assert login.status_code==200, login.text
            return {'Authorization':'Bearer '+login.json()['access_token']}
        oh=header('owner@example.test','very-long-owner-password')
        ih=header('invited@example.test','very-long-invite-password')
        sh=header('stranger@example.test','very-long-stranger-pass')
        response=client.post(f'/api/bands/{band}/invitations',headers=oh,
            json={'email':'invited@example.test','role':'member'})
        assert response.status_code==201,response.text
        token=response.json()['invite_token']
        path='/api/auth/accept-existing-invite'
        assert client.post(path,json={'token':token}).status_code==401
        assert client.post(path,headers=sh,json={'token':token}).status_code==400
        accepted=client.post(path,headers=ih,json={'token':token})
        assert accepted.status_code==201,accepted.text
        assert accepted.json()=={'band_id':band,'role':'member'}
        assert client.post(path,headers=ih,json={'token':token}).status_code==400
        assert client.get(f'/api/bands/{band}/members',headers=ih).status_code==200
        assert client.post(f'/api/bands/{band}/bookings',headers=ih,
            json={'venue':'Not allowed'}).status_code==403
