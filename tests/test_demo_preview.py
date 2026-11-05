import importlib
from fastapi.testclient import TestClient

def test_preview_seeding_is_opt_in_and_idempotent(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'demo.db'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    monkeypatch.setenv('BACKLINE_ACCOUNTS_ENABLED','0')
    monkeypatch.setenv('BACKLINE_DEMO_SEED','1')
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    bands=client.get('/api/bands').json()
    demo=next(b for b in bands if b['name']=='The Drunk Uncles (Demo)')
    gigs=client.get(f"/api/bands/{demo['id']}/events").json()
    assert len([g for g in gigs if g['kind']=='Gig'])==2
    stage=client.get(f"/api/bands/{demo['id']}/gigs/{next(g['id'] for g in gigs if g['kind']=='Gig')}/stage")
    assert stage.status_code==200
    assert len(stage.json()['items'])==6
    assert len(client.get(f"/api/bands/{demo['id']}/tours").json())==1
    module.init_db()
    assert len(client.get(f"/api/bands/{demo['id']}/events").json())==3
    assert len(client.get(f"/api/bands/{demo['id']}/setlists").json())==1

def test_default_install_does_not_seed_demo(tmp_path,monkeypatch):
    monkeypatch.setenv('BACKLINE_DB',str(tmp_path/'no_demo.db'))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    monkeypatch.delenv('BACKLINE_DEMO_SEED',raising=False)
    import src.app as module
    importlib.reload(module)
    client=TestClient(module.app)
    assert not any(b['name'].endswith('(Demo)') for b in client.get('/api/bands').json())
