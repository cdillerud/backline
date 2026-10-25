import importlib
from pathlib import Path
from fastapi.testclient import TestClient

def test_booking_crm_history_and_band_isolation(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'booking.db'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    import src.app as application
    importlib.reload(application)
    c=TestClient(application.app)
    first=c.post('/api/bands',json={'name':'First'}).json()['id']
    second=c.post('/api/bands',json={'name':'Second'}).json()['id']
    base=f'/api/bands/{first}/bookings'
    r=c.post(base,json={'venue':'The Cedar','contact_name':'Alex','next_followup':'2026-11-01'})
    assert r.status_code==201,r.text
    lead=r.json()['id']
    assert c.get(base).json()[0]['stage']=='To Contact'
    activity=c.post(base+f'/{lead}/activity',json={'kind':'Email sent','detail':'Introduced the band','next_followup':'2026-11-03'})
    assert activity.status_code==201
    r=c.post(base+f'/{lead}/stage',json={'stage':'Contacted','detail':'Requested spring calendar'})
    assert r.status_code==201
    hist=c.get(base+f'/{lead}/activity').json()
    assert len(hist)==3
    assert hist[0]['kind']=='Stage changed'
    assert c.get(base).json()[0]['stage']=='Contacted'
    assert c.post(base+f'/{lead}/activity',json={'kind':'Unapproved','detail':'Wrong'}).status_code==422
    assert c.post(base+f'/{lead}/stage',json={'stage':'Whatever','detail':'Wrong'}).status_code==422
    wrong=f'/api/bands/{second}/bookings/{lead}'
    assert c.get(wrong+'/activity').status_code==404
    assert c.post(wrong+'/activity',json={'kind':'Note','detail':'Wrong band'}).status_code==404
    assert c.post(wrong+'/stage',json={'stage':'Confirmed','detail':'Wrong band'}).status_code==404
    assert c.get(f'/api/bands/{second}/bookings').json()==[]
