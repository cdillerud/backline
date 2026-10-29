import importlib
from fastapi.testclient import TestClient

def test_market_evidence_and_campaign_approval(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'studio.db'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    import src.app as application
    importlib.reload(application)
    client=TestClient(application.app)
    band=client.post('/api/bands',json={'name':'Band'}).json()['id']
    other=client.post('/api/bands',json={'name':'Other'}).json()['id']
    gig=client.post(f'/api/bands/{band}/events',json={
        'kind':'Gig','title':'Saturday','date':'2026-11-14'}).json()['id']
    prefix=f'/api/bands/{band}/gigs/{gig}'
    finding={'title':'Another concert','source_url':'https://example.com/event/123',
        'event_date':'2026-11-14','venue':'Local room','category':'Concert',
        'relevance':'May share an audience'}
    assert client.post(prefix+'/market',json=finding).status_code==201
    assert len(client.get(prefix+'/market').json())==1
    assert client.post(prefix+'/market',json={**finding,'source_url':'javascript:alert(1)'}).status_code==422
    assert client.get(f'/api/bands/{other}/gigs/{gig}/market').status_code==404
    draft=client.post(prefix+'/campaign',json={
        'channel':'Facebook','angle':'Local originals',
        'body':'Saturday night: live music at our favorite room.'})
    assert draft.status_code==201 and draft.json()['status']=='draft'
    id=draft.json()['id']
    assert client.post(prefix+f'/campaign/{id}/approve',json={'note':'Reviewed location and date'}).json()=={
        'status':'approved','published':False}
    assert client.post(prefix+f'/campaign/{id}/approve',json={}).status_code==409
    assert client.get(prefix+'/campaign').json()[0]['status']=='approved'
    assert client.get(f'/api/bands/{other}/gigs/{gig}/campaign').status_code==404
    assert client.post(prefix+'/campaign',json={'channel':'Unknown','angle':'Test','body':'text'}).status_code==422
