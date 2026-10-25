import importlib
import pytest
from fastapi.testclient import TestClient
from src.accounts import hash_password

def test_owner_assisted_recovery_revokes_sessions(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'recover.db'))
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','1')
    import src.app as module
    importlib.reload(module)
    with module.db() as con:
        owner=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('owner@example.test','Owner',hash_password('owner-long-password-123'))).lastrowid
        member=con.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('member@example.test','Member',hash_password('member-long-password-123'))).lastrowid
        band=con.execute("INSERT INTO bands(name) VALUES('Recover Band')").lastrowid
        con.execute("INSERT INTO band_users VALUES(?,?,?)",(band,owner,'owner'))
        con.execute("INSERT INTO band_users VALUES(?,?,?)",(band,member,'member'))
    with TestClient(module.app) as client:
        def login(email,password):
            response=client.post('/api/auth/login',json={'email':email,'password':password})
            assert response.status_code==200,response.text
            return {'Authorization':'Bearer '+response.json()['access_token']}
        owner_h=login('owner@example.test','owner-long-password-123')
        member_h=login('member@example.test','member-long-password-123')
        endpoint=f'/api/bands/{band}/account-recovery'
        assert client.post(endpoint,headers=member_h,json={'email':'member@example.test'}).status_code==403
        assert client.post(endpoint,headers=owner_h,json={'email':'owner@example.test'}).status_code==403
        issued=client.post(endpoint,headers=owner_h,json={'email':'member@example.test'})
        assert issued.status_code==200,issued.text
        token=issued.json()['recovery_token']
        assert client.post('/api/auth/recover',json={'token':'invalid','password':'validnewpassword123'}).status_code==422
        response=client.post('/api/auth/recover',json={'token':token,'password':'validnewpassword123'})
        assert response.status_code==200,response.text
        assert response.json()['sessions_revoked'] is True
        assert client.get('/api/auth/me',headers=member_h).status_code==401
        assert client.post('/api/auth/recover',json={'token':token,'password':'anothernewpassword123'}).status_code==400
        assert client.post('/api/auth/login',json={'email':'member@example.test',
            'password':'member-long-password-123'}).status_code==401
        assert client.post('/api/auth/login',json={'email':'member@example.test',
            'password':'validnewpassword123'}).status_code==200

def test_recovery_expiry_and_reissue(tmp_path, monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'expiry.db'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    import src.app as module
    importlib.reload(module)
    from src.recovery import issue, redeem
    from fastapi import HTTPException
    with module.db() as db:
        owner=db.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('owner2@example.test','Owner',hash_password('owner2-long-password'))).lastrowid
        member=db.execute("INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)",
            ('member2@example.test','Member',hash_password('member2-long-password'))).lastrowid
        band=db.execute("INSERT INTO bands(name) VALUES('Expiry Band')").lastrowid
        db.execute("INSERT INTO band_users VALUES(?,?,?)",(band,owner,'owner'))
        db.execute("INSERT INTO band_users VALUES(?,?,?)",(band,member,'member'))
        expired=issue(db,owner,band,'member2@example.test',now=1000)
        with pytest.raises(HTTPException) as failed:
            redeem(db,expired,'updated-long-password',now=2801)
        assert failed.value.status_code==400
        first=issue(db,owner,band,'member2@example.test',now=4000)
        newer=issue(db,owner,band,'member2@example.test',now=4010)
        with pytest.raises(HTTPException):
            redeem(db,first,'updated-long-password',now=4020)
        assert redeem(db,newer,'updated-long-password',now=4020)['recovered'] is True
