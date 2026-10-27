"""Isolated synthetic account bootstrap: never claim existing non-demo bands."""
import importlib
import pytest
from fastapi.testclient import TestClient

def test_authenticated_demo_requires_secret_and_fresh_database(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"demo.sqlite"))
    monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED","1")
    monkeypatch.setenv("BACKLINE_DEMO_SEED","1")
    monkeypatch.setenv("BACKLINE_DEMO_ACCOUNTS","1")
    monkeypatch.setenv("BACKLINE_DEMO_PASSWORD","synthetic-password-not-for-production")
    import src.app as mod
    app=importlib.reload(mod)
    with app.db() as con:
        bands=con.execute("SELECT id,name FROM bands").fetchall()
        assert len(bands)==1 and bands[0]["name"]=="The Drunk Uncles (Demo)"
        assert con.execute("SELECT count(*) FROM users").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM discussion_threads").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM discussion_posts").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM event_rsvps").fetchone()[0]==1
    client=TestClient(app.app)
    assert client.get("/api/bands").status_code==401
    login=client.post("/api/auth/login",json={"email":"demo-owner@example.test","password":"synthetic-password-not-for-production"})
    assert login.status_code==200,login.text
    token=login.json()["access_token"]
    headers={"Authorization":"Bearer "+token}
    assert client.get("/api/bands",headers=headers).status_code==200
    band_id=bands[0]["id"]
    assert client.get(f"/api/bands/{band_id}/discussions").status_code==401
    threads=client.get(f"/api/bands/{band_id}/discussions",headers=headers)
    assert threads.status_code==200,threads.text
    assert len(threads.json())==1
    thread_id=threads.json()[0]["id"]
    posts=client.get(f"/api/bands/{band_id}/discussions/{thread_id}/posts",headers=headers)
    assert posts.status_code==200,posts.text
    assert len(posts.json())==1
    events=client.get(f"/api/bands/{band_id}/events",headers=headers)
    assert events.status_code==200,events.text
    rsvps=client.get(f"/api/bands/{band_id}/events/{events.json()[0]['id']}/rsvps",headers=headers)
    assert rsvps.status_code==200,rsvps.text
    assert len(rsvps.json())==1
    app.init_db()  # restart does not duplicate accounts, nor reset session
    with app.db() as con:
        assert con.execute("SELECT count(*) FROM users").fetchone()[0]==1
    assert client.get("/api/bands",headers={"Authorization":"Bearer "+token}).status_code==200

def test_authenticated_demo_rejects_legacy_bands(tmp_path,monkeypatch):
    monkeypatch.setenv("BACKLINE_DB",str(tmp_path/"legacy.sqlite"))
    monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED","0")
    monkeypatch.delenv("BACKLINE_DEMO_ACCOUNTS",raising=False)
    monkeypatch.delenv("BACKLINE_DEMO_SEED",raising=False)
    import src.app as mod
    app=importlib.reload(mod)
    monkeypatch.setenv("BACKLINE_ACCOUNTS_ENABLED","1")
    monkeypatch.setenv("BACKLINE_DEMO_SEED","1")
    monkeypatch.setenv("BACKLINE_DEMO_ACCOUNTS","1")
    monkeypatch.setenv("BACKLINE_DEMO_PASSWORD","synthetic-password-not-for-production")
    with pytest.raises(RuntimeError,match="refuses existing non-demo data"):
        app.init_db()
