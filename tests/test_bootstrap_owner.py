import importlib
import sqlite3
import pytest
from fastapi.testclient import TestClient
from src.bootstrap_owner import bootstrap

def test_offline_owner_claim_is_explicit_and_one_time(tmp_path,monkeypatch):
    path=tmp_path/'backline.db'
    with pytest.raises(ValueError,match="Existing"):
        bootstrap(path,'owner@example.test','Owner','very-long-test-password',1)
    monkeypatch.setenv('BACKLINE_DB',str(path))
    monkeypatch.setenv('BACKLINE_LOCAL_DEV','1')
    import src.app as application
    importlib.reload(application)
    band=TestClient(application.app).post('/api/bands',json={'name':'Claim this band'}).json()['id']
    with pytest.raises(ValueError,match="does not exist"):
        bootstrap(path,'owner@example.test','Owner','very-long-test-password',999)
    result=bootstrap(path,'owner@example.test','Owner','very-long-test-password',band)
    assert result['band_id']==band
    with pytest.raises(ValueError,match="already has an owner"):
        bootstrap(path,'another@example.test','Second','very-long-test-password',band)
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM band_users WHERE band_id=? AND role='owner'",(band,)).fetchone()[0]==1
    monkeypatch.delenv('BACKLINE_LOCAL_DEV',raising=False)
